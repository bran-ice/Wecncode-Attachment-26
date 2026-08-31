# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A hybrid RAG system over Samsung Galaxy user manuals. Read [`Implementation.md`](./Implementation.md)
for architecture and [`Phases.md`](./Phases.md) for the build checklist — **`Phases.md` is
the source of truth for what's done and what's next.** Check the boxes as you complete
work, and record what a phase's exit gate actually showed.

[`CHUNKING.md`](./CHUNKING.md) explains how a PDF becomes retrievable chunks — read it
before touching `ingest/chunk.py`. [`PIPELINE.html`](./PIPELINE.html) holds the data-flow
diagrams (open in a browser).

`CLAUDE.local.md` (gitignored) holds machine-specific notes — local paths, environment
quirks, scratch findings. Shared rules belong here; personal ones belong there.

Phases 0–8 are built. The exit gates for 5, 6, 7 and 8 have **not** passed: 5 and 7 are
blocked on the corpus (below), 6 and 8 need a human run-through. `README.md` and `Phases.md`
were both brought current on 2026-08-20 and agree with the code — if they disagree in
future, `Phases.md` wins.

**The corpus is one real A05 manual** (2026-08-31): `SM-A055F_UG_EU_Eng_Rev1.0_250507.pdf`,
32 pages → 76 chunks, 9 figures. It replaced the two placeholder excerpts, which replaced
the original 28-manual corpus. Two things about it:

- **It has no PDF outline** (`get_toc()` → 0 entries), so section paths come from font
  heuristics and are **flat** — no `chapter > section` ancestry. All 76 chunks still got
  a non-empty path.
- **It was renamed to scan correctly.** `SM-A05X_…` yields model `unknown`; `_CODE_RE`
  needs `[SFAN]` + three digits. Always check the model `--scan` reports, not just that
  it indexed the file.

The notes below were written for the deleted placeholder corpus. What still holds:

- The measured numbers still quoted in Phases 1–4 (R@5 0.93, MRR 0.844) came from the
  old corpus **and** the old embedder. They are not reproducible today.
- `eval/` is stale **by decision**, not by neglect. The gold set in `eval/questions.yaml`
  references chunks and pages that no longer exist. Don't run `eval.run_eval` and report
  its output as a quality signal, and don't "fix" the stale files. **A real manual has now
  landed, so rebuilding the gold set against it is unblocked** — that is the next
  measurement task, and it must come before any number is quoted again.
- Retrieval metrics are still weak at 76 chunks — R@5 is cheap when five results cover a
  large share of the corpus — but no longer meaningless the way they were at 43.
- ~~Citation pages are offset~~ — that applied to the deleted excerpts, one of which
  started at manual page 30. The current manual is paginated from its own page 1, so
  cited pages are internally consistent. They still won't match a *full* A05 manual's
  numbering, because this is the 32-page EU edition.
- `eval_out.txt` in the repo root is untracked old-corpus output from 2026-08-16. It is
  history like the rest of `eval/`, not a current measurement.

## Commands

```powershell
.venv/Scripts/streamlit.exe run app.py                   # the chat UI — the actual product
.venv/Scripts/python.exe -m pytest -m "not live"        # default suite
.venv/Scripts/python.exe -m pytest tests/test_retrieve.py::test_name   # one test
.venv/Scripts/python.exe -m ingest.acquire --scan        # local PDFs -> catalog/manifest.json
.venv/Scripts/python.exe -m ingest                       # build the store
.venv/Scripts/python.exe -m ingest --dry-run --limit 2   # parse+chunk only, no API
.venv/Scripts/python.exe -m ingest --no-figures          # text-only store
.venv/Scripts/python.exe -m scripts.ask "how do I enable always on display"
.venv/Scripts/python.exe -m scripts.ask --mode bm25 "EP-TA845"   # or --mode dense
.venv/Scripts/python.exe -m scripts.ask --answer "how do I take a screenshot"  # cited answer
.venv/Scripts/python.exe -m scripts.dump_chunks --sample 30      # Phase 2 human gate
.venv/Scripts/python.exe -m eval.run_eval                # full ablation → eval/RESULTS.md
```

`scripts/` is for iterating on retrieval without the UI; it is throwaway, not API.
`scripts.ask` retrieves only unless given `--answer`, which calls Gemini; `--quiet`
then hides the raw chunks. The Streamlit app is what Phase 6's human gate exercises.

`python -m ingest` reads `data/catalog/manifest.json` and fails with *"No manuals in the
manifest"* if it is absent — `--scan` builds it from whatever is in `data/raw/`. `--scan`
infers model, language and region **from the filename** and silently skips anything it
can't identify as English, so `Samsung A05.pdf` is dropped while
`SM-A055F_UG_EN_*.pdf` is indexed as a Galaxy A05. See `ingest/metadata.py`.

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
  They must not import from each other. `app.py` is the composition root and the one
  place exempt: it imports `build_embedder` from `ingest.embed` and injects the embedder
  into `ChatSession`, which is why `query/retrieve.py` can call `embed_query()` without
  importing `ingest/`. Wire new cross-pipeline dependencies the same way — inject at
  `app.py`, don't import across.
