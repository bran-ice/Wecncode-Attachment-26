"""Turn retrieved chunks into a grounded, cited answer — or an honest refusal.

Everything here exists to make one failure impossible: an answer that sounds
like the manual but was invented. Three mechanisms, in order of how much work
they do:

1. **The context is the only source.** The prompt carries numbered blocks and an
   instruction that nothing outside them may be used. World knowledge about
   Samsung phones is not admissible — it is exactly what produces a plausible
   settings path that does not exist on the user's device.
2. **Every claim carries `[n]`.** A marker is cheap to emit and cheap to check,
   which is what makes citation accuracy measurable at all in Phase 7.
3. **Refusal is a first-class output.** The model is told to emit a sentinel
   when the context does not cover the question. A system that answers anyway,
   from world knowledge, is worse than one that says it doesn't know: the user
   cannot tell the two apart, and the manual was the whole point.

Markers are parsed back into `Citation` objects against the chunks actually
sent. A `[9]` when only five blocks exist is dropped rather than rendered — the
model occasionally invents a marker, and a citation that resolves to nothing is
the same class of bug as a citation pointing at the wrong page.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterator, Optional, Sequence

from core.logging_setup import get_logger
from core.schema import Answer, Citation, RetrievedChunk

log = get_logger(__name__)

GEN_MODEL = "gemini-3.7-flash"

# Emitted verbatim by the model when the context does not cover the question.
# A sentinel rather than prose matching: "I don't have information" also appears
# inside perfectly good answers ("the manual does not list a weight for...").
REFUSAL_SENTINEL = "INSUFFICIENT_CONTEXT"

# Per-1M-token rates, used only for the cost column in the Phase 7 table.
# UNVERIFIED for gemini-3.7-flash: these are the old gemini-2.5-flash rates,
# kept as a placeholder after 2.5-flash was retired for new API keys. Check
# current pricing before publishing a cost-per-query number.
INPUT_COST_PER_1M = 0.30
OUTPUT_COST_PER_1M = 2.50

MAX_SNIPPET_CHARS = 1200

MAX_RETRIES = 4
# Same set ingest/embed.py treats as transient: overload and rate limiting are
# worth waiting out, a 404 on a retired model id is not.
# Transport failures never carry an HTTP status — the connection died before a
# response existed. A dropped TLS handshake ("UNEXPECTED_EOF_WHILE_READING") is
# the common one on flaky links, and it is exactly what a retry fixes.
_RETRYABLE = (
    "429", "RESOURCE_EXHAUSTED", "503", "500", "UNAVAILABLE", "timeout",
    "SSL", "EOF occurred", "ConnectError", "ConnectTimeout", "Connection reset",
)

# A per-*minute* 429 clears in seconds. A per-*day* one clears tomorrow, and
# retrying it burns four attempts and ~14s of backoff per call against a quota
# that cannot recover — which is how a 64-question eval spent its whole budget
# on the first few questions and reported the rest as model failures.
_DAILY_QUOTA = ("PerDay", "per day", "GenerateRequestsPerDayPerProject")


def _is_daily_quota(message: str) -> bool:
    return any(token in message for token in _DAILY_QUOTA)


def _is_retryable(message: str) -> bool:
    if _is_daily_quota(message):
        return False
    return any(token in message for token in _RETRYABLE)

SYSTEM_INSTRUCTION = f"""\
You answer questions about Samsung Galaxy devices using ONLY the numbered context \
blocks provided. The context is extracted from official Samsung user manuals.

