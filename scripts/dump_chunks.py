"""Print a random sample of chunks for human inspection.

The Phase 2 exit gate is a person reading these. No assertion catches a chunk
that is well-formed but incoherent, and incoherent chunks are invisible until
Phase 5, where they look like a generation problem.

    python -m scripts.dump_chunks --sample 30
    python -m scripts.dump_chunks --manual S93X --sample 10 --full
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import load_settings  # noqa: E402
from core.logging_setup import setup_logging  # noqa: E402
from ingest.chunk import chunk_document  # noqa: E402
from ingest.parse import parse_pdf  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=30)
    parser.add_argument("--manual", help="substring of a filename to restrict to")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--full", action="store_true", help="print whole chunk text")
    parser.add_argument("--stats", action="store_true", help="only print statistics")
    args = parser.parse_args(argv)

    setup_logging("WARNING")
    settings = load_settings(require_api_key=False)

    pdfs = sorted(settings.raw_dir.glob("*.pdf"))
    if args.manual:
        pdfs = [p for p in pdfs if args.manual.lower() in p.name.lower()]
    if not pdfs:
        print("No manuals matched. Run `python -m ingest.acquire` first.")
        return 1

    chunks = []
    for pdf in pdfs:
        parsed = parse_pdf(pdf)
        chunks.extend(chunk_document(parsed, doc_id=pdf.stem))

    tokens = sorted(c.token_count for c in chunks)
    print(f"\n{len(chunks)} chunks from {len(pdfs)} manual(s)")
    print(
        f"tokens  min {tokens[0]}  p25 {tokens[len(tokens)//4]}  "
        f"p50 {int(statistics.median(tokens))}  p95 {tokens[int(len(tokens)*0.95)]}  "
        f"max {tokens[-1]}"
    )
    print(
        f"under 50 tokens: {sum(1 for t in tokens if t < 50)}  |  "
        f"over 800: {sum(1 for t in tokens if t > 800)}  |  "
        f"no section path: {sum(1 for c in chunks if not c.section_path)}"
    )
    if args.stats:
        return 0

    random.seed(args.seed)
    for i, chunk in enumerate(random.sample(chunks, min(args.sample, len(chunks))), 1):
        body = chunk.text if args.full else chunk.text[:600]
        print("\n" + "=" * 78)
        print(f"[{i}] {chunk.doc_id[:44]}")
        print(f"    {chunk.section_path}")
        print(f"    p.{chunk.page_start}-{chunk.page_end}  {chunk.token_count} tokens")
        print("-" * 78)
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
