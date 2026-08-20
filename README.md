# Samsung Manual RAG

A hybrid retrieval-augmented generation system that answers questions about Samsung
Galaxy user manuals with **grounded, page-cited answers** — or an honest refusal when
the manuals don't cover the question.

> **Status: Phases 0–7 built; exit gates for 5–7 not yet passed.** There is a working
> chat UI: ask a question and it retrieves, cites, and writes a grounded answer — or
> refuses when the manuals don't cover it. Follow-ups work ("what about wireless
> charging on it?"). The evaluation harness now measures generated answers too —
> citation accuracy, refusal rate, cost — not just retrieval.
> See [`Phases.md`](./Phases.md) for the full checklist and what each gate still needs.
>
> **⚠️ The corpus on disk is a placeholder.** As of 2026-08-20 the 28-manual corpus was
> deleted and replaced with two short Galaxy A05 excerpts (43 chunks) pending a real
> manual. The retrieval numbers quoted below and in
> [`eval/RESULTS.md`](./eval/RESULTS.md) were measured on the old corpus with a
> different embedding model and **are not reproducible against the current store.**
> They are kept as a record of what was measured.

## Why hybrid

Product manuals are a bad fit for pure vector search. They're dense with part numbers
(`EP-TA845`), menu paths (`Settings > Lock screen`), and error codes — strings where an
exact match matters and a semantic near-match is worthless. They're equally full of
questions users phrase nothing like the manual does.

So retrieval runs both ways and fuses the results:

- **BM25** (SQLite FTS5) catches verbatim codes and menu paths
- **Dense vectors** (Gemini embeddings + FAISS) catch paraphrase and intent
- **Reciprocal Rank Fusion** merges the two ranked lists without score normalization,
  weighting BM25 higher when the question looks like an exact-string lookup

Each arm retrieves 30 candidates; RRF fuses them, near-duplicates are collapsed, and the
top 5 become the grounding context.

A cross-encoder reranker is implemented and tested, but **is not in the serving path** —
it cost 280× latency for no measurable gain. It stays as an eval arm; see below.

## Architecture

Two pipelines that share only a storage contract:

```
                        ┌──────────────────────────────┐
  OFFLINE (batch)       │        SHARED STORAGE        │      ONLINE (per message)
                        │                              │
 scrape → parse →       │  manuals/*.pdf   (raw)       │   query → expand → BM25 ┐
 chunk → embed  ───────▶│  corpus.db       (SQLite)    │◀──          + dense    ├─▶ RRF
                        │   ├ documents                │             ┘           │
 run: python -m ingest  │   ├ chunks                   │                      dedupe
                        │   └ chunks_fts (FTS5/BM25)   │                     + top-k
                        │  index.faiss    (vectors)    │            grounded answer + citations
                        └──────────────────────────────┘                         │
                                                                          Streamlit chat
```

Ingestion can run, fail, or be re-run without the query service knowing. The query
service never writes. Stores are built off to the side and swapped into place only on
success, so a reader never sees a half-written index and a crashed ingest leaves the
previous store serving.

## Stack

| Component | Choice |
|---|---|
| Embeddings | Gemini `gemini-embedding-001`, 768-dim (local `bge-small-en-v1.5` interchangeable via `EMBED_BACKEND`) |
| Generation | Gemini `gemini-3.5-flash-lite` |
| Keyword index | SQLite FTS5 (BM25) |
| Vector index | FAISS `IndexIDMap2` over `IndexFlatIP` (exact search) |
| Reranker | `bge-reranker-base` cross-encoder, local — **not in the serving path**, eval arm only |
| PDF parsing | PyMuPDF |
| UI | Streamlit |

Both embedding backends stay interchangeable behind `build_embedder()`. Local BGE avoids
the free tier's 1,000-items/day cap, which matters at corpus scale — but it drags in
`torch` and `sentence-transformers`, ~150s of cold start per process before a single
vector is computed. Gemini embeddings remove that entirely at the cost of a network round
trip per query. Switching backends changes the vector dimension, so it requires a full
re-ingest; the embedding cache keys on `(model, task_type, dim, text)` precisely so a
stale vector can never be served into a new index.

## Setup

Requires Python 3.11+ (developed on 3.14).

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; use source .venv/bin/activate elsewhere
pip install -r requirements.txt