Rules:
1. Use only the context. Do not use prior knowledge about Samsung devices, even if \
you are confident it is correct. Different models differ, and the user's manual is \
the authority.
2. Cite every factual claim inline with the block number in square brackets, like \
[1]. A sentence stating two facts from two blocks carries both: [1][3].
3. Never cite a block number that was not provided.
4. Reproduce settings paths, part numbers and button names exactly as written in \
the context. Do not normalise or modernise them.
5. If the context does not contain the answer, reply with exactly \
{REFUSAL_SENTINEL}: followed by one sentence naming what is missing. Do not \
guess, and do not pad a refusal with related facts the user did not ask for.
6. Be concise. Prefer the numbered steps the manual gives over prose."""

_MARKER_RE = re.compile(r"\[(\d+)\]")
# A sentence ends at ., ! or ? followed by whitespace — good enough to check
# that markers are distributed through the answer rather than dumped at the end.
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]*")


class GenerationError(RuntimeError):
    """Raised when the generation call fails or returns nothing usable."""


class QuotaExhausted(GenerationError):
    """The daily quota is gone. Waiting will not help; stop the run."""


@dataclass
class ContextBlock:
    """One numbered block, and the chunk it was rendered from."""

    marker: int
    hit: RetrievedChunk
    model: str

    def render(self) -> str:
        chunk = self.hit.chunk
        pages = (
            f"p.{chunk.page_start}"
            if chunk.page_start == chunk.page_end
            else f"pp.{chunk.page_start}-{chunk.page_end}"
        )
        header = f"[{self.marker}] {self.model} {pages}"
        if chunk.section_path:
            header += f" — {chunk.section_path}"
        return f"{header}\n{chunk.text}"


def build_context(
    hits: Sequence[RetrievedChunk], doc_models: Optional[dict[str, str]] = None
) -> list[ContextBlock]:
    """Number the retrieved chunks. Marker `n` is 1-based: `[1]` is the top hit."""
    doc_models = doc_models or {}
    return [
        ContextBlock(
            marker=position,
            hit=hit,
            model=doc_models.get(hit.chunk.doc_id, "Samsung Galaxy"),
        )
        for position, hit in enumerate(hits, start=1)
    ]


def doc_models_for(store, hits: Sequence[RetrievedChunk]) -> dict[str, str]:
    """Map doc_id → model name, so a citation names the manual it came from.

    Read-only: the query pipeline never writes to the store.
    """
    models: dict[str, str] = {}
    for hit in hits:
        doc_id = hit.chunk.doc_id
        if doc_id not in models:
            document = store.get_document(doc_id)
            models[doc_id] = document.model if document else "Samsung Galaxy"
    return models


def build_prompt(question: str, blocks: Sequence[ContextBlock]) -> str:
    context = "\n\n".join(block.render() for block in blocks)
    return f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:"


def parse_citations(
    text: str, blocks: Sequence[ContextBlock], store=None
) -> tuple[list[Citation], list[int]]:
    """Resolve `[n]` markers against the blocks actually sent.

    Returns the resolved citations in first-appearance order, plus the markers
    that resolved to nothing — those are hallucinated and must not be rendered
    as links, but the caller may want to count them.

    Figures are attached here, with `store`, because citation is the signal
    that an answer needed a passage. A figure on a retrieved-but-uncited chunk
    illustrates something the answer never said, so it is not rendered.
    """
    by_marker = {block.marker: block for block in blocks}
    citations: list[Citation] = []
    dangling: list[int] = []
    seen: set[int] = set()

    for match in _MARKER_RE.finditer(text):
        marker = int(match.group(1))
        if marker in seen:
            continue
        seen.add(marker)
        block = by_marker.get(marker)
        if block is None:
            dangling.append(marker)
            log.warning("Answer cited [%d], which was never in the context", marker)
            continue
        chunk = block.hit.chunk
        citations.append(
            Citation(
                marker=marker,
                chunk_id=chunk.chunk_id if chunk.chunk_id is not None else -1,
                model=block.model,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                section_path=chunk.section_path,
                snippet=chunk.text[:MAX_SNIPPET_CHARS],
                figures=_figures_for(store, chunk),
            )
        )
    return citations, dangling


def _figures_for(store, chunk) -> list:
    """The figures on a cited chunk, or none if the store has no figures.

    Failure here is cosmetic — a missing illustration must never cost the user
    a correct, cited answer — so a store predating the figures tables degrades
    to a text-only answer rather than raising.
    """
    if store is None or chunk.chunk_id is None:
        return list(chunk.figures)
    try:
        return store.get_figures(chunk.chunk_id)
    except Exception as exc:
        log.debug("Figure lookup failed for chunk %s (%s)", chunk.chunk_id, exc)
        return []


def uncited_sentences(text: str) -> list[str]:
    """Sentences making a claim with no `[n]` marker — the Phase 5 exit gate.

    Fragments too short to be a claim are ignored; so is the refusal line, which
    is deliberately uncited because it asserts nothing about the device.
    """
    if is_refusal(text):
        return []
    offenders = []
    for sentence in _SENTENCE_RE.findall(text):
        stripped = sentence.strip()
        if len(stripped.split()) < 4:
            continue
        if stripped.endswith(":"):  # a lead-in to a cited list
            continue
        if not _MARKER_RE.search(stripped):
            offenders.append(stripped)
    return offenders


def is_refusal(text: str) -> bool:
    return text.lstrip().startswith(REFUSAL_SENTINEL)


def clean_refusal(text: str) -> str:
    """Strip the sentinel, keeping the sentence that says what is missing."""
    body = text.lstrip()[len(REFUSAL_SENTINEL) :].lstrip(": ").strip()
    return body or "The manuals I have do not cover that."


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1_000_000 * INPUT_COST_PER_1M
        + output_tokens / 1_000_000 * OUTPUT_COST_PER_1M
    )


class GeminiGenerator:
    """Grounded generation over Gemini. The client loads lazily."""

    def __init__(
        self,
        api_key: str,
        model: str = GEN_MODEL,
        client=None,
        system_instruction: str = SYSTEM_INSTRUCTION,
        sleep=time.sleep,
    ):
        self.model = model
        self.system_instruction = system_instruction
        self._api_key = api_key
        self._client = client
        self._sleep = sleep
        self.input_tokens = 0
        self.output_tokens = 0

    @property
    def client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _config(self, instruction: Optional[str] = None):
        from google.genai import types

        return types.GenerateContentConfig(
            system_instruction=instruction or self.system_instruction,
            # Deterministic: the same question over the same context should not
            # produce a different settings path on a second run.
            temperature=0.0,
        )

    def _account(self, response) -> None:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return
        self.input_tokens += getattr(usage, "prompt_token_count", 0) or 0
        self.output_tokens += getattr(usage, "candidates_token_count", 0) or 0

    def _retry(self, call, what: str):
        """Retry transient failures. `call` must be restartable from scratch."""
        delay = 2.0
        for attempt in range(MAX_RETRIES):
            try:
                return call()
            except Exception as exc:
                message = str(exc)
                if _is_daily_quota(message):
                    raise QuotaExhausted(f"{what} failed: daily quota exhausted") from exc
                if not _is_retryable(message) or attempt == MAX_RETRIES - 1:
                    raise GenerationError(f"{what} failed: {message}") from exc
                log.warning("%s failed (%s); retrying in %.0fs", what, message[:80], delay)
                self._sleep(delay)
                delay = min(delay * 2, 30.0)
        raise GenerationError("unreachable")

    def generate_with_instruction(self, prompt: str, instruction: str) -> str:
        """Generate under a different system instruction than the grounded one.

        Used by query expansion, which is a rewriting task and must not inherit
        the citation rules — a rewritten question carrying `[1]` is nonsense.
        """
        response = self._retry(
            lambda: self.client.models.generate_content(
                model=self.model, contents=prompt, config=self._config(instruction)
            ),
            "expansion",
        )
        self._account(response)
        return getattr(response, "text", "") or ""

    def generate(self, prompt: str) -> str:
        response = self._retry(
            lambda: self.client.models.generate_content(
                model=self.model, contents=prompt, config=self._config()
            ),
            "generation",
        )
        self._account(response)
        text = getattr(response, "text", None)
        if not text:
            raise GenerationError("generation returned no text")
        return text

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield text pieces, retrying only until the first one is emitted.

        `generate_content_stream` returns lazily — the request is not made until
        the stream is iterated, so a 503 surfaces on the first `next()`, not at
        the call. Retrying has to wrap the iteration, not the opening call.

        Once a piece has been handed to the caller a retry would replay it: a UI
        that has already painted half an answer cannot un-paint it, so from that
        point a failure is a failure.
        """
        delay = 2.0
        for attempt in range(MAX_RETRIES):
            emitted = False
            try:
                stream = self.client.models.generate_content_stream(
                    model=self.model, contents=prompt, config=self._config()
                )
                for response in stream:
                    self._account(response)
                    if piece := getattr(response, "text", None):
                        emitted = True
                        yield piece
                return
            except Exception as exc:
                message = str(exc)
                if emitted:
                    raise GenerationError(f"generation failed mid-stream: {message}") from exc
                if _is_daily_quota(message):
                    raise QuotaExhausted("generation failed: daily quota exhausted") from exc
                if not _is_retryable(message) or attempt == MAX_RETRIES - 1:
                    raise GenerationError(f"generation failed: {message}") from exc
                log.warning("Generation failed (%s); retrying in %.0fs", message[:80], delay)
                self._sleep(delay)
                delay = min(delay * 2, 30.0)


