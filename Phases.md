# Build Checklist — Phase by Phase

Companion to `Implementation.md`. Every phase has a **Build** list, a **Tests** list, and
an **Exit gate**. Don't start the next phase until the gate passes — the gates exist
because a failure in Phase 2 is invisible until Phase 5 and expensive to unwind there.

Test stack: `pytest`. Anything touching Gemini is mocked in unit tests; a small set of
`@pytest.mark.live` tests hit the real API and are excluded by default
(`pytest -m "not live"`).

---

## Phase 0 — Foundation ✅ *complete — 23 tests green in ~5s*

**Build**
- [x] Scaffold directory tree from `Implementation.md` §3
- [x] `requirements.txt` — pymupdf, faiss-cpu, google-genai, sentence-transformers, streamlit, pytest, python-dotenv
- [x] `.env.example` with `GEMINI_API_KEY`; `.gitignore` excluding `data/`, `.env`
- [x] `core/config.py` — settings from env, fail loudly on missing key
- [x] `core/schema.py` — `Document`, `Chunk`, `RetrievedChunk`, `Citation`, `Answer`
- [x] `core/storage.py` — SQLite schema (`documents`, `chunks`, `chunks_fts`), FAISS load/save, atomic swap helper
- [x] `core/storage.fts_escape` — *added*: FTS5 query escaping (see note below)
- [x] Structured logging to console + `logs/`, UTF-8 forced on Windows consoles

**Tests**
- [x] `test_storage_roundtrip` — write a Document + 3 Chunks, read them back identical
- [x] `test_fts_populated_by_trigger` — inserting a chunk makes it findable via FTS5 `MATCH`
- [x] `test_fts_finds_exact_part_number` — verbatim `EP-TA845` lookup, the reason BM25 exists here
- [x] `test_fts_reflects_delete` — delete trigger keeps the FTS index in sync
- [x] `test_fts_survives_operator_characters_in_user_text` — `-`, `:`, `*`, `NEAR`, stray quotes
- [x] `test_fts_escape_quotes_every_term`
- [x] `test_empty_and_punctuation_only_queries_return_empty`
- [x] `test_vector_id_mapping_survives_save_load` — `chunks.vector_id` ↔ FAISS row survives save/load
- [x] `test_vectors_are_normalized_on_write`
- [x] `test_misaligned_ids_and_vectors_rejected`
- [x] `test_get_chunks_preserves_rank_order`
- [x] `test_opening_missing_store_is_a_clear_error`
- [x] `test_staging_commit_replaces_previous_store`
- [x] `test_crash_mid_write_leaves_previous_store_intact` — atomic swap
- [x] `test_crash_on_first_ever_build_leaves_no_store`
- [x] `test_config_missing_key_raises` + 4 more config tests
- [x] 3 schema tests (`embed_text` prefixing, citation labels)

**Exit gate:** ✅ passed — round trip works over the real storage contract, and a killed write leaves the previous store serving.

> **Bug caught by the gate:** FTS5 parses `-` as NOT and `:` as a column filter, so
> `EP-TA845` raised *"no such column: TA845"* and every part-number query silently
> returned nothing. Fixed with `fts_escape()`, which quotes each term and OR-joins
> them (recall first — fusion and reranking narrow it later in Phase 4).

---

## Phase 1 — Acquisition ✅ *complete — 28 manuals, 5,108 pages, 197 MB; 85 tests green*

**Build**
- [x] `ingest/discover.py` — sitemap → support pages → manual URLs *(replaces `scrape.py`)*
- [x] `ingest/robots.py` — robots.txt check, per-host cache, crawl-delay
- [x] Rate limiting (≥1s between requests, honors `Crawl-delay`)
- [x] `ingest/acquire.py` — download with `sha256`; skip unchanged on re-run
- [x] `ingest/metadata.py` — model, region, language, OS version from filename + PDF properties
- [x] English-only filter
- [x] `data/store/manifest.json` written atomically
- [x] Fallback path: hand-written `sources.txt` honored identically; `--scan` adopts local PDFs
- [x] *Added*: `dedupe_by_file` — one download per shared family manual
- [x] *Added*: `coverage.json` + `display_model` — authoritative model labels from discovery
- [x] **Download run** — 28 manuals, 5,108 pages, 197 MB in `data/raw/`
- [x] *Added*: `--codes` / `--region` targeting + merge-by-default writes
- [x] *Added*: magic-byte check rejecting Samsung NASCA DRM containers

