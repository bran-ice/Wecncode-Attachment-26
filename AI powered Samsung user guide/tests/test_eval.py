"""Phase 7 — the evaluation harness itself.

The eval is the project's evidence, so its arithmetic needs checking as much as
the code it measures. Everything here runs on fixtures and hand-computed
numbers; no store, no API.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.schema import Answer, Chunk, Citation, RetrievedChunk  # noqa: E402
from eval.generation import AnswerRecord, GenerationResult, score_citations  # noqa: E402
from eval.run_eval import (  # noqa: E402
    ArmResult,
    Question,
    check_regression,
    is_hit,
    load_questions,
    rank_of_first_hit,
)


def chunk(text="body", section="Settings > Lock screen", chunk_id=1):
    return Chunk(
        doc_id="d1", text=text, section_path=section,
        page_start=10, page_end=10, chunk_id=chunk_id,
    )


def hit(text="body", section="Settings > Lock screen", chunk_id=1, rank=0):
    return RetrievedChunk(
        chunk=chunk(text, section, chunk_id), score=1.0, source="rrf", rank=rank
    )


# --- the question set -----------------------------------------------------


def test_all_question_types_covered():
    """Each type needs enough questions for its metric to mean anything."""
    questions = load_questions()
    counts = {}
    for question in questions:
        counts[question.type] = counts.get(question.type, 0) + 1
    for expected in ("factual", "procedural", "spec", "unanswerable"):
        assert counts.get(expected, 0) >= 8, f"{expected}: {counts.get(expected, 0)}"


def test_question_ids_are_unique():
    ids = [q.id for q in load_questions()]
    assert len(ids) == len(set(ids))


def test_unanswerable_questions_carry_no_gold_labels():
    """An unanswerable question with an `expect` term is a mislabelled question."""
    for question in load_questions():
        if question.type == "unanswerable":
            assert question.expect == []
        else:
            # Either label alone is a valid gold: `expect_text` on its own is how
            # a pure verbatim-string question is labelled.
            assert question.expect or question.expect_text, f"{question.id} has no gold label"


# --- retrieval metric arithmetic ------------------------------------------


def test_rank_of_first_hit_is_one_based():
    question = Question(id="q", type="factual", question="q", expect=["Lock screen"])
    hits = [hit(section="Apps > Bixby"), hit(section="Settings > Lock screen")]
    assert rank_of_first_hit(question, hits) == 2


def test_rank_is_none_when_nothing_matches():
    question = Question(id="q", type="factual", question="q", expect=["Camera"])
    assert rank_of_first_hit(question, [hit()]) is None


def test_is_hit_matches_section_or_body():
    """Phase 2 merges short subsections, so the term can land in either."""
    question = Question(id="q", type="factual", question="q", expect=["Software update"])
    assert is_hit(question, hit(section="Settings", text="Software update: tap here"))
    assert is_hit(question, hit(section="Settings > Software update", text="tap here"))


def test_expect_text_alone_is_a_valid_gold_label():
    """A verbatim lookup may have no section worth naming — only the string."""
    question = Question(
        id="q", type="spec", question="SM-A155F", expect=[], expect_text=["SM-A155F"]
    )
    assert is_hit(question, hit(section="Specs", text="model SM-A155F here"))
    assert not is_hit(question, hit(section="Specs", text="something else"))


def test_expect_text_narrows_a_coarse_section():
    question = Question(
        id="q", type="spec", question="q",
        expect=["Battery"], expect_text=["EP-TA845"],
    )
    assert not is_hit(question, hit(section="Settings > Battery", text="charge it"))
    assert is_hit(question, hit(section="Settings > Battery", text="use EP-TA845"))


@pytest.mark.parametrize(
    "ranks,expected_mrr",
    [
        ([1, 1, 1], 1.0),
        ([2, 2], 0.5),
        ([1, 2, 4], (1 + 0.5 + 0.25) / 3),
        ([None, 1], 0.5),
    ],
)
def test_metrics_math_mrr(ranks, expected_mrr):
    """MRR is the mean of 1/rank, with a miss scoring zero."""
    reciprocals = [0.0 if r is None else 1.0 / r for r in ranks]
    assert sum(reciprocals) / len(reciprocals) == pytest.approx(expected_mrr)


@pytest.mark.parametrize(
    "ranks,expected_recall",
    [([1, 2, 5], 1.0), ([1, 6, None], 1 / 3), ([None, None], 0.0)],
)
def test_metrics_math_recall_at_5(ranks, expected_recall):
    hits = sum(1 for r in ranks if r is not None and r <= 5)
    assert hits / len(ranks) == pytest.approx(expected_recall)


# --- regression guard -----------------------------------------------------


def _arm(name="Hybrid (RRF)", recall_at_5=0.93):
    return ArmResult(
        name=name, recall_at_1=0.78, recall_at_5=recall_at_5, mrr=0.844,
        latency_p50=56, latency_p95=75, answerable=54, misses=[],
    )


def test_regression_passes_when_recall_holds(tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"Hybrid (RRF)": {"recall_at_5": 0.93, "mrr": 0.844}}))
    assert check_regression([_arm(recall_at_5=0.93)], baseline) == []


def test_regression_tolerates_small_noise(tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"Hybrid (RRF)": {"recall_at_5": 0.93, "mrr": 0.844}}))
    assert check_regression([_arm(recall_at_5=0.90)], baseline) == []


def test_regression_fails_on_a_real_drop(tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"Hybrid (RRF)": {"recall_at_5": 0.93, "mrr": 0.844}}))
    problems = check_regression([_arm(recall_at_5=0.80)], baseline)
    assert len(problems) == 1 and "below the baseline" in problems[0]


def test_missing_baseline_is_not_a_failure(tmp_path):
    assert check_regression([_arm()], tmp_path / "absent.json") == []


# --- generation metrics ---------------------------------------------------


def _answer(citations, retrieved):
    return Answer(question="q", text="text", citations=citations, retrieved=retrieved)


def _citation(marker, chunk_id):
    return Citation(
        marker=marker, chunk_id=chunk_id, model="Galaxy S24 Ultra",
        page_start=10, page_end=10, section_path="Settings > Lock screen", snippet="s",
    )


def test_citation_scored_against_the_chunk_it_points_at():
    question = Question(id="q", type="factual", question="q", expect=["Lock screen"])
    retrieved = [
        hit(section="Settings > Lock screen", chunk_id=1),
        hit(section="Apps > Bixby", chunk_id=2),
    ]
    answer = _answer([_citation(1, 1), _citation(2, 2)], retrieved)
    # One citation is on-topic, the other points at an unrelated chunk.
    assert score_citations(answer, is_hit, question) == 1


def test_citation_to_a_chunk_not_in_context_scores_zero():
    question = Question(id="q", type="factual", question="q", expect=["Lock screen"])
    answer = _answer([_citation(1, 99)], [hit(chunk_id=1)])
    assert score_citations(answer, is_hit, question) == 0


def _record(**kwargs):
    defaults = dict(
        question_id="q", question="q?", type="factual", text="t",
        refused=False, citations=0, good_citations=0,
    )
    return AnswerRecord(**{**defaults, **kwargs})


def test_citation_accuracy_aggregates_over_citations_not_answers():
    """One answer with 4 bad citations must not be hidden by three clean ones."""
    result = GenerationResult(records=[
        _record(citations=4, good_citations=0),
        _record(citations=1, good_citations=1),
        _record(citations=1, good_citations=1),
    ])
    assert result.citation_accuracy == pytest.approx(2 / 6)


def test_refusal_rate_counts_only_unanswerable():
    result = GenerationResult(records=[
        _record(type="unanswerable", refused=True),
        _record(type="unanswerable", refused=False),
        _record(type="factual", refused=False),
    ])
    assert result.refusal_rate == pytest.approx(0.5)


def test_false_refusal_rate_counts_only_answerable():
    """Refusing everything would otherwise score a perfect refusal rate."""
    result = GenerationResult(records=[
        _record(type="unanswerable", refused=True),
        _record(type="factual", refused=True),
        _record(type="procedural", refused=False),
    ])
    assert result.refusal_rate == 1.0
    assert result.false_refusal_rate == pytest.approx(0.5)


def test_uncited_claim_rate_ignores_refusals_and_errors():
    result = GenerationResult(records=[
        _record(uncited=["bare claim"]),
        _record(refused=True),
        _record(error="503"),
        _record(),
    ])
    assert result.uncited_claim_rate == pytest.approx(0.5)


def test_cost_per_query_excludes_failed_calls():
    result = GenerationResult(records=[
        _record(input_tokens=1_000_000, output_tokens=0),
        _record(error="503", input_tokens=0),
    ])
    assert result.cost_per_query == pytest.approx(0.30)


def test_latency_percentiles_ignore_errors():
    result = GenerationResult(records=[
        _record(latency_ms=100), _record(latency_ms=200),
        _record(latency_ms=999999, error="503"),
    ])
    assert result.latency(0.5) == 200


def test_citation_accuracy_is_none_for_an_uncited_answer():
    assert _record(citations=0).citation_accuracy is None


# --- partial runs ---------------------------------------------------------


def test_refusal_rate_excludes_errored_questions():
    """A 429 is the API declining, not the model failing to refuse."""
    result = GenerationResult(records=[
        _record(type="unanswerable", refused=True),
        _record(type="unanswerable", error="daily quota exhausted"),
    ])
    assert result.refusal_rate == 1.0


def test_refusal_rate_is_none_when_nothing_ran():
    """Better no number than a 0.00 that reads as total failure to refuse."""
    result = GenerationResult(records=[
        _record(type="unanswerable", error="daily quota exhausted"),
    ])
    assert result.refusal_rate is None


def test_completed_and_errors_split_the_records():
    result = GenerationResult(records=[_record(), _record(error="503")])
    assert len(result.completed) == 1 and len(result.errors) == 1


def test_round_robin_covers_every_type_early():
    """A quota-limited run must not spend its budget on one question type."""
    from eval.run_eval import _round_robin_by_type

    questions = (
        [Question(id=f"p{i}", type="procedural", question="q", expect=["x"]) for i in range(28)]
        + [Question(id=f"u{i}", type="unanswerable", question="q") for i in range(10)]
        + [Question(id=f"s{i}", type="spec", question="q", expect=["x"]) for i in range(10)]
    )
    first_ten = _round_robin_by_type(questions)[:10]
    assert {q.type for q in first_ten} == {"procedural", "unanswerable", "spec"}


def test_round_robin_keeps_every_question():
    from eval.run_eval import _round_robin_by_type

    questions = load_questions()
    assert sorted(q.id for q in _round_robin_by_type(questions)) == sorted(
        q.id for q in questions
    )
