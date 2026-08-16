"""Build the searchable store from the manuals in `data/raw/`.

    python -m ingest              # parse, chunk, embed, index
    python -m ingest --dry-run    # everything except the Gemini calls
    python -m ingest --limit 2    # first two manuals, for a fast smoke test

The store is assembled in a staging directory and swapped into place only on
success, so the query side never reads a half-built index and a crash here
leaves the previous store serving.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from core.config import load_settings
from core.logging_setup import get_logger, setup_logging
from core.schema import Document
from core.storage import staging_store
from ingest.acquire import load_manifest
from ingest.chunk import chunk_document
from ingest.embed import BATCH_SIZE, EmbeddingCache, build_embedder
from ingest.parse import parse_pdf

log = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="only the first N manuals")
    parser.add_argument(
        "--dry-run", action="store_true", help="parse and chunk only; no API calls"
    )
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args(argv)

    settings = load_settings(require_api_key=False)
    setup_logging(settings.log_level)
    started = time.monotonic()

    records = list(load_manifest(settings.catalog_dir).values())
    if not records:
        log.error(
            "No manuals in the manifest. Run `python -m ingest.acquire --scan` first."
        )
        return 1
    records.sort(key=lambda r: r.filename)
    if args.limit:
        records = records[: args.limit]

    # Parse and chunk everything first: it is free, and a failure here should
    # surface before any Gemini quota is spent.
    documents: list[Document] = []
    chunks_by_doc = []
    for record in records:
        pdf = settings.raw_dir / record.filename
        if not pdf.exists():
            log.warning("Missing %s — skipping", record.filename)
            continue
        parsed = parse_pdf(pdf)
        chunks = chunk_document(parsed, doc_id=record.doc_id)
        if not chunks:
            log.warning("No chunks from %s — skipping", record.filename)
            continue
        documents.append(
            Document(
                doc_id=record.doc_id,
                model=record.model,
                title=record.title,
                url=record.url,
                sha256=record.sha256,
                n_pages=record.n_pages,
                language=record.language,
                region=record.region,
                os_version=record.os_version,
            )
        )
        chunks_by_doc.append(chunks)

    total = sum(len(c) for c in chunks_by_doc)
    log.info("Parsed %d manuals into %d chunks", len(documents), total)
    if not total:
        log.error("Nothing to index.")
        return 1

    cache = EmbeddingCache(settings.data_root / "cache" / "embeddings.db")
    embedder = None
    if not args.dry_run:
        embedder = build_embedder(settings, cache=cache)
        log.info(
            "Embedding backend: %s",
            settings.embed_model if settings.embed_backend == "gemini"
            else settings.local_embed_model,
        )

    with staging_store(settings.store_dir) as store:
        store.set_meta("embed_model", settings.embed_model)
        store.set_meta("chunker", "section-aware v1")

        all_ids: list[int] = []
        all_texts: list[str] = []
        for document, chunks in zip(documents, chunks_by_doc):
            store.add_document(document)
            ids = store.add_chunks(chunks)
            all_ids.extend(ids)
            all_texts.extend(c.embed_text() for c in chunks)

        log.info("Wrote %d chunks to %s", len(all_ids), store.db_path.name)

        if args.dry_run:
            log.info("Dry run: skipping embeddings and vector index")
            # A store without vectors is still useful — keyword search works —
            # but say so plainly rather than leaving it to be discovered later.
            store.set_meta("vector_index", "absent (dry run)")
        else:
            vectors = embedder.embed_texts(all_texts, batch_size=args.batch_size)
            log.info(
                "Embeddings ready: %d vectors, %d API calls, %d cache hits",
                len(vectors),
                embedder.api_calls,
                embedder.cached_hits,
            )
            store.set_meta("embed_backend", settings.embed_backend)
            store.build_vector_index(all_ids, vectors)

    cache.close()
    elapsed = time.monotonic() - started
    log.info("Store built in %.0fs -> %s", elapsed, settings.store_dir)
    print(
        f"\n{len(documents)} manuals, {total} chunks"
        + ("" if args.dry_run else f", {embedder.dim}-dim vectors")
        + f" in {settings.store_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