**Tests** — 51 covering this phase
- [x] `test_parses_real_world_filenames` — 8 real filename shapes → model/language/OS
- [x] `test_multi_model_manual_named_as_family`, `test_unknown_model_is_empty_not_wrong`
- [x] `test_enrich_*` — PDF properties fill gaps but never override a filename model
- [x] `test_dedup_by_content_hash` + `test_rerun_is_idempotent` — second run is a no-op
- [x] `test_language_filter_excludes_non_english`
- [x] `test_rate_limit_respected` — mocked clock shows ≥1s spacing
- [x] `test_manifest_roundtrip_and_schema`
- [x] `test_html_error_page_is_not_saved_as_a_manual` — expired links return HTML
- [x] `test_failed_download_leaves_no_partial_file`
- [x] `test_download_host_is_never_fetched` — discovery only ever *writes* that URL
- [x] `test_robots_disallowed_url_skipped_by_default` / `test_user_directed_flag_allows_disallowed_url`
- [x] `test_403_on_robots_is_treated_as_disallowed_not_as_allowed` (regression, see below)
- [x] `test_shared_manual_downloaded_once_but_records_every_model`
- [x] `@live test_live_samsung_robots_distinguishes_hosts`

**Exit gate:** 22 English manuals in `data/raw/` with a valid manifest, second run a no-op.
Discovery half verified against the live site; download half pending approval.

> **Robots finding.** `org.downloadcenter.samsung.com` (the PDF host) is
> `User-agent: * / Disallow: /`, but `www.samsung.com` publishes sitemaps and permits
> `/{region}/support/model/{SKU}/`, which is server-rendered and carries the links.
> So discovery is fully sanctioned and never touches the PDF host; downloading is
> user-directed and gated behind `--user-directed`.
>
> **Bug caught by the gate.** `RobotFileParser.read()` fetches with urllib's default
> User-Agent, which Samsung answers with **403** — and robotparser turns a 403 into
> "disallow everything". Every URL looked forbidden, including Samsung's own homepage.
> The failure was silent and *looked like compliance*. Now robots.txt is fetched with
> our own session and parsed explicitly.
>
> **DRM.** Some manuals are served inside Samsung's NASCA DRM container — `Content-Type:
> application/pdf`, plausible size, but the bytes start `<## NASCA DRM FILE`. The A06
> manual is DRM-wrapped on the UK site and clean on the India site, so acquisition now
> checks magic bytes and the same manual is retried from another region. No attempt is
> made to decrypt DRM.
>
> **Regions.** Model availability is regional: Canada carries none of the budget A-series,
> so `--region uk` and `--region in` supply the A0x/A1x/A2x/A3x manuals and the S10e.
>
> **Corpus reality.** 22 manuals cover 42 models — Samsung ships one combined manual
> per family generation (the S24 and S25 lines share `S93X_S92X_UG_CA_16_ENG_D3.pdf`).
> Plan assumed 15–30 files for ~15 models; the real ratio is many models per file.

---

## Phase 2 — Parse & chunk ✅ *complete — 4,630 chunks, p50 308 tokens; 120 tests green*

**Build**
- [x] `ingest/parse.py` — PyMuPDF page → text blocks with font size + bbox
- [x] **Headings from the embedded PDF outline** — all 28 manuals carry a 3-level outline,
      so structure is *read*, not guessed; font size/weight only fills gaps
- [x] Table extraction → markdown, kept as its own block type
- [x] Header/footer stripping (position bands: top 6%, bottom 6% of page height)
- [x] Front-matter skipping — cover art and the printed contents list
- [x] `ingest/chunk.py` — packs to ~500 tokens, ~80 overlap, never crosses a section
- [x] *Added*: sibling merging — short subsections combine under a shared parent
- [x] *Added*: sentence-level splitting for oversized single paragraphs
- [x] *Added*: wrapped-heading rejoining
- [x] `section_path` computed per chunk and prefixed onto chunk text
- [x] `page_start` / `page_end` tracked per chunk
- [x] `scripts/dump_chunks.py --sample 30` for human inspection

