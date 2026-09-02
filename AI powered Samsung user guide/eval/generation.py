"""Measure the generated answer, not just the retrieval that fed it.

Retrieval metrics stop one step short of what the system promises. Recall@5
says the right page was in the context; it says nothing about whether the answer
used it, cited it, or made something up alongside it. The four measures here are
the ones that close that gap:

* **Citation accuracy** — does a `[n]` point at a chunk that actually bears on
  the question? Scored against the same gold `expect` terms retrieval is scored
  on, so a citation to a chunk that would have counted as a retrieval miss
  counts as a bad citation. This is a *proxy*: it asks whether the cited page is
  on-topic, not whether the specific sentence is supported by it. Reading is the
  only way to check the latter, which is why `--dump` exists.
* **Uncited claims** — sentences asserting something with no marker. The Phase 5
  exit gate is that this is zero.
* **Refusal rate** — on the unanswerable questions, refusing is correct. Split
  from *false refusals* on answerable ones, because a system that refuses
  everything would otherwise score perfectly.
* **Cost and latency** — per answered question, since this is what the thing
  costs to run.

Every number here comes from real API calls, so this module is never imported
by the default test suite.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Optional, Sequence

from core.logging_setup import get_logger
from core.schema import Answer
from query.generate import (
    QuotaExhausted,
    answer_question,
    estimate_cost,
    uncited_sentences,
)
from query.retrieve import retrieve

log = get_logger(__name__)

CONTEXT_K = 5


@dataclass
class AnswerRecord:
    """One question's generated answer, scored."""

    question_id: str
    question: str
    type: str
    text: str
    refused: bool
    citations: int
    good_citations: int
    uncited: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None

    @property
    def cost(self) -> float:
        return estimate_cost(self.input_tokens, self.output_tokens)

    @property
    def citation_accuracy(self) -> Optional[float]:
        if not self.citations:
            return None
        return self.good_citations / self.citations


@dataclass
class GenerationResult:
    """The generation arm, aggregated."""

    records: list[AnswerRecord] = field(default_factory=list)
    stopped_early: bool = False

    @property
    def answerable(self) -> list[AnswerRecord]:
        return [r for r in self.records if r.type != "unanswerable"]

    @property
    def unanswerable(self) -> list[AnswerRecord]:
        return [r for r in self.records if r.type == "unanswerable"]

    @property
    def citation_accuracy(self) -> float:
        """Over answerable questions with at least one citation."""
        scored = [r for r in self.answerable if r.citations]
        if not scored:
            return 0.0
        return sum(r.good_citations for r in scored) / sum(r.citations for r in scored)

    @property
    def uncited_claim_rate(self) -> float:
        answered = [r for r in self.answerable if not r.refused and not r.error]
        if not answered:
            return 0.0
        return sum(1 for r in answered if r.uncited) / len(answered)

    @property
    def refusal_rate(self) -> Optional[float]:
        """Correct refusals, over unanswerable questions that actually ran.

        Errored questions are excluded, not counted as failures to refuse. A
        429 is the API declining to answer, not the model inventing one, and
        scoring it as the latter turns a quota problem into a phantom
        hallucination problem. None means nothing ran.
        """
        asked = [r for r in self.unanswerable if not r.error]
        if not asked:
            return None
        return sum(1 for r in asked if r.refused) / len(asked)

    @property
    def errors(self) -> list[AnswerRecord]:
        return [r for r in self.records if r.error]

    @property
    def completed(self) -> list[AnswerRecord]:
        return [r for r in self.records if not r.error]

    @property
    def false_refusal_rate(self) -> float:
        """Refusals on questions the manuals *do* cover — the cost of caution."""
        answerable = [r for r in self.answerable if not r.error]
        if not answerable:
            return 0.0
        return sum(1 for r in answerable if r.refused) / len(answerable)

    @property
    def uncited_total(self) -> int:
        return sum(len(r.uncited) for r in self.answerable)

    def latency(self, percentile: float) -> float:
        values = sorted(r.latency_ms for r in self.records if not r.error)
        if not values:
            return 0.0
        index = min(int(len(values) * percentile), len(values) - 1)
        return values[index]

    @property
    def cost_per_query(self) -> float:
        scored = [r for r in self.records if not r.error]
        return statistics.mean([r.cost for r in scored]) if scored else 0.0


def score_citations(answer: Answer, is_hit_fn, question) -> int:
    """How many of the answer's citations point at an on-topic chunk.

    The citation carries a `chunk_id`; the retrieved chunks carry the text the
    gold labels match against, so scoring joins the two rather than trusting
    either alone.
    """
    by_id = {
        hit.chunk.chunk_id: hit for hit in answer.retrieved if hit.chunk.chunk_id is not None
    }
    good = 0
    for citation in answer.citations:
        hit = by_id.get(citation.chunk_id)
        if hit is not None and is_hit_fn(question, hit):
            good += 1
    return good


def run_generation_arm(
    questions: Sequence,
    store,
    embedder,
    generator,
    is_hit_fn,
    mode: str = "hybrid",
    top_k: int = CONTEXT_K,
    on_record=None,
) -> GenerationResult:
    """Generate an answer for every question and score it.

    Failures are recorded, not raised: one 503 late in a 64-question run should
    not throw away the preceding sixty.
    """
    result = GenerationResult()

    for question in questions:
        started = time.monotonic()
        record = AnswerRecord(
            question_id=question.id,
            question=question.question,
            type=question.type,
            text="",
            refused=False,
            citations=0,
            good_citations=0,
        )
        try:
            retrieval = retrieve(
                store, question.question, embedder=embedder, mode=mode, top_k=top_k
            )
            answer = answer_question(
                question.question, retrieval.chunks, generator, store=store
            )
            record.text = answer.text
            record.refused = answer.refused
            record.citations = len(answer.citations)
            record.good_citations = score_citations(answer, is_hit_fn, question)
            record.uncited = uncited_sentences(answer.text)
            record.latency_ms = answer.latency_ms or (time.monotonic() - started) * 1000
            record.input_tokens = answer.input_tokens or 0
            record.output_tokens = answer.output_tokens or 0
        except QuotaExhausted as exc:
            # Every remaining question would fail identically. Stop and keep
            # what completed, rather than filling the results with noise.
            log.warning("Daily quota exhausted at %s; stopping", question.id)
            record.error = "daily quota exhausted"
            result.records.append(record)
            if on_record:
                on_record(record)
            result.stopped_early = True
            return result
        except Exception as exc:
            log.warning("%s failed: %s", question.id, exc)
            record.error = str(exc)[:200]
            record.latency_ms = (time.monotonic() - started) * 1000

        result.records.append(record)
        if on_record:
            on_record(record)

    return result
