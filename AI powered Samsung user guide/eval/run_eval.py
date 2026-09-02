"""Measure retrieval quality, and produce the ablation table.

The point of this file is the comparison, not any single number. Absolute
recall depends on the corpus and on how the questions were written; what the
project actually claims is *relative*: that fusing keyword and vector search
beats either alone, and that reranking sharpens the top of the list.

    python -m eval.run_eval                 # all four arms
    python -m eval.run_eval --mode hybrid   # one arm
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import load_settings  # noqa: E402
from core.logging_setup import setup_logging  # noqa: E402
from core.schema import RetrievedChunk  # noqa: E402
from core.storage import Store  # noqa: E402
from ingest.embed import build_embedder  # noqa: E402
from query.rerank import build_reranker  # noqa: E402
from query.retrieve import retrieve  # noqa: E402

QUESTIONS = Path(__file__).parent / "questions.yaml"


@dataclass
class Question:
    id: str
    type: str
    question: str
    expect: list[str] = field(default_factory=list)
    expect_text: list[str] = field(default_factory=list)

    @property
    def answerable(self) -> bool:
        return self.type != "unanswerable"


def load_questions(path: Path = QUESTIONS) -> list[Question]:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Question(**entry) for entry in raw]


def is_hit(question: Question, hit: RetrievedChunk) -> bool:
    """A chunk counts as correct if its section path carries any expected term.

    Section paths, not chunk ids: ids change on every re-index, and the right
    answer does not. `expect_text` narrows it where a section is too coarse.
    """
    # Match against the path *and* the body: Phase 2 merges short sibling
    # subsections under their parent, so "Settings > Software update" can arrive
    # as "Settings" with "Software update:" inline. The chunk genuinely covers
    # the topic either way, and scoring it a miss would understate retrieval.
    haystack = f"{hit.chunk.section_path} {hit.chunk.text}".lower()
    # An empty `expect` means the gold label is `expect_text` alone — a question
    # whose right answer is a literal string with no useful section to name.
    # Requiring both would score such a question a miss no matter what came
    # back, silently deflating every arm on exactly the verbatim lookups the
    # hybrid claim rests on.
    if question.expect and not any(term.lower() in haystack for term in question.expect):
        return False
    if question.expect_text:
        body = hit.chunk.text.lower()
        return any(term.lower() in body for term in question.expect_text)
    return bool(question.expect)


def rank_of_first_hit(question: Question, hits: list[RetrievedChunk]) -> int | None:
    for position, hit in enumerate(hits, 1):
        if is_hit(question, hit):
            return position
    return None


@dataclass
class ArmResult:
    name: str
    recall_at_1: float
    recall_at_5: float
    mrr: float
    latency_p50: float
    latency_p95: float
    answerable: int
    misses: list[str]


def run_arm(
    name: str, mode: str, rerank: bool, store, embedder, questions: list[Question],
    reranker=None,
) -> ArmResult:
    hits_at_1 = hits_at_5 = 0
    reciprocals: list[float] = []
    latencies: list[float] = []
    misses: list[str] = []
    answerable = [q for q in questions if q.answerable]

    for question in answerable:
        started = time.monotonic()
        result = retrieve(
            store, question.question, embedder=embedder, mode=mode, top_k=20
        )
        chunks = result.chunks
        if rerank and reranker is not None:
            chunks = reranker.rerank(question.question, chunks, top_k=5)
        else:
            chunks = chunks[:5]
        latencies.append((time.monotonic() - started) * 1000)

        rank = rank_of_first_hit(question, chunks)
        if rank == 1:
            hits_at_1 += 1
        if rank is not None and rank <= 5:
            hits_at_5 += 1
            reciprocals.append(1.0 / rank)
        else:
            reciprocals.append(0.0)
            misses.append(question.id)

    total = len(answerable)
    ordered = sorted(latencies)
    return ArmResult(
        name=name,
        recall_at_1=hits_at_1 / total,
        recall_at_5=hits_at_5 / total,
        mrr=statistics.mean(reciprocals) if reciprocals else 0.0,
        latency_p50=statistics.median(ordered) if ordered else 0.0,
        latency_p95=ordered[int(len(ordered) * 0.95)] if ordered else 0.0,
        answerable=total,
        misses=misses,
    )


BASELINE = Path(__file__).parent / "baseline.json"
CHECKPOINT = Path(__file__).parent / "generation_checkpoint.json"
# A drop this large is a regression, not corpus noise. Recorded against the
# hybrid arm because that is the one that ships.
REGRESSION_TOLERANCE = 0.05


def check_regression(results: list[ArmResult], baseline_path: Path = BASELINE) -> list[str]:
    """Compare against the recorded baseline. Returns the failures, if any."""
    if not baseline_path.exists():
        return []
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    problems = []
    for result in results:
        recorded = baseline.get(result.name)
        if not recorded:
            continue
        drop = recorded["recall_at_5"] - result.recall_at_5
        if drop > REGRESSION_TOLERANCE:
            problems.append(
                f"{result.name}: Recall@5 {result.recall_at_5:.2f} is "
                f"{drop:.2f} below the baseline {recorded['recall_at_5']:.2f}"
            )
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["bm25", "dense", "hybrid", "all"], default="all")
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("--json", type=Path, help="write results as JSON")
    parser.add_argument(
        "--generate", action="store_true",
        help="also run the generation arm: citation accuracy, refusals, cost (costs API calls)",
    )
    parser.add_argument(
        "--dump", type=Path, help="with --generate, write every answer for reading",
    )
    parser.add_argument(
        "--write-baseline", action="store_true",
        help="record this run as the regression baseline",
    )
    parser.add_argument(
        "--gen-model", help="override GEN_MODEL for the generation arm only",
    )
    parser.add_argument(
        "--gen-limit", type=int,
        help="stop after N generated answers — free-tier quotas are per day",
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="ignore the generation checkpoint and start over",
    )
    args = parser.parse_args(argv)

    setup_logging("WARNING")
    settings = load_settings(require_api_key=args.generate)
    questions = load_questions()
    print(
        f"{len(questions)} questions "
        f"({sum(1 for q in questions if q.answerable)} answerable, "
        f"{sum(1 for q in questions if not q.answerable)} unanswerable)\n"
    )

    embedder = build_embedder(settings)
    arms = (
        [("BM25 only", "bm25", False), ("Dense only", "dense", False),
         ("Hybrid (RRF)", "hybrid", False), ("Hybrid + rerank", "hybrid", True)]
        if args.mode == "all"
        else [(args.mode, args.mode, not args.no_rerank)]
    )
    reranker = build_reranker(enabled=any(a[2] for a in arms))

    results: list[ArmResult] = []
    with Store(settings.store_dir) as store:
        for name, mode, rerank in arms:
            result = run_arm(name, mode, rerank, store, embedder, questions, reranker)
            results.append(result)
            print(
                f"{result.name:18} R@1 {result.recall_at_1:.2f}  "
                f"R@5 {result.recall_at_5:.2f}  MRR {result.mrr:.3f}  "
                f"p50 {result.latency_p50:5.0f}ms"
            )

    print("\n| Arm | Recall@1 | Recall@5 | MRR | p50 | p95 |")
    print("|---|---|---|---|---|---|")
    for r in results:
        print(
            f"| {r.name} | {r.recall_at_1:.2f} | {r.recall_at_5:.2f} | {r.mrr:.3f} "
            f"| {r.latency_p50:.0f}ms | {r.latency_p95:.0f}ms |"
        )

    if results[-1].misses:
        print(f"\nMissed by {results[-1].name}: {', '.join(results[-1].misses)}")

    if problems := check_regression(results):
        print("\nREGRESSION against eval/baseline.json:")
        for problem in problems:
            print(f"  {problem}")

    if args.write_baseline:
        BASELINE.write_text(
            json.dumps(
                {r.name: {"recall_at_5": r.recall_at_5, "mrr": r.mrr} for r in results},
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nBaseline written to {BASELINE}")

    if args.generate:
        _run_generation(settings, questions, embedder, args.dump, args)

    if args.json:
        args.json.write_text(
            json.dumps([r.__dict__ for r in results], indent=2), encoding="utf-8"
        )
    return 1 if problems else 0


def _round_robin_by_type(questions: list[Question]) -> list[Question]:
    """Interleave the four question types.

    A daily quota means most runs are partial, and a partial run taken in file
    order measures whatever type happens to come first — the last attempt spent
    its whole budget on `procedural` and never asked a single unanswerable
    question, which is exactly the one that carries the refusal metric.
    """
    buckets: dict[str, list[Question]] = {}
    for question in questions:
        buckets.setdefault(question.type, []).append(question)

    ordered: list[Question] = []
    while any(buckets.values()):
        for bucket in buckets.values():
            if bucket:
                ordered.append(bucket.pop(0))
    return ordered


def _run_generation(settings, questions, embedder, dump, args) -> None:
    """The generation arm. Separate because it costs money and takes minutes."""
    from dataclasses import replace as replace_settings

    from eval.generation import AnswerRecord, GenerationResult, run_generation_arm
    from query.generate import build_generator

    # A free-tier daily quota does not stretch to 64 questions, so answers
    # accumulate across runs instead of restarting from nothing each day.
    done: dict[str, AnswerRecord] = {}
    if CHECKPOINT.exists() and not args.fresh:
        for raw in json.loads(CHECKPOINT.read_text(encoding="utf-8")):
            record = AnswerRecord(**raw)
            if not record.error:
                done[record.question_id] = record
        print(f"Resuming: {len(done)} answers already recorded in {CHECKPOINT.name}")

    if args.gen_model:
        settings = replace_settings(settings, gen_model=args.gen_model)
    pending = _round_robin_by_type([q for q in questions if q.id not in done])
    if args.gen_limit:
        pending = pending[: args.gen_limit]

    print(
        f"\nGenerating {len(pending)} answers with {settings.gen_model} "
        f"({len(done)} already recorded) — this calls the API.\n"
    )
    generator = build_generator(settings)

    def progress(record):
        mark = "REFUSED" if record.refused else ("ERROR" if record.error else "ok")
        accuracy = record.citation_accuracy
        detail = f"{record.citations} cites" + (
            f", {accuracy:.0%} on-topic" if accuracy is not None else ""
        )
        print(f"  {record.question_id:28} {mark:8} {detail}")

    with Store(settings.store_dir) as store:
        result = run_generation_arm(
            pending, store, embedder, generator, is_hit, on_record=progress
        )

    # Merge with what earlier runs collected, then checkpoint before reporting:
    # a crash in the reporting code must not cost the API calls.
    fresh = {r.question_id: r for r in result.records if not r.error}
    merged = {**done, **fresh}
    result = GenerationResult(
        records=list(merged.values()) + [r for r in result.records if r.error],
        stopped_early=result.stopped_early,
    )
    CHECKPOINT.write_text(
        json.dumps([r.__dict__ for r in merged.values()], indent=2), encoding="utf-8"
    )

    answered = len(result.completed)
    print(
        f"\n{answered}/{len(questions)} questions answered "
        f"({len(result.errors)} failed)."
    )
    if result.stopped_early:
        print(
            "Stopped early: the daily quota is exhausted. Re-run tomorrow to "
            f"continue — {CHECKPOINT.name} keeps what completed."
        )
    if answered < len(questions):
        print("PARTIAL RUN — the numbers below describe only the questions that ran.")

    print("\n| Generation metric | Value |")
    print("|---|---|")
    print(f"| Citation accuracy | {result.citation_accuracy:.2f} |")
    print(f"| Answers with an uncited claim | {result.uncited_claim_rate:.2f} |")
    refusal = result.refusal_rate
    asked = len([r for r in result.unanswerable if not r.error])
    print(
        f"| Refusal rate (unanswerable) | "
        + (f"{refusal:.2f} (n={asked})" if refusal is not None else "not measured")
        + " |"
    )
    print(f"| False refusals (answerable) | {result.false_refusal_rate:.2f} |")
    print(f"| Latency p50 | {result.latency(0.5):.0f}ms |")
    print(f"| Latency p95 | {result.latency(0.95):.0f}ms |")
    print(f"| Cost per query | ${result.cost_per_query:.5f} |")

    if bad := [r for r in result.answerable if r.uncited]:
        print(f"\nUncited claims in {len(bad)} answers:")
        for record in bad[:5]:
            print(f"  {record.question_id}: {record.uncited[0][:90]}")

    if wrong := [r for r in result.unanswerable if not r.refused and not r.error]:
        print(f"\nShould have refused but did not: {', '.join(r.question_id for r in wrong)}")

    if dump:
        lines = []
        for record in result.records:
            lines.append(f"### {record.question_id} ({record.type})")
            lines.append(f"**Q:** {record.question}\n")
            lines.append(record.error or record.text)
            lines.append(
                f"\n_{record.citations} citations, {record.good_citations} on-topic, "
                f"{len(record.uncited)} uncited claims, {record.latency_ms:.0f}ms_\n"
            )
        dump.write_text("\n".join(lines), encoding="utf-8")
        print(f"\nAnswers written to {dump} — the citation-accuracy proxy is only a proxy; read them.")


if __name__ == "__main__":
    raise SystemExit(main())