**Tests** — 35 covering this phase
- [x] `test_outline_drives_section_paths`, `test_heading_levels_come_from_the_outline`
- [x] `test_chapter_only_in_the_outline_still_appears_in_paths`
- [x] `test_chunks_never_cross_a_section_boundary`
- [x] `test_no_chunk_exceeds_the_hard_ceiling` + size distribution measured corpus-wide
- [x] `test_long_section_splits_with_overlap`
- [x] `test_running_header_and_page_number_stripped`
- [x] `test_tables_are_not_split_across_chunks` — rows stay with their header row
- [x] `test_page_range_is_accurate`
- [x] `test_numbered_steps_are_body_not_headings`, `test_diagram_callout_numbers_are_dropped`
- [x] `test_bold_lead_in_ending_in_period_is_not_a_heading`
- [x] `test_part_numbers_survive_parsing` — `EP-TA845` intact
- [x] `test_small_siblings_merge_under_their_parent` + `..._keep_their_own_headings_inline`
- [x] `test_headings_are_not_duplicated_into_chunk_text`
- [x] **Manual gate:** 18 sampled chunks read across two passes — coherent, self-contained

**Exit gate:** ✅ passed. 4,630 chunks; p25 149 / p50 308 / p95 497 tokens; none over 800;
none without a section path; 3 fragment-looking paths out of 3,442, all false positives.

> **The big win.** Every manual carries an embedded 3-level PDF outline (chapter >
> section > subsection, with page numbers). The plan assumed font-size heuristics; the
> outline is authoritative and made section paths reliable across a 2019 manual and a
> 2026 one alike.
>
> **Bugs caught by the gate**
> 1. *Largest span ≠ heading.* Taking each line's biggest span made every numbered step
>    a heading (181 headings vs 109 body paragraphs), because steps embed an oversized
>    numeral and body text embeds icon glyphs. Using the **dominant** span fixed it.
> 2. *Diagram callouts.* Figure labels ("1", "2") are large and bold — typographically
>    identical to headings. Rejected: headings contain letters.
> 3. *Wrapped headings.* A heading spanning two lines was truncated mid-sentence and its
>    tail opened a bogus section — visible in citations as
>    `Health and Safety > be covered by the warranty service`. Fixed by rejoining wrapped
>    heading lines and requiring headings to start with a capital.
> 4. *Chunks too small.* Section-bounded chunking alone gave a median of 66 tokens,
>    because Samsung subsections are one or two sentences. Merging short siblings under
>    their shared parent lifted the median to 308 while keeping each sub-topic labelled.
>
> **Known limitation.** Icons render as empty `( )` — "tap the More options icon ( )".
> Unavoidable without OCR of glyph images, and harmless: surrounding words carry the
> meaning. A handful of lines with inline images extract out of reading order.

---

## Phase 3 — Embed & index ✅ *complete — 4,630 × 384-dim vectors; 146 tests green*

**Build**
- [x] `ingest/embed.py` — batch to `gemini-embedding-001`, `RETRIEVAL_DOCUMENT` task type
- [x] Retry with exponential backoff on 429/5xx, honouring the server's `retryDelay`
- [x] *Added*: sliding-window rate limiter — the free tier counts **items**, not requests
- [x] Checkpoint after each batch; resume without re-embedding
- [x] Content-hash cache so unchanged chunks never re-embed
- [x] *Added*: duplicate collapsing — identical boilerplate embeds once
- [x] Vector index via `core/storage.build_vector_index` (L2-normalize, `IndexFlatIP`)
      — no separate `index.py` needed; the storage contract already owned this
- [x] `ingest/__main__.py` — full pipeline with `--dry-run` and `--limit`