cp .env.example .env          # then add your Gemini API key
```

Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
`.env` is gitignored; **never put a real key in `.env.example`**, which is committed.

## Usage

```bash
python -m ingest              # build the store first: parse, chunk, embed, index
streamlit run app.py          # then chat — this is the interface
```

`python -m ingest` reads `data/catalog/manifest.json`, which discovery writes. If you are
supplying your own PDFs in `data/raw/` rather than scraping, build the manifest from them
first:

```bash
python -m ingest.acquire --scan
```

Filenames carry the metadata: `--scan` infers model, language and region from them and
**skips any file it can't identify as English**. A file named `Samsung A05.pdf` is
skipped; `SM-A055F_UG_EN_something.pdf` is indexed as a Galaxy A05. See
`ingest/metadata.py` for the patterns it recognizes.

The sidebar toggles the retrieval mode (hybrid / BM25 / dense), limits answers to one
device model, and shows latency and token cost per turn. Every claim carries a `[n]`
that expands into the manual page it came from.

For working on retrieval without a browser in the way:

```bash
python -m ingest --dry-run    # everything except the embedding calls
python -m scripts.ask "how do I enable always on display"   # retrieved passages only
python -m scripts.ask --answer "how do I take a screenshot" # cited answer (Gemini)
python -m scripts.ask --mode bm25 "EP-TA845"                # one retrieval arm
python -m eval.run_eval       # reproduce the ablation table
```

## Tests

```bash
pytest -m "not live"          # default: 286 tests, no API calls
pytest -m live                # hits the real Gemini API, costs quota
```

Unit tests mock Gemini. Tests marked `live` are excluded by default so the suite stays
free; run them when you've changed anything touching the API.

The default suite takes ~130s on Windows, most of it antivirus scanning the venv during
import rather than test execution. Excluding `.venv/` from Defender cuts it substantially.

## Project layout

```
core/       schema, config, logging, and the shared storage contract
ingest/     offline pipeline: scrape → parse → chunk → embed → index
query/      online pipeline: expand → retrieve → fuse → generate (rerank.py is eval-only)
eval/       question set, metrics, ablation runner
tests/      pytest suite
app.py      Streamlit chat UI
```

## Evaluation

[`eval/RESULTS.md`](./eval/RESULTS.md) holds the ablation across BM25 / dense / hybrid /
hybrid+rerank. The gold set is 64 hand-written questions — 16 factual, 28 procedural, 10
spec-table, 10 deliberately unanswerable.

**These numbers were measured on the 28-manual corpus with 384-dim local BGE embeddings.**
That corpus has been replaced by a placeholder, so the table below is history, not a
current measurement:

| Arm | Recall@1 | Recall@5 | MRR | p50 |
|---|---|---|---|---|
| BM25 only | 0.69 | 0.76 | 0.713 | 15ms |
| Dense only | 0.72 | 0.93 | 0.802 | 37ms |
| **Hybrid (adaptive RRF)** | 0.78 | **0.93** | **0.844** | 56ms |
| Hybrid + rerank | **0.80** | 0.91 | 0.840 | 15,600ms |

Reranking is not in the serving path: it bought +0.02 Recall@1 while *losing* 0.02
Recall@5 and costing 280× latency, which is not viable in front of a chat UI.

`eval/generation.py` extends this to the generated answer — citation accuracy (does the
cited page actually contain the fact), refusal rate on the unanswerable questions, false
refusals on answerable ones, uncited-claim rate, and cost per query. Every answer is
written to `eval/answers.md` for reading, because aggregate scores hide the failures
worth seeing.

That table is the point. "Hybrid" is a claim, and the ablation is what makes it evidence
— which is also why re-running it against the current 43-chunk placeholder would be
worse than not running it at all. Recall@5 is nearly free when five results cover most
of the corpus. The gold set needs rebuilding against a real manual first.

## Documents

- [`Implementation.md`](./Implementation.md) — architecture, decisions, risks
- [`Phases.md`](./Phases.md) — per-phase build checklist, tests, and exit gates
- [`CHUNKING.md`](./CHUNKING.md) — how a PDF becomes retrievable chunks
- [`PIPELINE.html`](./PIPELINE.html) — data-flow diagrams, embeddings, and retrieval (open in a browser)

## Notes

Manuals are downloaded from Samsung's public support site for personal use; the
manuals themselves are Samsung's copyright and are not redistributed here (`data/` is
gitignored).
