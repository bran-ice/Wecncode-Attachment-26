# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A hybrid RAG system over Samsung Galaxy user manuals. Read [`Implementation.md`](./Implementation.md)
for architecture and [`Phases.md`](./Phases.md) for the build checklist — **`Phases.md` is
the source of truth for what's done and what's next.** Check the boxes as you complete
work, and record what a phase's exit gate actually showed.

`CLAUDE.local.md` (gitignored) holds machine-specific notes — local paths, environment
quirks, scratch findings. Shared rules belong here; personal ones belong there.

Phases 0–4 are complete (28 manuals, 4,630 chunks, hybrid retrieval at R@5 0.93 /
MRR 0.844). Next is Phase 5, grounded generation. `README.md` still says "Phase 0" —
it lags; trust `Phases.md`.

## Commands

```powershell
.venv/Scripts/python.exe -m pytest -m "not live"        # default suite
.venv/Scripts/python.exe -m pytest tests/test_retrieve.py::test_name   # one test
.venv/Scripts/python.exe -m ingest                       # build the store
.venv/Scripts/python.exe -m ingest --dry-run --limit 2   # parse+chunk only, no API
.venv/Scripts/python.exe -m scripts.ask "how do I enable always on display"
.venv/Scripts/python.exe -m scripts.ask --mode bm25 "EP-TA845"   # or --mode dense
.venv/Scripts/python.exe -m scripts.dump_chunks --sample 30      # Phase 2 human gate
.venv/Scripts/python.exe -m eval.run_eval                # full ablation → eval/RESULTS.md
```

`scripts/` is for iterating on retrieval without the UI; it is throwaway, not API.

## Environment

- Windows, PowerShell. A venv lives at `.venv/` — use `.venv/Scripts/python.exe`
  explicitly rather than assuming an activated shell.
- Python 3.14. Check wheel availability before adding a dependency; several ML packages
  lag on new Python versions.
- `pytest -m "not live"` is the default suite: fast, free, no network.

## Hard rules

- **Never put a real API key in `.env.example`.** It is the committed template. Keys go
  in `.env`, which is gitignored. If a key appears anywhere committed, say so and
  advise rotating it.
- **Never commit `data/`.** It holds Samsung's copyrighted manuals and a rebuildable index.
- **The query pipeline never writes to the store.** Writes go through `staging_store()`
  only. If you find yourself wanting to mutate the store at query time, that's a design
  problem, not a code problem.

## Architecture invariants

These are load-bearing. Breaking one produces failures that surface phases later, far
from the cause.

- **Two pipelines, one contract.** `ingest/` and `query/` share only `core/storage.py`.
  They must not import from each other.
- **Atomic store swaps.** Build into `store.new`, swap on success, keep `store.old` until
  the swap lands. A crashed ingest must leave the previous store serving.
- **`chunk_id` *is* the FAISS vector id** (`IndexIDMap2`). Don't introduce a side mapping;
  it will drift.
- **FTS5 stays in sync via SQL triggers**, not caller discipline. If you add a write path
  for chunks, the triggers must cover it.
- **All FTS queries go through `fts_escape()`.** Raw user text is not a valid MATCH
  expression — `-`, `:`, `*`, `NEAR`, and quotes are operators. `EP-TA845` unescaped
  raises *"no such column: TA845"*, which is how part-number search silently dies.
- **Vectors are L2-normalized once, at index build.** Inner product then equals cosine.
  Don't normalize again at query time in a way that assumes otherwise.
- **Chat history feeds query expansion only, never the grounding context.** Grounding
  context is retrieved chunks and nothing else.

## Conventions

- Type hints on public functions; `from __future__ import annotations` at the top.
- Dataclasses for data crossing pipeline boundaries — see `core/schema.py`.
- Log via `core.logging_setup.get_logger(__name__)`, not `print`.
- Errors users can act on should say what to do: *"Run `python -m ingest` to build one"*,
  not *"store not found"*.
- Comments explain **why**, not what. The FTS escaping and Windows rename dance in
  `core/storage.py` are the model: each says what would break without it.

## Testing

- Every phase has an exit gate in `Phases.md`. Don't advance past a failing gate.
- Mock Gemini in unit tests. Real API calls go behind `@pytest.mark.live`.
- Prefer **relative** assertions for retrieval quality (hybrid beats each half alone,
  rerank improves MRR) over absolute thresholds — absolute numbers depend on the corpus
  and will make the suite brittle.
- Two gates are deliberately human: reading 30 sampled chunks in Phase 2, and driving 10
  conversations in Phase 6. Don't try to automate these away — incoherent chunks pass
  every assertion you could write for them.

## Models and defaults

Defaults live in `core/config.Settings` and two of them are deliberate, measured choices —
don't "fix" them without redoing the measurement:

- **`embed_backend="local"`** (`BAAI/bge-small-en-v1.5`, 384-dim). Gemini's free tier caps
  at 1,000 items/day and the corpus needs 4,630. Generation still goes to Gemini
  (`gemini-2.5-flash`). `GeminiEmbedder` and `LocalEmbedder` are interchangeable behind
  `build_embedder()`; both must stay so.
- **`rerank_enabled=False`.** The cross-encoder cost 280× latency (56ms → 15.6s p50) for a
  flat MRR. The rerank path stays tested and available as an eval arm.

- **Query/document asymmetry is preserved in both backends** — Gemini via task types
  (`RETRIEVAL_DOCUMENT` at ingest, `RETRIEVAL_QUERY` at search), BGE via the instruction
  prefix on the query side only. Mismatching them quietly degrades retrieval, and the
  embedding cache keys on task type, so a mismatch also poisons the cache.
- Ingestion must checkpoint and cache by content hash. Re-embedding an unchanged corpus
  is real money and real quota.
- Verify model IDs against current Google AI docs rather than trusting the strings in
  these files — they move.

## Grounding is the product

The system's value is that it doesn't invent settings paths. When in doubt, prefer a
refusal that names what's missing over an answer that sounds plausible. Every claim in
an answer carries a `[n]` marker resolving to a real manual and page, and citation
accuracy is measured — a citation pointing at the wrong page is a bug of the same
severity as a wrong answer.