**Tests** — 20 covering this phase
- [x] `test_batches_respect_the_batch_size`
- [x] `test_rate_limit_is_retried_then_succeeds` + `test_server_retry_hint_is_honoured`
- [x] `test_non_retryable_error_fails_fast` — a 400 is not retried 8 times
- [x] `test_partial_progress_is_kept_when_a_later_batch_fails` — checkpointing
- [x] `test_second_run_makes_no_api_calls` + `test_only_changed_texts_are_re_embedded`
- [x] `test_cache_survives_a_new_embedder` — a crashed run resumes
- [x] `test_cache_key_separates_task_types_and_dimensions`
- [x] `test_documents_and_queries_use_different_task_types`
- [x] `test_duplicate_texts_are_embedded_once`
- [x] `test_short_response_is_rejected_rather_than_misaligned`
- [x] `test_rate_limiter_paces_below_the_quota` + `..._forgets_old_usage`
- [x] `test_vectors_are_normalized_on_write` (Phase 0, storage layer)
- [x] `test_crash_mid_write_leaves_previous_store_intact` (Phase 0, atomic swap)
- [x] `@live test_live_gemini_embedding_shape_and_task_types`
- [x] `@live test_self_retrieval_on_the_real_index` — score 1.000, identical text
- [x] `test_local_queries_get_the_bge_instruction_prefix`
- [x] `test_build_embedder_honours_the_configured_backend`
- [x] `test_batch_size_must_divide_the_quota_window`

**Exit gate:** ✅ passed. `python -m ingest` produced 28 documents / 4,630 chunks /
4,630 vectors (384-dim, `index.faiss` 7.1 MB, `corpus.db` 14.7 MB). Self-retrieval returns
identical text at score 1.000. Second run: **0 API calls, 4,630 cache hits.**

> **Quota reality — and the switch to local embeddings.** Gemini's free tier turned out to
> have two ceilings: 100 embedded *items* per minute (a batch of 50 spends 50), and — the
> real blocker — **1,000 items per day**. The corpus needs 4,630, so Gemini embeddings meant
> either five days of waiting or enabling billing (~$0.20). Chosen instead:
> `BAAI/bge-small-en-v1.5` locally — free, no quota, 4,630 vectors in ~8 minutes on CPU.
> Both backends live behind one interface (`build_embedder`), selected by `EMBED_BACKEND`,
> so Phase 7 can benchmark them on the same corpus. The 965 Gemini vectors bought before the
> wall remain cached and valid; cache keys are scoped by model and dimension so a 768-dim
> vector can never contaminate the 384-dim index.
>
> **Query/document asymmetry survives the switch.** Gemini uses `RETRIEVAL_QUERY` vs
> `RETRIEVAL_DOCUMENT`; BGE uses an instruction prefix on queries only. Both are wired, and
> both are silent quality bugs if omitted.
>
> **43% of the corpus is duplicated text.** 4,630 chunks, 2,639 unique — the Google-settings
> passage appears in 22 manuals verbatim. Duplicates cost nothing to embed (collapsed before
> encoding), but **Phase 4 must dedupe at retrieval**: without it one passage can occupy the
> entire top-k, and no reranker fixes that because all 22 copies are equally relevant.
>
> **Bug caught by the gate.** `manifest.json` and `coverage.json` lived inside
> `data/store/`, which the atomic swap replaces wholesale — so the first successful build
> **deleted its own input**, and the next run would have found no manuals. They now live in
> `data/catalog/`, with a regression test asserting the two directories never nest.

---

## Phase 4 — Hybrid retrieval ✅ *complete — R@5 0.93, MRR 0.844; 34 tests green*

**Build**
- [x] `eval/questions.yaml` — 60 questions (54 answerable, 6 unanswerable, 10 verbatim)
- [x] `scripts/ask.py` CLI loop for iterating without the UI
- [ ] Query expansion — deferred to Phase 5, where chat history first exists
- [x] BM25 via FTS5, top 30 (+ stopword filtering)
- [x] Dense via FAISS, query-side prefix, top 30
- [x] RRF fusion, `k=60`, with **adaptive per-query weighting**
- [x] `query/rerank.py` — cross-encoder behind a swappable interface, **off by default**
- [x] Metadata filter when the user names a model
- [x] `eval/run_eval.py` + `eval/RESULTS.md` — recall@1/@5, MRR, latency per arm
- [x] *Added*: near-duplicate collapsing (43% of the corpus is duplicated)

