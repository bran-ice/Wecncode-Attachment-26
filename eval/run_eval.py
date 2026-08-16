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
    if not any(term.lower() in haystack for term in question.expect):
        return False
    if question.expect_text:
        body = hit.chunk.text.lower()
        return any(term.lower() in body for term in question.expect_text)
    return True


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["bm25", "dense", "hybrid", "all"], default="all")
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("--json", type=Path, help="write results as JSON")
    args = parser.parse_args(argv)

    setup_logging("WARNING")
    settings = load_settings(require_api_key=False)
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

    if args.json:
        args.json.write_text(
            json.dumps([r.__dict__ for r in results], indent=2), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
