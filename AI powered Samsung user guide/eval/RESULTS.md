# Retrieval Evaluation

Measured on the full corpus: 28 manuals, 4,630 chunks, 384-dim `bge-small-en-v1.5`
embeddings. 60 questions — 54 answerable, 6 deliberately unanswerable.

Reproduce with `python -m eval.run_eval`.

## Ablation

| Arm | Recall@1 | Recall@5 | MRR | p50 | p95 |
|---|---|---|---|---|---|
| BM25 only | 0.69 | 0.76 | 0.713 | 15ms | 39ms |
| Dense only | 0.72 | 0.93 | 0.802 | 37ms | 43ms |
| **Hybrid (adaptive RRF)** | 0.78 | **0.93** | **0.844** | **56ms** | 75ms |
| Hybrid + rerank | **0.80** | 0.91 | 0.840 | 15,600ms | 35,712ms |

## The result that justifies hybrid

Aggregate numbers hide the actual mechanism. Split by question type:

| | BM25 | Dense | Hybrid |
|---|---|---|---|
| **Verbatim strings** (n=10) MRR | **0.900** | 0.640 | **0.900** |
| **Natural language** (n=44) MRR | 0.670 | **0.839** | 0.831 |

Dense retrieval loses 26 points on exact strings — `IP68` and `IP67` occupy nearly
the same point in embedding space, which is precisely the wrong behaviour. BM25
loses 17 points on paraphrase, because "why is charging slow" shares no words with
"reduced charging speed".

**Hybrid matches the winner on verbatim and stays within 1 point on natural.** It is
not the best on any single category; it is the only arm that is never bad. That is
the property worth having when you cannot predict what a user will type.

### A warning about eval sets

The first version of this eval contained 44 questions, all natural-language
paraphrases. On that set **dense beat hybrid on every metric** (R@5 0.95 vs 0.91),
and the conclusion would have been that fusion is not worth its cost.

The eval was the problem, not the design: every question was the exact scenario
dense retrieval is built for. Adding 10 verbatim-string questions — each verified to
exist in the corpus first — reversed the finding. An ablation is only as honest as
its question distribution.

## Tuning: adaptive fusion weights

Equal RRF weighting let the weaker arm displace the stronger arm's top hits. A fixed
weight forces a trade:

| BM25 weight | Overall MRR | Verbatim MRR | Natural MRR |
|---|---|---|---|
| 1.0 (equal) | 0.800 | **0.900** | 0.777 |
| 0.7 | 0.815 | 0.740 | **0.831** |
| 0.5 | 0.805 | 0.740 | 0.820 |
| 0.2 | 0.808 | 0.740 | 0.824 |
| **adaptive** | **0.844** | **0.900** | **0.831** |

Downweighting BM25 helps prose and destroys exact-string lookup — trading away the
one thing BM25 is in the system for. So the weight is chosen per query: full weight
when the query contains a literal-looking token (`IP68`, `45W`, `SM-A155F`, all-caps
like `HEIF`) or is three words or fewer; 0.7 otherwise.

**Caveat:** this is a regex over query *shape*, not a measure of term rarity, and it
was tuned on 54 questions. A more principled version would check each token's
document frequency in the index. Treat it as fitted, not proven.

## The reranker does not earn its place

The plan assumed a cross-encoder would clearly improve precision. On this corpus it
does not:

- **+0.02 Recall@1** — the only gain
- **−0.02 Recall@5** — it promotes some hits to rank 1 while pushing others out of
  the top 5 entirely
- **MRR flat** (0.844 → 0.840) — no net ranking improvement
- **280× slower** — 56ms → 15.6s at p50, 35.7s at p95

Two reasons. `bge-reranker-base` is a 278M-parameter model scoring 20 candidates per
query on CPU. And adaptive RRF has already left little headroom: reranking a list
that is 93% correct at k=5 has more to lose than to gain.

A 15-second wait *before generation begins* is not viable for a chat UI. Worth
revisiting with a smaller model (`ms-marco-MiniLM-L-6-v2`, ~22M params), a shorter
candidate list (top 8 rather than 20), or GPU inference.

## Deduplication

43% of the corpus is duplicated — 4,630 chunks, 2,639 unique. The "Settings > Google"
passage appears verbatim in 22 manuals. Without collapsing, a single question can
fill the entire top-k with one passage.

Exact matching was not enough: manual revisions reword a sentence or two, so copies
differ by a word. One real charging query returned three near-identical warnings
differing only by "An". Near-duplicate detection (Jaccard ≥ 0.85 over token sets)
collapsed 24 of 30 candidates on that query.

## Fixes that moved the numbers

| Change | Effect |
|---|---|
| Drop stopwords from FTS queries | R@5 0.68 → 0.91, p50 240ms → 57ms |
| Near-duplicate collapsing | Top-k diversity; 24/30 candidates collapsed on one query |
| Adaptive BM25 weighting | MRR 0.800 → 0.844 |
| Match gold on path *and* body | Measurement fix — merged subsections were scored as misses |

The stopword bug was the largest single win. `fts_escape` OR-joins every term, so
"what happens if I **lose my phone**, can I **track it**" matched any long passage
containing "phone" and "it" — one *Reminder* passage was ranking first for several
unrelated questions.

Note that the 0.68 → 0.91 figure combines a real retrieval fix with a measurement
fix applied at the same time; they are not separated.

## Remaining misses (5 of 54)

`bixby-routines`, `edge-panel`, `security-updates`, `factory-reset`,
`verbatim-model-code`.

The last is arguably a bad gold label: `SM-A155F` appears in 26 chunks across
unrelated sections, so no single section is "the" right answer.

## Not yet measured

Citation accuracy, refusal rate on the 6 unanswerable questions, and cost per query
all require Phase 5 (generation). The 6 unanswerable questions are carried in the
set but currently unused.