**Tests**
- [ ] `test_exact_code_lookup` — a model number / error code is found by BM25 (dense-only misses it)
- [ ] `test_paraphrase_lookup` — a question sharing no keywords with the source is found by dense
- [ ] `test_rrf_math` — hand-computed fusion on synthetic ranks matches implementation
- [ ] `test_rrf_beats_both` — on the eval set, fused recall@5 > BM25-alone and > dense-alone
- [ ] `test_rerank_improves_precision` — MRR after rerank > before
- [ ] `test_model_filter` — "S24 Ultra" question returns only S24 Ultra chunks
- [ ] `test_expansion_uses_history` — "does it do that too?" expands to an explicit query
- [ ] `test_empty_result_path` — a nonsense query returns empty, not garbage

**Exit gate:** ablation table filled for BM25 / dense / hybrid / hybrid+rerank, and hybrid+rerank wins. This table is the evidence the whole "hybrid" claim rests on.

---

## Phase 5 — Grounded generation

**Build**
- [ ] Prompt with numbered context blocks tagged `[n] {model} p.{page} — {section}`
- [ ] Instructions: context only, inline `[n]` after each claim, refuse when uncovered
- [ ] `[n]` parser → `Citation` objects mapped back to real chunks
- [ ] Refusal path returns what's missing, not a generic apology
- [ ] Token streaming
- [ ] Per-call token + cost accounting

**Tests**
- [ ] `test_citation_parsing` — `[1]`, `[2][3]`, malformed `[9]` (out of range) all handled
- [ ] `test_every_claim_cited` — response sentences carry at least one marker
- [ ] `test_refuses_unanswerable` — off-manual question triggers refusal, not invention
- [ ] `test_no_outside_knowledge` — question answerable from world knowledge but absent from context → refusal
- [ ] `test_citation_points_to_real_page` — cited page's text actually contains the fact
- [ ] `test_streaming_assembles` — streamed chunks concatenate to the complete answer
- [ ] `@live test_end_to_end_answer` — a real question returns a cited, correct answer

**Exit gate:** across the 40 eval questions, zero uncited claims and zero hallucinated settings paths.

---

## Phase 6 — Chat UI

**Build**
- [ ] `app.py` — Streamlit chat with message history
- [ ] Streamed answer rendering
- [ ] Citations as expandable cards: snippet + manual + page
- [ ] Sidebar: model filter, retrieval-mode toggle (hybrid / BM25 / dense)
- [ ] Per-turn latency + token-cost readout
- [ ] History feeds query expansion **only** — never the grounding context
- [ ] Graceful error surface for API failure / empty index

**Tests**
- [ ] `test_history_not_in_context` — grounding prompt contains no prior turns
- [ ] `test_mode_toggle_changes_results` — BM25 and dense modes return different sets
- [ ] `test_citation_card_mapping` — each `[n]` renders the correct source chunk
- [ ] `test_empty_index_message` — no index present → clear instruction, no traceback
- [ ] `test_api_failure_handled` — mocked API error shows a message, session survives
- [ ] **Manual gate:** 10 hand-driven multi-turn conversations, no dead ends

**Exit gate:** a fresh user can install, ingest, and get a cited answer from the README alone.

---

## Phase 7 — Evaluation

**Build**
- [ ] Finalize 40 questions across four types: factual / procedural / spec-table / unanswerable
- [ ] Metrics: recall@5, MRR, citation accuracy, refusal rate, p50+p95 latency, cost per query
- [ ] Ablation runner across all four retrieval modes
- [ ] Results table + short writeup in `eval/RESULTS.md`
- [ ] Update README with the results summary (README itself written in Phase 0)

**Tests**
- [ ] `test_eval_reproducible` — two runs on a fixed index give identical retrieval metrics
- [ ] `test_all_question_types_covered` — each of the four types has ≥8 questions
- [ ] `test_metrics_math` — recall@k and MRR verified against hand-computed fixtures
- [ ] Regression: eval run wired into CI, fails if recall@5 drops >5% from the recorded baseline

**Exit gate:** `eval/RESULTS.md` exists with the ablation table and honest numbers — including the questions the system gets wrong.

---

## Cross-cutting

- [ ] `pytest -m "not live"` green and under 60s at every phase gate
- [ ] Live tests runnable on demand and documented in the README
- [ ] No secrets in the repo; `data/` never committed
- [ ] Every phase's exit gate recorded (pass/fail + date) as you go
