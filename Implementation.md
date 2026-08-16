# Hybrid RAG for Samsung Galaxy User Manuals — Implementation Plan

## 1. Decisions locked in

| Area | Decision |
|---|---|
| Corpus | Samsung **Galaxy phone** user manuals, **scraped/downloaded** from Samsung support |
| Architecture | **Two independent pipelines over shared storage**: offline ingestion, online per-message query |
| Embeddings | **Gemini** (`gemini-embedding-001`) |
| Generation | **Gemini** (`gemini-2.5-flash`, escalate to `gemini-2.5-pro` if synthesis is weak) |
| Retrieval | **Hybrid**: BM25 keyword + dense vector, fused, then reranked |
| Answers | **Grounded generation with inline source citations** (manual + page) |
| Interface | **Local chat UI** (Streamlit) |

> Verify exact Gemini model IDs against current Google AI docs at build time — they move.

## 2. System shape

```
                        ┌──────────────────────────────┐
  OFFLINE (batch)       │        SHARED STORAGE        │      ONLINE (per message)
                        │                              │
 scrape → parse →       │  manuals/*.pdf   (raw)       │   query → expand → BM25 ┐
 chunk → embed  ───────▶│  corpus.db       (SQLite)    │◀──          + dense    ├─▶ RRF
                        │   ├ documents                │             ┘           │
 run: python -m ingest  │   ├ chunks                   │                    rerank
                        │   └ chunks_fts (FTS5/BM25)   │                         │
                        │  index.faiss    (vectors)    │            grounded answer + citations
                        └──────────────────────────────┘                         │
                                                                          Streamlit chat
```

The two pipelines share **only** the storage contract. Ingestion can run, fail, or be
re-run without the query service knowing; the query service never writes to the index.

## 3. Layout

```
samsung-rag/
├─ data/
│  ├─ raw/                  # downloaded PDFs
│  └─ store/                # corpus.db, index.faiss, manifest.json
├─ ingest/
│  ├─ scrape.py             # discover + download manuals
│  ├─ parse.py              # PDF → structured blocks (text, tables, headings)
│  ├─ chunk.py              # section-aware chunking
│  ├─ embed.py              # Gemini batch embeddings
│  ├─ index.py              # write SQLite + FAISS
│  └─ __main__.py           # orchestrates, resumable
├─ query/
│  ├─ retrieve.py           # BM25 + dense + RRF
│  ├─ rerank.py             # cross-encoder or Gemini rerank
│  ├─ generate.py           # grounded prompt + citation parsing
│  └─ pipeline.py           # single entrypoint: answer(question) -> Answer
├─ core/
│  ├─ config.py             # env + settings
│  ├─ schema.py             # Chunk, Document, Citation, Answer
│  └─ storage.py            # the shared-storage contract, used by both sides
├─ eval/
│  ├─ questions.yaml        # ~40 hand-written Q/A with expected source pages
│  └─ run_eval.py           # recall@k, MRR, citation accuracy, groundedness
├─ app.py                   # Streamlit chat UI
└─ .env.example             # GEMINI_API_KEY
```

## 4. Phases

> Per-phase build checklists, test lists, and exit gates live in [`Phases.md`](./Phases.md).

### Phase 0 — Foundation (½ day)
- Project scaffold, `.env` handling, `pip` deps, logging.
- `core/schema.py`: `Document`, `Chunk`, `RetrievedChunk`, `Citation`, `Answer`.
- `core/storage.py`: the contract both pipelines depend on. SQLite schema:
  - `documents(id, model, title, url, sha256, n_pages, ingested_at)`
  - `chunks(id, doc_id, page_start, page_end, section_path, text, token_count)`
  - `chunks_fts` — FTS5 virtual table over `chunks.text` (this is the BM25 side)
  - FAISS index on disk; row `id` ↔ FAISS vector id kept in `chunks.vector_id`.
- **Exit:** can write and read a fake document end to end.

### Phase 1 — Acquisition (1 day)
- `scrape.py`: enumerate Galaxy manual download links, respect `robots.txt`,
  rate-limit, cache by URL hash, record `sha256` so re-runs skip unchanged files.
- Normalize metadata from filename/PDF properties: model name, region, language,
  OS version. Filter to English.
- **Exit:** ~15–30 Galaxy manuals in `data/raw/` with a `manifest.json`.
- **Risk:** links may be JS-rendered or behind a POST API. Fallback: a checked-in
  URL list you populate manually — ingestion doesn't care where the PDFs came from.

### Phase 2 — Parse & chunk (1–2 days) ← *quality lives here*
- `parse.py` with PyMuPDF: per page, extract text blocks with font size/position
  so headings are recoverable; extract tables separately (they carry specs and
  error codes) and serialize as markdown.