- **`query/session.py` is the seam the UI talks to.** `ChatSession` owns history and
  drives expand → retrieve → generate; `check_store_ready()` produces the actionable
  "no store yet" message. A traceback surfacing in the UI usually passes through
  `ChatSession.ask`, so read it before assuming the fault is in retrieval or generation.
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
- **Figures are display-only.** They never enter the grounding context, `embed_text()`,
  or ranking — the generator is text-only and every `[n]` resolves to text on a page.
  `figures`/`chunk_figures` deliberately do not touch `chunks`, so the FTS triggers and
  the vector-id rule are unaffected. See `ingest/figures.py`.
- **A figure renders only on the chunk it physically sits in, and only when that chunk is
  cited.** Do not widen this to sibling chunks, the parent section, or the page range —
  decided 2026-08-31 after measuring the consequence. Samsung puts the illustration under
  a section intro while "how do I…" answers cite the procedure subsection, so figures
  genuinely miss more often than they fire. **That is the accepted cost, not a bug to
  fix.** A figure shown beside a procedure it does not depict is a claim the manual never
  made, carrying the same authority as the cited text. If this is ever revisited the lever
  is chunking — putting the figure and its procedure in one chunk — not a looser mapping.
- **Figure PNGs live inside the store root** (`data/store/figures/<doc_id>/`), so
  `staging_store()` swaps database, index and images together. Written anywhere else
  they would outlive a failed ingest and no longer match the store that is serving.
- **Chat history feeds query expansion only, never the grounding context.** Grounding
  context is retrieved chunks and nothing else. The *question* in the grounding prompt is
  the expander's rewrite (`ChatSession` passes `resolved_question`) — without it the model
  refuses "explain it step by step" for having no antecedent, even when retrieval was
  perfect. Substituting the question is not a breach; adding a prior turn to the context
  blocks would be.

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
- Prefer **relative** assertions for retrieval quality (hybrid beats each half alone) over
  absolute thresholds — absolute numbers depend on the corpus and will make the suite
  brittle. Don't assert that rerank improves MRR; measurement says it doesn't.
- The default suite is 316 tests on this machine. Most of the wall time is antivirus
  scanning the venv during import, not tests running — it is not a regression. If a run
  takes many minutes, clear `%LOCALAPPDATA%\Temp\pytest-of-brani` before assuming a hang;
  accumulated temp dirs have pushed a green suite past ten minutes.
- Two gates are deliberately human: reading 30 sampled chunks in Phase 2, and driving 10
  conversations in Phase 6. Don't try to automate these away — incoherent chunks pass
  every assertion you could write for them.

## Models and defaults

Defaults live in `core/config.Settings`, but **what actually runs is `.env`**, which
overrides them and is gitignored. Check `.env` before reasoning about behaviour — the
defaults in `config.py` are no longer what the system uses.

Currently live (set in `.env`, 2026-08-20):

| | `config.py` default | `.env` override |
|---|---|---|
| `embed_backend` | `local` | **`gemini`** |
| `embed_model` | `gemini-embedding-001` | same (not overridden) |
| `gen_model` | `gemini-3.7-flash` | **`gemini-3.5-flash-lite`** |

The env vars `load_settings()` actually reads are `GEMINI_API_KEY`, `DATA_ROOT`,
`EMBED_MODEL`, `EMBED_BACKEND`, `LOCAL_EMBED_MODEL`, `GEN_MODEL`, `RERANK`,
`RERANK_MODEL` and `LOG_LEVEL` — nothing else in `.env` has any effect. In particular
**the 768 dimension is not configurable**: `EMBED_DIM` is a module constant in
`ingest/embed.py`, not a setting. Changing it invalidates every vector in the store.

- **The embedding backend switched away from local BGE for cold-start latency.** Local
  cost ~150s per process — ~140s of it `import torch` + `import sentence_transformers`
  before any weights loaded (measured warm: s-t 116.4s, torch 24.0s, faiss 2.7s, BGE
  weights 8.6s, encode 0.08s). In Streamlit that was a ~3-minute wait on first render.
  The original quota rationale still holds and will apply again: the free tier caps at
  1,000 items/day, which the old 4,630-chunk corpus blew through. At 43 chunks it is
  inert. If a real manual pushes the count back into the thousands, move BGE to an ONNX
  runtime (same weights, same vector space, seconds of import) rather than reverting to
  torch.
- **Switching backends changes the vector dimension, so it requires a full re-ingest.**
  The embedding cache keys on `(model, task_type, dim, text)` precisely so a stale vector
  can never be served into a new index — a backend switch is a clean total miss.
- **`rerank_enabled=False`, and the flag is moot anyway.** The cross-encoder cost 280×
  latency (56ms → 15.6s p50) for a flat MRR. Beyond the flag, nothing in the serving path
  imports `query/rerank.py` — only `eval/run_eval.py` does. Flipping `RERANK=true` will
  not put a reranker in front of the UI.

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