def build_generator(settings, client=None) -> GeminiGenerator:
    return GeminiGenerator(
        api_key=settings.gemini_api_key, model=settings.gen_model, client=client
    )


def answer_question(
    question: str,
    hits: Sequence[RetrievedChunk],
    generator: GeminiGenerator,
    store=None,
    doc_models: Optional[dict[str, str]] = None,
    resolved_question: Optional[str] = None,
) -> Answer:
    """Generate one grounded answer over already-retrieved chunks.

    Retrieval is the caller's job — this stays separate so the Phase 7 ablation
    can vary the retrieval arm without touching generation.

    `resolved_question` is the pronoun-resolved rewrite from `query/expand.py`,
    and is what the model is asked. See `stream_answer` for why.
    """
    started = time.monotonic()

    # Retrieving nothing is not a generation problem; asking the model about an
    # empty context invites it to answer from world knowledge.
    if not hits:
        return Answer(
            question=question,
            text="I found nothing in the manuals about that.",
            refused=True,
            latency_ms=(time.monotonic() - started) * 1000,
        )

    if doc_models is None:
        doc_models = doc_models_for(store, hits) if store is not None else {}
    blocks = build_context(hits, doc_models)

    before_input, before_output = generator.input_tokens, generator.output_tokens
    raw = generator.generate(build_prompt(resolved_question or question, blocks))

    return _assemble(
        question, raw, blocks, hits, generator, before_input, before_output, started,
        store=store,
    )