- Drop headers/footers by detecting text repeated on >60% of pages.
- `chunk.py`: **section-aware, not fixed-window**. Split on detected headings,
  then pack to ~500 tokens with ~80 token overlap, never crossing a section.
  Every chunk keeps `section_path` (e.g. `Settings > Battery > Fast charging`)
  and is prefixed with it at embed time — this is what makes citations readable
  and boosts retrieval on short questions.
- **Exit:** dump 30 random chunks and read them. If they're incoherent, fix here
  before touching retrieval — no reranker rescues bad chunks.

### Phase 3 — Embed & index (½ day)
- `embed.py`: batch chunks to `gemini-embedding-001`, retry with backoff,
  checkpoint after each batch so a crash resumes instead of re-billing.
- Use the task-type distinction: `RETRIEVAL_DOCUMENT` at ingest,
  `RETRIEVAL_QUERY` at search time.
- `index.py`: normalize vectors, `IndexFlatIP` (corpus is small; exact search is
  fine and removes a tuning variable). Write index + rebuild FTS table atomically
  into a temp dir, then swap — so the online side never reads a half-written index.
- **Exit:** `python -m ingest` on an empty store produces a queryable index.

### Phase 4 — Hybrid retrieval (1–2 days)
- **Query expansion:** Gemini rewrites the message into 2–3 search queries,
  resolving chat context ("does it do that too?" → an explicit question) and
  adding synonyms Samsung actually uses ("Edge panel", "Bixby routines").
- **BM25:** SQLite FTS5 over expanded queries, top 30. Catches model numbers,
  menu paths, and error codes verbatim — the thing dense retrieval loses.
- **Dense:** FAISS cosine, top 30.
- **Fusion:** Reciprocal Rank Fusion, `score = Σ 1/(60 + rank)`. No score
  normalization needed, which is why RRF beats weighted-sum here.
- **Rerank:** top ~20 fused → cross-encoder (`bge-reranker-base`, local, fast) →
  top 5. Keep it behind an interface with a Gemini-rerank alternative.
- **Metadata filter:** if the user names a model, constrain to that document set.
- **Exit:** on `eval/questions.yaml`, recall@5 measurably beats BM25-alone and
  dense-alone. Record all three numbers — this is the evidence the "hybrid" claim rests on.

### Phase 5 — Grounded generation (1 day)
- Prompt contract: numbered context blocks, each tagged `[1] {model} p.{page} — {section}`.
  Instruct: answer **only** from context; cite `[n]` inline after each claim; if the
  context doesn't cover it, say so and name what's missing. No outside knowledge.
- Parse `[n]` markers back into `Citation` objects → real page links in the UI.
- **Refusal path is a feature**, not a bug: a manual QA system that invents a
  settings path is worse than one that says "not covered in the S24 manual."
- Stream tokens to the UI.

### Phase 6 — Chat UI (1 day)
- Streamlit: message history, streamed answer, citations as expandable cards
  showing the source snippet, manual name, and page number.
- Sidebar: model/manual filter, retrieval-mode toggle (hybrid / BM25 / dense) for
  demoing the difference, and a latency + token-cost readout per turn.
- Multi-turn: history feeds query expansion only, never the grounding context.

### Phase 7 — Evaluation (1 day)
- 40 questions across four types: **factual** ("how do I enable Always On Display"),
  **procedural** (multi-step), **spec/table lookup**, **unanswerable** (must refuse).
- Metrics: recall@5, MRR, citation accuracy (does cited page contain the fact),
  refusal rate on unanswerables, p50/p95 latency, cost per query.
- Ablation table: BM25 / dense / hybrid / hybrid+rerank. This table is the
  strongest artifact the project produces — build it, don't skip it.

## 5. Sequencing

Phases 0→3 are strictly ordered. Once the index exists, 4–6 can interleave; build a
throwaway CLI query loop at the start of Phase 4 so you can iterate on retrieval
without UI in the way. Total: **~7–9 working days**.

## 6. Main risks

| Risk | Mitigation |
|---|---|
| Scraping blocked or JS-gated | Manual URL list fallback; ingestion is source-agnostic |
| Manuals are multi-column / image-heavy → garbled text | Inspect parse output early (Phase 2 exit gate); PyMuPDF block ordering, OCR only if forced |
| Gemini embedding quota during full re-index | Checkpointing + content-hash cache; only changed chunks re-embed |
| Near-identical manuals across models cause cross-model bleed | Model metadata filter + `section_path` in chunk text + surface the model name in every citation |
| Answers look right but cite the wrong page | Citation accuracy is an explicit metric, not a vibe check |

## 7. Open items for you

1. Roughly how many Galaxy models should the corpus cover — a focused 5, or 20+?
2. Is offline operation ever required, or is network-at-query-time always fine?
3. Do you want conversation history persisted across UI restarts?

---

**Nothing has been built yet.** Confirm or amend this plan and I'll start with Phase 0.
