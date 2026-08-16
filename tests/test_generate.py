"""Phase 5 — grounded generation.

Gemini is mocked everywhere except the `live` test. What is being tested is the
contract around the model: that markers resolve to real pages, that a refusal
survives as a refusal, and that an invented `[9]` never becomes a link.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.schema import Chunk, RetrievedChunk  # noqa: E402
from query.generate import (  # noqa: E402
    MAX_RETRIES,
    GenerationError,
    GeminiGenerator,
    REFUSAL_SENTINEL,
    answer_question,
    build_context,
    build_prompt,
    estimate_cost,
    is_refusal,
    parse_citations,
    stream_answer,
    uncited_sentences,
)


class FakeResponse:
    def __init__(self, text, prompt_tokens=100, output_tokens=20):
        self.text = text
        self.usage_metadata = type(
            "Usage",
            (),
            {"prompt_token_count": prompt_tokens, "candidates_token_count": output_tokens},
        )()


class FakeModels:
    def __init__(self, text="", pieces=None, raises=None):
        self.text = text
        self.pieces = pieces or []
        self.raises = raises
        self.prompts = []

    def generate_content(self, model, contents, config):
        self.prompts.append(contents)
        if self.raises:
            raise self.raises
        return FakeResponse(self.text)

    def generate_content_stream(self, model, contents, config):
        self.prompts.append(contents)
        if self.raises:
            raise self.raises
        return [FakeResponse(piece, prompt_tokens=0, output_tokens=1) for piece in self.pieces]


class FakeClient:
    def __init__(self, **kwargs):
        self.models = FakeModels(**kwargs)


def make_generator(**kwargs) -> GeminiGenerator:
    return GeminiGenerator(api_key="test-key", client=FakeClient(**kwargs))


@pytest.fixture
def hits(chunks):
    for position, chunk in enumerate(chunks):
        chunk.chunk_id = 100 + position
    return [
        RetrievedChunk(chunk=chunk, score=1.0 / (position + 1), source="rrf", rank=position)
        for position, chunk in enumerate(chunks)
    ]


@pytest.fixture
def models(chunks):
    return {chunks[0].doc_id: "Galaxy S24 Ultra"}


# --- context and prompt ---------------------------------------------------


def test_blocks_are_numbered_from_one(hits, models):
    blocks = build_context(hits, models)
    assert [block.marker for block in blocks] == [1, 2, 3]


def test_block_header_carries_model_page_and_section(hits, models):
    rendered = build_context(hits, models)[0].render()
    assert rendered.startswith("[1] Galaxy S24 Ultra p.42 — Settings > Lock screen")


def test_page_range_renders_as_a_range(hits, models):
    rendered = build_context(hits, models)[1].render()
    assert "pp.57-58" in rendered


def test_prompt_contains_every_block_and_the_question(hits, models):
    prompt = build_prompt("how do I charge fast", build_context(hits, models))
    assert "EP-TA845" in prompt
    assert "how do I charge fast" in prompt


# --- citation parsing -----------------------------------------------------


def test_citation_parsing_resolves_markers_to_chunks(hits, models):
    blocks = build_context(hits, models)
    citations, dangling = parse_citations("Do this [1] and that [2].", blocks)
    assert [c.marker for c in citations] == [1, 2]
    assert [c.chunk_id for c in citations] == [100, 101]
    assert dangling == []


def test_adjacent_markers_both_resolve(hits, models):
    blocks = build_context(hits, models)
    citations, _ = parse_citations("Two facts [2][3].", blocks)
    assert [c.marker for c in citations] == [2, 3]


def test_repeated_marker_cited_once(hits, models):
    blocks = build_context(hits, models)
    citations, _ = parse_citations("First [1]. Again [1]. Still [1].", blocks)
    assert len(citations) == 1


def test_out_of_range_marker_is_dropped_not_rendered(hits, models):
    blocks = build_context(hits, models)
    citations, dangling = parse_citations("Invented [9] but real [1].", blocks)
    assert [c.marker for c in citations] == [1]
    assert dangling == [9]


def test_citation_points_to_the_real_page(hits, models):
    blocks = build_context(hits, models)
    citations, _ = parse_citations("Use a 45W adapter [2].", blocks)
    citation = citations[0]
    # The cited page must be the page the fact actually came from.
    assert (citation.page_start, citation.page_end) == (57, 58)
    assert "EP-TA845" in citation.snippet
    assert citation.label() == "Galaxy S24 Ultra pp.57-58"


def test_no_markers_yields_no_citations(hits, models):
    citations, dangling = parse_citations("Bare assertion.", build_context(hits, models))
    assert citations == [] and dangling == []


# --- the every-claim-cited gate -------------------------------------------


def test_every_claim_cited_passes_a_well_formed_answer():
    text = "Open Settings and tap Lock screen [1]. Then enable the toggle [2]."
    assert uncited_sentences(text) == []


def test_every_claim_cited_flags_a_bare_sentence():
    text = "Open Settings and tap Lock screen [1]. It also charges faster."
    assert uncited_sentences(text) == ["It also charges faster."]


def test_lead_in_lines_are_not_flagged():
    assert uncited_sentences("Follow these steps to enable it:\nTap Settings [1].") == []


def test_refusal_is_exempt_from_the_citation_gate():
    assert uncited_sentences(f"{REFUSAL_SENTINEL}: the manuals do not cover pricing.") == []


# --- refusal --------------------------------------------------------------


def test_refuses_unanswerable(hits, models):
    generator = make_generator(
        text=f"{REFUSAL_SENTINEL}: the manuals do not give a battery cycle rating."
    )
    answer = answer_question("how many charge cycles", hits, generator, doc_models=models)
    assert answer.refused is True
    assert REFUSAL_SENTINEL not in answer.text
    assert "battery cycle rating" in answer.text


def test_refusal_says_what_is_missing_not_a_generic_apology(hits, models):
    generator = make_generator(text=f"{REFUSAL_SENTINEL}: no section covers eSIM transfer.")
    answer = answer_question("how do I move my eSIM", hits, generator, doc_models=models)
    assert "eSIM transfer" in answer.text


def test_empty_retrieval_refuses_without_calling_the_model(models):
    generator = make_generator(text="should never be produced")
    answer = answer_question("anything", [], generator, doc_models=models)
    assert answer.refused is True
    assert generator._client.models.prompts == []


def test_no_outside_knowledge_is_instructed(hits, models):
    """The prompt must forbid prior knowledge; without it the model fills gaps."""
    generator = make_generator(text="Answer [1].")
    answer_question("q", hits, generator, doc_models=models)
    assert "Do not use prior knowledge" in generator.system_instruction


# --- answers --------------------------------------------------------------


def test_answer_carries_citations_and_retrieved_chunks(hits, models):
    generator = make_generator(text="Tap Settings [1].")
    answer = answer_question("how do I enable AOD", hits, generator, doc_models=models)
    assert answer.refused is False
    assert [c.marker for c in answer.citations] == [1]
    assert len(answer.retrieved) == 3
    assert answer.latency_ms is not None


def test_token_accounting_is_per_call(hits, models):
    generator = make_generator(text="Tap Settings [1].")
    first = answer_question("q1", hits, generator, doc_models=models)
    second = answer_question("q2", hits, generator, doc_models=models)
    assert first.input_tokens == 100 and first.output_tokens == 20
    # Per-call, not cumulative — the generator total keeps climbing.
    assert second.input_tokens == 100
    assert generator.input_tokens == 200


def test_cost_estimate_scales_with_tokens():
    assert estimate_cost(0, 0) == 0
    assert estimate_cost(1_000_000, 0) == pytest.approx(0.30)
    assert estimate_cost(0, 1_000_000) == pytest.approx(2.50)


def test_generation_failure_is_wrapped(hits, models):
    generator = make_generator(raises=RuntimeError("400 INVALID_ARGUMENT"))
    generator._sleep = lambda _seconds: None
    with pytest.raises(GenerationError):
        answer_question("q", hits, generator, doc_models=models)


def test_permanent_error_is_not_retried(hits, models):
    """A retired model id returns 404. Retrying it just wastes the user's time."""
    generator = make_generator(raises=RuntimeError("404 NOT_FOUND"))
    calls = []
    generator._sleep = lambda seconds: calls.append(seconds)
    with pytest.raises(GenerationError):
        answer_question("q", hits, generator, doc_models=models)
    assert calls == []