def stream_answer(
    question: str,
    hits: Sequence[RetrievedChunk],
    generator: GeminiGenerator,
    store=None,
    doc_models: Optional[dict[str, str]] = None,
    resolved_question: Optional[str] = None,
) -> Iterator[str | Answer]:
    """Yield text as it arrives, then the assembled `Answer` last.

    Citations cannot be resolved until the text is complete — a marker can be
    split across two streamed pieces — so the UI streams the prose and attaches
    sources at the end.

    `resolved_question` is the rewrite `query/expand.py` produced for a
    follow-up, and is what the model is asked. "Explain it step by step" has no
    antecedent in the context, so a model told to use only the context correctly
    refuses it — the retrieval was right, the question was the part that still
    needed history. Only the question is substituted: the context blocks remain
    retrieved chunks and nothing else, so no prior turn can be cited.

    `Answer.question` keeps what the user actually typed.
    """
    started = time.monotonic()

    if not hits:
        message = "I found nothing in the manuals about that."
        yield message
        yield Answer(
            question=question, text=message, refused=True,
            latency_ms=(time.monotonic() - started) * 1000,
        )
        return

    if doc_models is None:
        doc_models = doc_models_for(store, hits) if store is not None else {}
    blocks = build_context(hits, doc_models)

    before_input, before_output = generator.input_tokens, generator.output_tokens
    pieces: list[str] = []
    for piece in generator.stream(build_prompt(resolved_question or question, blocks)):
        pieces.append(piece)
        yield piece

    yield _assemble(
        question, "".join(pieces), blocks, hits, generator,
        before_input, before_output, started, store=store,
    )


def _assemble(
    question: str,
    raw: str,
    blocks: Sequence[ContextBlock],
    hits: Sequence[RetrievedChunk],
    generator: GeminiGenerator,
    before_input: int,
    before_output: int,
    started: float,
    store=None,
) -> Answer:
    refused = is_refusal(raw)
    text = clean_refusal(raw) if refused else raw.strip()
    citations, dangling = parse_citations(text, blocks, store=store)

    if dangling:
        log.warning("Dropped %d citation(s) with no matching block", len(dangling))
    if not refused and not citations:
        log.warning("Answer carried no citations: %r", text[:80])

    return Answer(
        question=question,
        text=text,
        citations=citations,
        retrieved=list(hits),
        refused=refused,
        latency_ms=(time.monotonic() - started) * 1000,
        input_tokens=generator.input_tokens - before_input,
        output_tokens=generator.output_tokens - before_output,
    )
