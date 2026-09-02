"""One conversation: expand, retrieve, generate, remember.

This is the whole chat pipeline with no Streamlit in it. `app.py` is a view over
this class, which is what makes the multi-turn behaviour testable — Streamlit's
rerun-on-every-interaction model is close to untestable, and the rule worth
testing (history never reaches the grounding context) lives here.

The store is opened once and read many times; nothing here writes to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

from core.logging_setup import get_logger
from core.schema import Answer
from query.expand import Expansion, Turn, expand_query
from query.generate import GenerationError, stream_answer
from query.retrieve import retrieve

log = get_logger(__name__)

DEFAULT_TOP_K = 5
# Candidates are fused before the top_k cut, so retrieving deeper costs nothing
# at generation time and gives RRF more to work with.
CANDIDATE_DEPTH = 30


@dataclass
class TurnResult:
    """Everything one exchange produced, for rendering and for the readout."""

    question: str
    answer: Optional[Answer] = None
    expansion: Optional[Expansion] = None
    error: Optional[str] = None
    retrieval_ms: float = 0.0
    bm25_count: int = 0
    dense_count: int = 0
    collapsed: int = 0

    @property
    def searched_as(self) -> str:
        """What was actually sent to the retriever — shown in the UI so a
        surprising result set is explainable rather than mysterious."""
        if self.expansion and self.expansion.rewritten:
            return self.expansion.rewritten
        return self.question


@dataclass
class ChatSession:
    """A multi-turn conversation over one store."""

    store: object
    generator: object
    embedder: object = None
    mode: str = "hybrid"
    model_filter: Optional[str] = None
    top_k: int = DEFAULT_TOP_K
    history: list[Turn] = field(default_factory=list)
    turns: list[TurnResult] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(t.answer.input_tokens or 0 for t in self.turns if t.answer)

    @property
    def total_output_tokens(self) -> int:
        return sum(t.answer.output_tokens or 0 for t in self.turns if t.answer)

    def ask(self, question: str) -> Iterator[str | TurnResult]:
        """Stream one turn's text, then yield the finished `TurnResult`.

        Errors are returned inside the result rather than raised: a chat window
        that dies on one bad turn loses the whole conversation.
        """
        import time

        question = question.strip()
        result = TurnResult(question=question)
        if not question:
            result.error = "Ask a question about your Samsung device."
            self.turns.append(result)
            yield result
            return

        # Expansion is the only place history is allowed to be read.
        try:
            expansion = expand_query(question, self.history, self.generator)
        except Exception as exc:  # defensive: expand_query already swallows
            log.warning("Expansion raised (%s); continuing unexpanded", exc)
            expansion = Expansion(queries=[question])
        result.expansion = expansion

        started = time.monotonic()
        try:
            retrieval = retrieve(
                self.store,
                expansion.primary,
                embedder=self.embedder,
                queries=expansion.queries,
                mode=self.mode,
                candidates=CANDIDATE_DEPTH,
                top_k=self.top_k,
                model_filter=self.model_filter,
            )
        except Exception as exc:
            log.exception("Retrieval failed")
            result.error = f"Search failed: {exc}"
            self.turns.append(result)
            yield result
            return

        result.retrieval_ms = (time.monotonic() - started) * 1000
        result.bm25_count = retrieval.bm25_count
        result.dense_count = retrieval.dense_count
        result.collapsed = retrieval.collapsed_duplicates

        # `stream_answer` receives chunks and the question only. No turn of
        # history is passed, and there is no parameter through which it could be.
        #
        # The *resolved* question goes to the model: a rewrite is the only thing
        # that gives "explain it step by step" an antecedent, and without one a
        # generator restricted to the context refuses a follow-up whose chunks
        # were retrieved perfectly well. `searched_as` falls back to the raw
        # question when nothing was rewritten.
        try:
            for piece in stream_answer(
                question,
                retrieval.chunks,
                self.generator,
                store=self.store,
                resolved_question=result.searched_as,
            ):
                if isinstance(piece, str):
                    yield piece
                else:
                    result.answer = piece
        except GenerationError as exc:
            log.warning("Generation failed: %s", exc)
            result.error = _friendly_error(str(exc))
            self.turns.append(result)
            yield result
            return

        if result.answer is not None:
            self.history.append(Turn(question=question, answer=result.answer.text))
        self.turns.append(result)
        yield result

    def reset(self) -> None:
        self.history.clear()
        self.turns.clear()


INGEST_COMMAND = ".venv/Scripts/python.exe -m ingest"


def check_store_ready(store_dir, store=None) -> Optional[tuple[str, str]]:
    """Why the app cannot start, as (message, command to fix it).

    Returns None when the store is usable. Lives here rather than in `app.py`
    so the failure messages are testable: "no index" is the first thing a new
    user hits, and a traceback there loses them.
    """
    from pathlib import Path

    store_dir = Path(store_dir)
    if not store_dir.exists():
        return (
            f"No search index at {store_dir}. Build one first — it downloads and "
            "indexes the manuals, and takes a few minutes.",
            INGEST_COMMAND,
        )
    if store is not None and store.count_chunks() == 0:
        return (
            "The index is empty — no manuals have been ingested yet.",
            INGEST_COMMAND,
        )
    return None


def _friendly_error(message: str) -> str:
    """Say what to do, not just what broke."""
    if "429" in message or "RESOURCE_EXHAUSTED" in message:
        return (
            "Gemini rate limit reached. Wait a minute and ask again — "
            "the free tier allows a limited number of requests per minute."
        )
    if "503" in message or "UNAVAILABLE" in message:
        return "The model is busy right now. Try again in a moment."
    if "404" in message or "NOT_FOUND" in message:
        return (
            "The configured model is unavailable. Check GEN_MODEL in .env "
            "against the models your API key can reach."
        )
    if "API key" in message or "401" in message or "PERMISSION_DENIED" in message:
        return "Gemini rejected the API key. Check GEMINI_API_KEY in .env."
    return f"The answer could not be generated: {message}"