def test_transient_error_is_retried_then_succeeds(hits, models):
    """503 UNAVAILABLE is what a busy model returns; it usually clears."""
    generator = make_generator(text="Tap Settings [1].")
    generator._sleep = lambda _seconds: None
    fake = generator._client.models
    real_call = fake.generate_content
    attempts = {"n": 0}

    def flaky(model, contents, config):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("503 UNAVAILABLE")
        return real_call(model, contents, config)

    fake.generate_content = flaky
    answer = answer_question("q", hits, generator, doc_models=models)
    assert attempts["n"] == 2
    assert answer.text == "Tap Settings [1]."


def test_retries_give_up_eventually(hits, models):
    generator = make_generator(raises=RuntimeError("503 UNAVAILABLE"))
    generator._sleep = lambda _seconds: None
    with pytest.raises(GenerationError):
        answer_question("q", hits, generator, doc_models=models)
    assert len(generator._client.models.prompts) == MAX_RETRIES


def test_empty_model_output_raises(hits, models):
    generator = make_generator(text="")
    with pytest.raises(GenerationError):
        answer_question("q", hits, generator, doc_models=models)


def test_doc_model_falls_back_when_document_is_missing(hits):
    blocks = build_context(hits, {})
    assert blocks[0].model == "Samsung Galaxy"


