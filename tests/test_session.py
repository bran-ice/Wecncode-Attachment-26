"""Phase 6 — multi-turn chat pipeline.

Streamlit is not exercised here; `app.py` is a view and `ChatSession` is the
thing with behaviour. The load-bearing test is `test_history_not_in_context`:
if history ever reaches the grounding prompt, the system can cite itself.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.schema import Document, RetrievedChunk  # noqa: E402
from query.expand import (  # noqa: E402
    Turn,
    expand_query,
    looks_dependent,
    render_history,
)
from query.session import (  # noqa: E402
    ChatSession,
    _friendly_error,
    check_store_ready,
)


class FakeStore:
    """Records what was searched. Never written to — that is the invariant."""

    def __init__(self, chunks, doc):
        self._chunks = chunks
        self._doc = doc
        self.bm25_queries = []
        self.dense_queries = []

    def search_bm25(self, query, k=30):
        self.bm25_queries.append(query)
        return [
            RetrievedChunk(chunk=c, score=1.0 / (i + 1), source="bm25", rank=i)
            for i, c in enumerate(self._chunks)
        ]

    def search_dense(self, vector, k=30):
        self.dense_queries.append(vector)
        return [
            RetrievedChunk(chunk=c, score=1.0 / (i + 1), source="dense", rank=i)
            for i, c in enumerate(reversed(self._chunks))
        ]

    def get_document(self, doc_id):
        return self._doc

    def list_documents(self):
        return [self._doc]


class FakeEmbedder:
    def embed_query(self, text):
        import numpy as np

        self.last = text
        return np.zeros(4, dtype="float32")


class FakeGenerator:
    """Captures every prompt it is handed, grounding and expansion alike."""

    def __init__(self, answer="Tap Settings [1].", rewrite=None, raises=None):
        self.answer = answer
        self.rewrite = rewrite
        self.raises = raises
        self.prompts = []
        self.instructions = []
        self.input_tokens = 0
        self.output_tokens = 0

    def generate_with_instruction(self, prompt, instruction):
        self.prompts.append(prompt)
        self.instructions.append(instruction)
        return self.rewrite or ""

    def generate(self, prompt):
        self.prompts.append(prompt)
        if self.raises:
            raise self.raises
        self.input_tokens += 50
        self.output_tokens += 10
        return self.answer

    def stream(self, prompt):
        self.prompts.append(prompt)
        if self.raises:
            raise self.raises
        self.input_tokens += 50
        self.output_tokens += 10
        yield self.answer


@pytest.fixture
def store(chunks, doc):
    for i, chunk in enumerate(chunks):
        chunk.chunk_id = 100 + i
    return FakeStore(chunks, doc)


def make_session(store, generator=None, **kwargs):
    return ChatSession(
        store=store,
        generator=generator or FakeGenerator(),
        embedder=FakeEmbedder(),
        **kwargs,
    )


def run(session, question):
    """Drive one turn to completion, returning the TurnResult."""
    return [piece for piece in session.ask(question)][-1]


# --- the invariant --------------------------------------------------------


def test_history_not_in_context(store):
    """Grounding prompts must contain no prior turn, question or answer."""
    generator = FakeGenerator(answer="The battery is 5000mAh [1].")
    session = make_session(store, generator)

    run(session, "how big is the battery")
    generator.prompts.clear()
    run(session, "how do I enable always on display")

    grounding = [p for p in generator.prompts if p.startswith("CONTEXT:")]
    assert grounding, "the second turn must have produced a grounding prompt"
    for prompt in grounding:
        assert "how big is the battery" not in prompt
        assert "5000mAh" not in prompt


def test_history_is_used_for_expansion(store):
    """The same history that is banned from grounding is required here."""
    generator = FakeGenerator(rewrite="does the Galaxy S24 Ultra support fast charging")
    session = make_session(store, generator)
    session.history.append(Turn("does the S24 Ultra have wireless charging", "Yes [1]."))

    run(session, "does it support fast charging too?")

    expansion = [p for p in generator.prompts if p.startswith("CONVERSATION:")]
    assert expansion, "a follow-up must trigger an expansion call"
    assert "wireless charging" in expansion[0]


def test_expanded_query_is_what_gets_searched(store):
    generator = FakeGenerator(rewrite="Galaxy S24 Ultra fast charging")
    session = make_session(store, generator, mode="bm25")
    session.history.append(Turn("tell me about the S24 Ultra", "It is a phone [1]."))

    result = run(session, "what about it?")

    assert "Galaxy S24 Ultra fast charging" in store.bm25_queries
    # The original is searched too: a bad rewrite must not lose the question.
    assert "what about it?" in store.bm25_queries
    assert result.searched_as == "Galaxy S24 Ultra fast charging"


def test_grounding_prompt_gets_the_resolved_question(store):
    """The model is asked the rewrite, not the pronoun.

    Retrieving the right chunks is not enough: asked "explain it step by step"
    over a context that never says what "it" is, a generator restricted to the
    context refuses — correctly, and uselessly.
    """
    generator = FakeGenerator(rewrite="how do I take a screenshot, step by step")
    session = make_session(store, generator)
    session.history.append(Turn("how do I take a screenshot", "Press Side + Vol Down [1]."))

    result = run(session, "can you explain it step by step")

    grounding = [p for p in generator.prompts if p.startswith("CONTEXT:")]
    assert "QUESTION: how do I take a screenshot, step by step" in grounding[0]
    # What the user typed is still what the UI shows and what the Answer records.
    assert result.question == "can you explain it step by step"
    assert result.answer.question == "can you explain it step by step"


def test_unexpanded_question_reaches_grounding_unchanged(store):
    generator = FakeGenerator()
    session = make_session(store, generator)
    run(session, "how do I take a screenshot")
    grounding = [p for p in generator.prompts if p.startswith("CONTEXT:")]
    assert "QUESTION: how do I take a screenshot" in grounding[0]


# --- expansion ------------------------------------------------------------


def test_first_question_is_never_expanded(store):
    generator = FakeGenerator(rewrite="should not be called")
    session = make_session(store, generator)
    run(session, "how do I take a screenshot")
    assert not any(p.startswith("CONVERSATION:") for p in generator.prompts)


def test_self_contained_followup_skips_the_rewrite_call():
    history = [Turn("how do I take a screenshot", "Press Side + Volume Down [1].")]
    assert looks_dependent("how do I enable dark mode on the Galaxy S24", history) is False


@pytest.mark.parametrize(
    "question",
    ["does it do that too?", "what about the S24?", "and the battery?", "why?"],
)
def test_dependent_questions_are_detected(question):
    history = [Turn("does the A52 have an SD card slot", "Yes [1].")]
    assert looks_dependent(question, history) is True


def test_expansion_failure_falls_back_to_the_raw_question():
    class Broken:
        def generate_with_instruction(self, prompt, instruction):
            raise RuntimeError("503 UNAVAILABLE")

    history = [Turn("does the A52 have an SD slot", "Yes [1].")]
    expansion = expand_query("what about it?", history, Broken())
    assert expansion.queries == ["what about it?"]


def test_expansion_uses_a_rewriting_instruction_not_the_citation_rules(store):
    generator = FakeGenerator(rewrite="something explicit")
    session = make_session(store, generator)
    session.history.append(Turn("q", "a"))
    run(session, "what about it?")
    assert "Output ONLY the rewritten question" in generator.instructions[0]


def test_history_render_truncates_long_answers():
    rendered = render_history([Turn("q", "x" * 1000)])
    assert len(rendered) < 400


def test_only_recent_turns_are_rendered():
    history = [Turn(f"question {i}", f"answer {i}") for i in range(10)]
    rendered = render_history(history, max_turns=2)
    assert "question 9" in rendered and "question 3" not in rendered


# --- mode toggle ----------------------------------------------------------


def test_mode_toggle_changes_results(store):
    """The sidebar toggle must actually reach the retriever."""
    bm25_session = make_session(store, mode="bm25")
    dense_session = make_session(store, mode="dense")

    bm25_result = run(bm25_session, "screenshot")
    dense_result = run(dense_session, "screenshot")

    assert bm25_result.bm25_count > 0 and bm25_result.dense_count == 0
    assert dense_result.dense_count > 0 and dense_result.bm25_count == 0
    # The fake store deliberately reverses dense order, so the top hit differs.
    bm25_top = bm25_result.answer.retrieved[0].chunk.chunk_id
    dense_top = dense_result.answer.retrieved[0].chunk.chunk_id
    assert bm25_top != dense_top


def test_model_filter_reaches_retrieval(store, doc):
    session = make_session(store, mode="bm25", model_filter="Galaxy S24 Ultra")
    result = run(session, "battery")
    assert result.answer is not None


def test_top_k_limits_the_context(store):
    session = make_session(store, mode="bm25", top_k=2)
    result = run(session, "battery")
    assert len(result.answer.retrieved) == 2


# --- citation cards -------------------------------------------------------


def test_citation_card_mapping(store, chunks):
    """Each [n] must render the chunk it actually came from."""
    generator = FakeGenerator(answer="First [1]. Second [2].")
    session = make_session(store, generator, mode="bm25")
    result = run(session, "anything")

    citations = result.answer.citations
    retrieved = result.answer.retrieved
    assert len(citations) == 2
    for citation in citations:
        source = retrieved[citation.marker - 1].chunk
        assert citation.chunk_id == source.chunk_id
        assert citation.page_start == source.page_start
        assert citation.snippet.startswith(source.text[:20])


def test_citation_names_the_manual_it_came_from(store, doc):
    generator = FakeGenerator(answer="Fact [1].")
    session = make_session(store, generator, mode="bm25")
    result = run(session, "anything")
    assert result.answer.citations[0].model == doc.model


# --- errors ---------------------------------------------------------------


def test_api_failure_handled_and_session_survives(store):
    from query.generate import GenerationError

    generator = FakeGenerator(raises=GenerationError("429 RESOURCE_EXHAUSTED"))
    session = make_session(store, generator, mode="bm25")

    result = run(session, "anything")
    assert result.error and "rate limit" in result.error.lower()
    assert result.answer is None

    # The conversation must still be usable afterwards.
    generator.raises = None
    second = run(session, "anything else")
    assert second.error is None and second.answer is not None


def test_failed_turn_is_not_remembered_as_context(store):
    from query.generate import GenerationError

    generator = FakeGenerator(raises=GenerationError("503 UNAVAILABLE"))
    session = make_session(store, generator, mode="bm25")
    run(session, "anything")
    assert session.history == []


def test_retrieval_failure_is_reported_not_raised(store):
    def broken(*args, **kwargs):
        raise RuntimeError("no such column: TA845")

    store.search_bm25 = broken
    session = make_session(store, mode="bm25")
    result = run(session, "EP-TA845")
    assert result.error and "Search failed" in result.error


def test_empty_question_is_rejected_without_calling_the_model(store):
    generator = FakeGenerator()
    session = make_session(store, generator)
    result = run(session, "   ")
    assert result.error and generator.prompts == []


@pytest.mark.parametrize(
    "message,expected",
    [
        ("429 RESOURCE_EXHAUSTED", "rate limit"),
        ("503 UNAVAILABLE", "busy"),
        ("404 NOT_FOUND", "GEN_MODEL"),
        ("PERMISSION_DENIED", "GEMINI_API_KEY"),
    ],
)
def test_errors_say_what_to_do(message, expected):
    assert expected in _friendly_error(message)


# --- accounting -----------------------------------------------------------


def test_cost_accumulates_across_turns(store):
    session = make_session(store, mode="bm25")
    run(session, "one")
    run(session, "two")
    assert session.total_input_tokens == 100
    assert session.total_output_tokens == 20


def test_reset_clears_history_and_turns(store):
    session = make_session(store, mode="bm25")
    run(session, "one")
    session.reset()
    assert session.history == [] and session.turns == []


# --- startup guards -------------------------------------------------------


def test_missing_index_message_says_how_to_build_one(tmp_path):
    problem = check_store_ready(tmp_path / "nope")
    assert problem is not None
    message, command = problem
    assert "No search index" in message
    assert "-m ingest" in command


def test_empty_index_message(tmp_path, store):
    """An index that exists but holds nothing is a different failure."""
    store.count_chunks = lambda: 0
    problem = check_store_ready(tmp_path, store)
    assert problem is not None and "empty" in problem[0]


def test_healthy_store_reports_no_problem(tmp_path, store):
    store.count_chunks = lambda: 4630
    assert check_store_ready(tmp_path, store) is None
