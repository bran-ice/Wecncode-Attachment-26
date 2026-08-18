# Samsung Manual RAG

A hybrid retrieval-augmented generation system that answers questions about Samsung
Galaxy user manuals with **grounded, page-cited answers** — or an honest refusal when
the manuals don't cover the question.

> **Status: Phases 0–6 of 8 built.** There is a working chat UI: ask a question and it
> retrieves, cites, and writes a grounded answer — or refuses when the manuals don't
> cover it. Follow-ups work ("what about wireless charging on it?"). 28 manuals, 5,108
> pages, 4,630 chunks, Recall@5 0.93 (MRR 0.844) — see [`eval/RESULTS.md`](./eval/RESULTS.md).
> Phase 7 is the remaining work: measuring citation accuracy, refusal rate, and cost,
> which are the numbers Phases 5 and 6 are still claimed rather than proven on.
> See [`Phases.md`](./Phases.md) for the full build checklist.

## Why hybrid

Product manuals are a bad fit for pure vector search. They're dense with part numbers
(`EP-TA845`), menu paths (`Settings > Lock screen`), and error codes — strings where an
exact match matters and a semantic near-match is worthless. They're equally full of
questions users phrase nothing like the manual does.

So retrieval runs both ways and fuses the results:

- **BM25** (SQLite FTS5) catches verbatim codes and menu paths
- **Dense vectors** (Gemini embeddings + FAISS) catch paraphrase and intent
- **Reciprocal Rank Fusion** merges the two ranked lists without score normalization
- **A cross-encoder reranker** trims the fused set to the few chunks worth grounding on

## Architecture

Two pipelines that share only a storage contract:

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

Ingestion can run, fail, or be re-run without the query service knowing. The query
service never writes. Stores are built off to the side and swapped into place only on
success, so a reader never sees a half-written index and a crashed ingest leaves the
previous store serving.

## Stack

| Component | Choice |
|---|---|
| Embeddings | `bge-small-en-v1.5` local, 384-dim (Gemini `gemini-embedding-001` available) |
| Generation | Gemini `gemini-3.7-flash` |
| Keyword index | SQLite FTS5 (BM25) |
| Vector index | FAISS `IndexIDMap2` over `IndexFlatIP` (exact search) |
| Reranker | `bge-reranker-base` cross-encoder, local — **off by default**, see below |
| PDF parsing | PyMuPDF |
| UI | Streamlit |

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
pytest -m "not live"          # default: fast, no API calls, ~5s
pytest -m live                # hits the real Gemini API, costs quota
```

Unit tests mock Gemini. Tests marked `live` are excluded by default so the suite stays
free and fast; run them when you've changed anything touching the API.

## Project layout

```
core/       schema, config, logging, and the shared storage contract
ingest/     offline pipeline: scrape → parse → chunk → embed → index
query/      online pipeline: retrieve → rerank → generate
eval/       question set, metrics, ablation runner
tests/      pytest suite
app.py      Streamlit chat UI
```

## Evaluation

[`eval/RESULTS.md`](./eval/RESULTS.md) holds the ablation across BM25 / dense / hybrid /
hybrid+rerank, currently on 60 hand-written questions (54 answerable, 6 deliberately not):

| Arm | Recall@1 | Recall@5 | MRR | p50 |
|---|---|---|---|---|
| BM25 only | 0.69 | 0.76 | 0.713 | 15ms |
| Dense only | 0.72 | 0.93 | 0.802 | 37ms |
| **Hybrid (adaptive RRF)** | 0.78 | **0.93** | **0.844** | 56ms |
| Hybrid + rerank | **0.80** | 0.91 | 0.840 | 15,600ms |

Reranking is off by default: it bought +0.02 Recall@1 while *losing* 0.02 Recall@5 and
costing 280× latency, which is not viable in front of a chat UI. Phase 7 extends this
with citation accuracy (does the cited page actually contain the fact), refusal rate on
the unanswerable questions, and cost per query — all of which need Phase 5 generation
to exist first.

That table is the point. "Hybrid" is a claim, and the ablation is what makes it evidence.

## Documents

- [`Implementation.md`](./Implementation.md) — architecture, decisions, risks
- [`Phases.md`](./Phases.md) — per-phase build checklist, tests, and exit gates
- [`CHUNKING.md`](./CHUNKING.md) — how a PDF becomes retrievable chunks
- [`PIPELINE.html`](./PIPELINE.html) — data-flow diagrams, embeddings, and retrieval (open in a browser)

## Notes

Manuals are downloaded from Samsung's public support site for personal use; the
manuals themselves are Samsung's copyright and are not redistributed here (`data/` is
gitignored).