# --- streaming ------------------------------------------------------------


def test_streaming_assembles(hits, models):
    generator = make_generator(pieces=["Tap ", "Settings ", "[1]."])
    outputs = list(stream_answer("q", hits, generator, doc_models=models))
    text_pieces = [item for item in outputs if isinstance(item, str)]
    answer = outputs[-1]
    assert "".join(text_pieces) == "Tap Settings [1]."
    assert answer.text == "Tap Settings [1]."


def test_streaming_resolves_citations_only_at_the_end(hits, models):
    """A marker can be split across pieces, so parsing waits for the whole text."""
    generator = make_generator(pieces=["Tap Settings [", "1", "]."])
    answer = list(stream_answer("q", hits, generator, doc_models=models))[-1]
    assert [c.marker for c in answer.citations] == [1]


def test_stream_retries_a_failure_raised_on_first_iteration(hits, models):
    """The genai stream is lazy: a 503 arrives at the first next(), not the call."""
    generator = make_generator(pieces=["Tap Settings [1]."])
    generator._sleep = lambda _seconds: None
    fake = generator._client.models
    attempts = {"n": 0}

    def lazy_stream(model, contents, config):
        attempts["n"] += 1
        first_try = attempts["n"] == 1

        def gen():
            if first_try:
                raise RuntimeError("503 UNAVAILABLE")
            yield FakeResponse("Tap Settings [1].", 0, 1)

        return gen()

    fake.generate_content_stream = lazy_stream
    answer = list(stream_answer("q", hits, generator, doc_models=models))[-1]
    assert attempts["n"] == 2
    assert answer.text == "Tap Settings [1]."


def test_stream_does_not_replay_text_after_a_mid_stream_failure(hits, models):
    """Once a piece is emitted, a retry would duplicate it in the user's view."""
    generator = make_generator()
    generator._sleep = lambda _seconds: None
    fake = generator._client.models

    def half_broken(model, contents, config):
        def gen():
            yield FakeResponse("Tap ", 0, 1)
            raise RuntimeError("503 UNAVAILABLE")

        return gen()

    fake.generate_content_stream = half_broken
    with pytest.raises(GenerationError, match="mid-stream"):
        list(stream_answer("q", hits, generator, doc_models=models))


def test_streaming_empty_retrieval_still_yields_an_answer(models):
    generator = make_generator(pieces=["unused"])
    outputs = list(stream_answer("q", [], generator, doc_models=models))
    assert outputs[-1].refused is True


# --- live -----------------------------------------------------------------


@pytest.mark.live
def test_end_to_end_answer(hits, models):
    """A real Gemini call over a fixed context: cited, grounded, no invention."""
    from core.config import load_settings
    from query.generate import build_generator

    generator = build_generator(load_settings())
    answer = answer_question(
        "how do I enable always on display", hits, generator, doc_models=models
    )
    assert answer.refused is False
    assert answer.citations, "a real answer must cite something"
    assert all(c.marker in (1, 2, 3) for c in answer.citations)
    assert uncited_sentences(answer.text) == []


@pytest.mark.live
def test_live_refuses_what_the_context_does_not_cover(hits, models):
    from core.config import load_settings
    from query.generate import build_generator

    generator = build_generator(load_settings())
    answer = answer_question(
        "what is the warranty period in Kenya", hits, generator, doc_models=models
    )
    assert answer.refused is True
