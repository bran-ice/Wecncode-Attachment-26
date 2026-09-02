"""Throwaway CLI for iterating on retrieval without the UI in the way.

    python -m scripts.ask "how do I enable always on display"
    python -m scripts.ask --mode bm25 "EP-TA845"
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import load_settings  # noqa: E402
from core.logging_setup import setup_logging  # noqa: E402
from core.storage import Store  # noqa: E402
from ingest.embed import build_embedder  # noqa: E402
from query.generate import (  # noqa: E402
    REFUSAL_SENTINEL,
    build_generator,
    clean_refusal,
    estimate_cost,
    is_refusal,
    stream_answer,
)
from query.retrieve import retrieve  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="+")
    parser.add_argument("--mode", default="hybrid", choices=["hybrid", "bm25", "dense"])
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--model", help="restrict to manuals covering this model")
    parser.add_argument("--full", action="store_true")
    parser.add_argument(
        "--answer", action="store_true", help="generate a cited answer (calls Gemini)"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="with --answer, hide the raw chunks"
    )
    args = parser.parse_args(argv)

    setup_logging("WARNING")
    # Model output contains arrows and typographic dashes; the Windows console
    # is cp1252 and raises UnicodeEncodeError mid-stream without this.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # An answer needs the Gemini key; retrieval alone does not.
    settings = load_settings(require_api_key=args.answer)
    question = " ".join(args.question)

    embedder = build_embedder(settings) if args.mode != "bm25" else None
    answer = None
    with Store(settings.store_dir) as store:
        started = time.monotonic()
        result = retrieve(
            store, question, embedder=embedder, mode=args.mode,
            top_k=args.k, model_filter=args.model,
        )
        elapsed = (time.monotonic() - started) * 1000
        if args.answer:
            # Inside the `with`: resolving each citation's manual name reads the
            # store, and it closes on exit.
            answer = _generate(question, result.chunks, settings, store)

    print(f"\n{question!r}  [{args.mode}]  {elapsed:.0f}ms")
    print(f"bm25 {result.bm25_count} + dense {result.dense_count} candidates, "
          f"{result.collapsed_duplicates} duplicates collapsed\n")
    if not (args.answer and args.quiet):
        for i, hit in enumerate(result.chunks, 1):
            body = hit.chunk.text if args.full else hit.chunk.text[:220]
            print(f"[{i}] {hit.score:.4f}  p.{hit.chunk.page_start}-{hit.chunk.page_end}")
            print(f"    {hit.chunk.section_path}")
            print(f"    {body}\n")

    if answer is not None:
        # The prose already streamed to stdout; only the sources and the
        # accounting are left to print.
        if answer.refused:
            print("  (refused — not covered by the retrieved pages)")
        for citation in answer.citations:
            print(f"  [{citation.marker}] {citation.label()} — {citation.section_path}")
        cost = estimate_cost(answer.input_tokens or 0, answer.output_tokens or 0)
        print(
            f"\n  {answer.input_tokens}in/{answer.output_tokens}out tokens"
            f"  ~${cost:.5f}  {answer.latency_ms:.0f}ms"
        )
    return 0


def _generate(question, hits, settings, store):
    """Stream the answer to stdout as it arrives, then return the `Answer`."""
    generator = build_generator(settings)
    print("\n" + "-" * 70)
    final = None
    # Hold back the opening pieces until it is clear whether this is a refusal:
    # the sentinel is a protocol detail and should never reach the reader.
    buffer, decided = "", False
    for piece in stream_answer(question, hits, generator, store=store):
        if not isinstance(piece, str):
            final = piece
            continue
        if decided:
            print(piece, end="", flush=True)
            continue
        buffer += piece
        if len(buffer) >= len(REFUSAL_SENTINEL) + 2:
            decided = True
            print(clean_refusal(buffer) if is_refusal(buffer) else buffer,
                  end="", flush=True)
    if not decided and buffer:  # answer shorter than the sentinel
        print(clean_refusal(buffer) if is_refusal(buffer) else buffer, end="")
    print()
    return final


if __name__ == "__main__":
    raise SystemExit(main())
