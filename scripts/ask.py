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
from query.retrieve import retrieve  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="+")
    parser.add_argument("--mode", default="hybrid", choices=["hybrid", "bm25", "dense"])
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--model", help="restrict to manuals covering this model")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args(argv)

    setup_logging("WARNING")
    settings = load_settings(require_api_key=False)
    question = " ".join(args.question)

    embedder = build_embedder(settings) if args.mode != "bm25" else None
    with Store(settings.store_dir) as store:
        started = time.monotonic()
        result = retrieve(
            store, question, embedder=embedder, mode=args.mode,
            top_k=args.k, model_filter=args.model,
        )
        elapsed = (time.monotonic() - started) * 1000

    print(f"\n{question!r}  [{args.mode}]  {elapsed:.0f}ms")
    print(f"bm25 {result.bm25_count} + dense {result.dense_count} candidates, "
          f"{result.collapsed_duplicates} duplicates collapsed\n")
    for i, hit in enumerate(result.chunks, 1):
        body = hit.chunk.text if args.full else hit.chunk.text[:220]
        print(f"[{i}] {hit.score:.4f}  p.{hit.chunk.page_start}-{hit.chunk.page_end}")
        print(f"    {hit.chunk.section_path}")
        print(f"    {body}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
