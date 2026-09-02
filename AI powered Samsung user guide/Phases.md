# Build Checklist — Phase by Phase

Companion to `Implementation.md`. Every phase has a **Build** list, a **Tests** list, and
an **Exit gate**. Don't start the next phase until the gate passes — the gates exist
because a failure in Phase 2 is invisible until Phase 5 and expensive to unwind there.

Test stack: `pytest`. Anything touching Gemini is mocked in unit tests; a small set of
`@pytest.mark.live` tests hit the real API and are excluded by default
(`pytest -m "not live"`).

> **⚠️ Corpus and embedding backend changed on 2026-08-20 — see
> [Corpus reset](#corpus-reset-2026-08-20) at the bottom.** The 28-manual corpus was
> deleted and replaced with a 2-file placeholder. Every measured number recorded in
> Phases 1–4 below (4,630 chunks, R@5 0.93, MRR 0.844) was taken on the old corpus with
> the old embedder and **is not currently reproducible**. The numbers are kept as a
> record of what was measured, not as a description of the store on disk today.

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

> **Superseded 2026-08-20.** The backend is now `gemini-embedding-001` at 768 dims
> (`EMBED_BACKEND=gemini` in `.env`), and the store holds 43 vectors, not 4,630. The
> local-BGE rationale below is still the reason `LocalEmbedder` exists and stays
> interchangeable — it is no longer what runs. See [Corpus reset](#corpus-reset-2026-08-20).

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

**Tests** — 36 green in `tests/test_retrieve.py` + `tests/test_rerank.py`. Planned names
mapped onto what was actually written:

- [x] `test_exact_code_lookup` → covered by the eval split, not a unit test: verbatim-string
      MRR is BM25 0.900 vs dense 0.640 (`eval/RESULTS.md`). Plus
      `test_literal_queries_keep_bm25_at_full_weight`
- [x] `test_paraphrase_lookup` → same, inverted: natural-language MRR is dense 0.839 vs
      BM25 0.670. Plus `test_prose_queries_let_dense_lead`
- [x] `test_rrf_math` → `test_rrf_scores_match_the_formula`,
      `test_rrf_needs_no_score_normalisation`
- [x] `test_rrf_beats_both` → `test_chunk_found_by_both_retrievers_outranks_either_alone`
      (unit), confirmed on the eval set: hybrid MRR 0.844 > dense 0.802 > BM25 0.713
- [x] ~~`test_rerank_improves_precision`~~ — **disproven, not implemented.** Rerank left MRR
      flat (0.844 → 0.840) and *lost* 0.02 Recall@5. Asserting it would have been asserting
      something false. Replaced by `test_reranking_is_off_by_default` and
      `test_rerank_env_var_enables_it`, which pin the decision instead
- [x] `test_model_filter` → `test_model_filter_matches_a_family_manual`,
      `test_unknown_model_does_not_empty_the_results`
- [ ] `test_expansion_uses_history` — deferred to Phase 5 with query expansion itself
- [x] `test_empty_result_path` → `test_empty_lists_fuse_to_nothing`
- [x] *Added*: dedupe suite (5 tests) for the near-duplicate collapsing

**Exit gate:** ✅ passed, with the gate's own prediction corrected. The ablation table is
filled for all four arms (`eval/RESULTS.md`, 60 questions on the full 4,630-chunk corpus)
and **hybrid wins — but hybrid+rerank does not.** Rerank bought +0.02 Recall@1 while losing
0.02 Recall@5, held MRR flat, and cost 280× latency (56ms → 15.6s p50), so it ships off by
default behind a swappable interface.

What the table actually proves is better than what the gate asked for. Aggregate recall
hides the mechanism; the per-type split is the evidence: dense loses 26 MRR points on
verbatim strings (`IP68` and `IP67` sit almost on top of each other in embedding space),
BM25 loses 17 on paraphrase ("why is charging slow" shares no words with "reduced charging
speed"), and fusion pays neither penalty. That is the hybrid claim, measured.

---

## Phase 5 — Grounded generation ✅ *built — `query/generate.py`, 34 tests green*

**Build**
- [x] Prompt with numbered context blocks tagged `[n] {model} p.{page} — {section}`
- [x] Instructions: context only, inline `[n]` after each claim, refuse when uncovered
- [x] `[n]` parser → `Citation` objects mapped back to real chunks; out-of-range
      markers are dropped rather than rendered as dead links
- [x] Refusal path returns what's missing, not a generic apology — the model emits an
      `INSUFFICIENT_CONTEXT:` sentinel, stripped before the text reaches the reader
- [x] Token streaming, with retry up to the first emitted piece and no replay after it
- [x] Per-call token + cost accounting (`Answer.input_tokens` / `output_tokens`)
- [x] *Added*: `scripts/ask.py --answer` — the first end-to-end question-to-answer path
- [x] *Added*: retry/backoff on 429/503, mirroring `ingest/embed.py`

**Model change:** `gemini-2.5-flash` now 404s — *"no longer available to new users."*
Default moved to **`gemini-3.7-flash`**, verified working against this key. Pinned, not
`gemini-flash-latest`: an alias silently changes the system under the eval numbers, and
`gemini-flash-latest` was returning 503 when probed. The cost constants in
`query/generate.py` are still the old 2.5-flash rates and are marked UNVERIFIED.

**Model change 2026-08-20:** generation now runs **`gemini-3.5-flash-lite`**, set via
`GEN_MODEL` in `.env` (the `config.py` default is still `gemini-3.7-flash`). ID verified
against `client.models.list()` before the switch, per the "verify model IDs" rule. The
cost constants remain UNVERIFIED and are now wrong in a second way — they are 2.5-flash
rates being applied to flash-lite pricing.

**Tests**
- [x] `test_citation_parsing` — `[1]`, `[2][3]`, repeated `[1]`, out-of-range `[9]`
- [x] `test_every_claim_cited` → `uncited_sentences()` plus three tests around it
- [x] `test_refuses_unanswerable` — and that the refusal names what is missing
- [x] `test_no_outside_knowledge` — the prompt forbids prior knowledge; verified live
      against "warranty period in Kenya", which refuses
- [x] `test_citation_points_to_real_page` — cited pages and snippet match the chunk
- [x] `test_streaming_assembles` — and that a marker split across pieces still resolves
- [x] `@live test_end_to_end_answer` — plus a live refusal test
- [x] *Added*: retry tests — transient 503 retried, 404 not, no replay mid-stream

**Exit gate:** ⏳ **not yet run.** The 60-question sweep measuring uncited claims and
hallucinated settings paths needs `eval/run_eval.py` extended to the generation arm,
which is Phase 7 work. What is verified so far is one end-to-end answer (screenshot
question: 5 citations, every claim marked, correct pages) and one refusal.

Manual spot check, `--mode bm25 --answer "how do I take a screenshot"`:
15,300 in / 1,105 out tokens, ~7.5s, 5 citations resolving to five different manuals.

---

## Phase 6 — Chat UI ✅ *built — `app.py` + `query/session.py`, 34 tests green*

**Build**
- [x] `app.py` — Streamlit chat with message history
- [x] Streamed answer rendering, re-rendered from the assembled `Answer` at the end so
      the refusal sentinel never reaches the reader
- [x] Citations as expandable cards: snippet + manual + page + section path
- [x] Sidebar: model filter (28 manuals), mode toggle, passages-per-answer slider,
      clear-conversation button
- [x] Per-turn latency + token-cost readout, including what the question was
      *searched as* when expansion rewrote it
- [x] History feeds query expansion **only** — never the grounding context
- [x] Graceful error surface for API failure / empty index / missing key / bad model
- [x] *Added*: `query/expand.py` — the follow-up rewriting deferred from Phase 4
- [x] *Added*: `query/session.py` — the chat pipeline with no Streamlit in it, which is
      what makes any of this testable

**Tests**
- [x] `test_history_not_in_context` — no prior question or answer text in any grounding
      prompt, checked over a two-turn conversation
- [x] `test_mode_toggle_changes_results` — the sidebar toggle reaches the retriever and
      BM25 vs dense return different top hits
- [x] `test_citation_card_mapping` — each `[n]` resolves to the chunk, page and snippet
      it actually came from
- [x] `test_empty_index_message` — and a separate message for *no* index vs *empty* index
- [x] `test_api_failure_handled` — 429 surfaces as advice, and the next turn still works
- [x] *Added*: expansion tests — dependent-question detection, the rewrite instruction,
      fallback when the rewrite call fails, history truncation
- [x] *Added*: `test_multithread_store_is_readable_from_another_thread`
- [ ] **Manual gate:** 10 hand-driven multi-turn conversations, no dead ends — *yours to
      drive; deliberately not automated*

**Bug found by driving it:** `@st.cache_resource` holds one `Store` while Streamlit runs
every rerun on a fresh thread, and SQLite connections are thread-bound — the second
interaction died with *"SQLite objects created in a thread can only be used in that same
thread."* `Store(..., multithread=True)` now opts into `check_same_thread=False`, and is
refused outright when `create=True`: safe for the read-only query path, corruption for
ingestion.

**Verified by driving the real app** (Streamlit's `AppTest`, real store, real Gemini):
- Renders: title, mode radio, 28-manual filter, chat input, no exceptions
- One-turn: "how do I take a screenshot" → cited answer, 5 citation cards across 5 manuals
- Two-turn: "does the A52 have a headphone jack" → *"Yes, the Galaxy A52 5G includes an
  Earphone jack [1]"*; follow-up "what about wireless charging on it?" was searched as
  *"What about wireless charging on the A52?"* — expansion resolved the pronoun from
  history, and the grounding prompt still saw only chunks
- Retry worked against three real 503s mid-conversation

**Exit gate:** ⏳ needs a fresh-user run-through. The README now documents install →
ingest → `streamlit run app.py`, but nobody has followed it from a clean machine. Note
`streamlit` was in `requirements.txt` yet not installed in `.venv` — exactly the kind of
gap that run-through exists to catch.

---

## Phase 7 — Evaluation 🔶 *built, not re-measured — 286 tests green in 130s*

**Build**
- [x] 64 questions across four types — 16 factual / 28 procedural / 10 spec / 10
      unanswerable (exceeds the 40 originally planned)
- [x] Retrieval metrics: recall@1, recall@5, MRR, p50 + p95 latency
- [x] Ablation runner across all four arms (BM25 / dense / hybrid / hybrid+rerank)
- [x] `eval/RESULTS.md` — ablation table plus the per-question-type split that actually
      justifies hybrid, and a section on why the reranker does not earn its place
- [x] *Added*: `eval/generation.py` — the generation arm, scoring the **answer** and not
      just the retrieval that fed it: citation accuracy, refusal rate, false-refusal
      rate, uncited-claim rate, cost per query
- [x] *Added*: `eval/answers.md` — every generated answer recorded for reading, since
      aggregate scores hide the failures worth seeing
- [x] *Added*: resumable checkpointing (`eval/generation_checkpoint.json`, gitignored as
      a run artifact) — a 64-question generation sweep is too expensive to restart
- [x] *Added*: daily-quota handling in `query/generate.py` — `QuotaExhausted` stops the
      run instead of retrying. A per-minute 429 clears in seconds; a per-day one clears
      tomorrow, and retrying it burned four attempts and ~14s of backoff per call until
      a 64-question eval had spent its budget on the first few questions and reported
      the rest as model failures.
- [ ] Update README with the results summary — README still says "Phase 0"

**Tests** — 25 in `tests/test_eval.py`
- [x] `test_all_question_types_covered` — each of the four types has ≥8 questions
- [x] `test_metrics_math_mrr` / `test_metrics_math_recall_at_5` — parametrized against
      hand-computed fixtures
- [x] `test_question_ids_are_unique`, `test_unanswerable_questions_carry_no_gold_labels`
- [x] `test_is_hit_matches_section_or_body`, `test_expect_text_narrows_a_coarse_section`
- [x] Regression harness: `test_regression_passes_when_recall_holds`,
      `test_regression_tolerates_small_noise`, `test_regression_fails_on_a_real_drop`,
      `test_missing_baseline_is_not_a_failure`
- [x] Citation scoring: scored against the chunk it points at, zero for a chunk not in
      context, aggregated over citations rather than answers, `None` when uncited
- [x] Rate metrics exclude what they should — refusal rate counts only unanswerable and
      excludes errored questions, false-refusal counts only answerable, uncited-claim
      rate ignores refusals and errors, cost excludes failed calls, latency percentiles
      ignore errors
- [ ] `test_eval_reproducible` — two runs on a fixed index give identical retrieval metrics
- [ ] Regression wired into CI (the harness exists and is tested; nothing runs it)

**Exit gate:** ⏳ **blocked on corpus, not on code.** `eval/RESULTS.md` exists with the
ablation table and an honest account of what the system gets wrong — but it is measured
on the deleted 28-manual corpus and says so in its own first line. The gold set in
`eval/questions.yaml` references chunks and pages that no longer exist. Re-running the
sweep against today's 43-chunk placeholder would produce numbers, and every one of them
would be meaningless: R@5 over 43 chunks is near-free when 5 results cover most of the
corpus, and hybrid-vs-each-half has no room to show a difference.

**Decision (2026-08-20):** leave `eval/` untouched until a real manual lands. Rebuild
the gold set first, then re-measure. Do not "fix" the stale files in the meantime.

---

## Phase 8 — Figures in answers 🔶 *built — 316 tests green; human gate outstanding*

Answers that describe a screen now render the manual's illustration of it. Scope is
**display only**: figures never enter the grounding context, never reach the embedder,
and never affect ranking. The generator stays text-only, so every `[n]` still resolves
to text on a page.

**The decision that shaped the implementation.** Measured on the A05 excerpts before
writing any code:

| Observation | Consequence |
|---|---|
| Most raster XObjects are 6x17–19x11 pt | `page.get_images()` yields status-bar glyphs, not figures |
| On figure pages the raster and the vector paths share one bbox | Callouts are vector art **over** a raster screenshot |
| `getting-started` excerpt: 0 rasters, 0 drawings | Whole documents can be figure-free; no-figures is the normal case |

So **regions are rendered, not images extracted** — extracting the embedded image
returns the photo with none of the callout lines that say where to tap.

**Build**
- [x] `ingest/figures.py` — detection (`MIN_PT`, `PAGE_FRACTION`, `GAP`,
      `MAX_WORDS_INSIDE`) and content-addressed PNG rendering at 150 DPI
- [x] `ingest/parse.py` — figure blocks emitted at their vertical position in reading
      order, so a figure between two procedures attaches to the one it illustrates
- [x] `ingest/chunk.py` — a figure contributes no text and no tokens and never triggers
      a split; it lands on whichever chunk is open when reading order reaches it
- [x] `core/storage.py` — `figures` + `chunk_figures`; neither touches `chunks`, so the
      FTS triggers and chunk_id-is-the-vector-id are unaffected
- [x] Images written **inside** the store root, so `staging_store()` swaps database,
      index and images together
- [x] `query/generate.py` — figures attached to **cited** chunks only; a store predating
      the tables degrades to no figures rather than raising
- [x] `app.py` — rendered inline beneath the answer, above Sources, deduped, ≤3 columns
- [x] `--no-figures` for a text-only build

**Tests** — 27 new (23 in `tests/test_figures.py`, 4 in `tests/test_generate.py`)
- [x] Each detection threshold tested against the failure it prevents: inline icons,
      full-page background, prose-filled region, near/far clustering, reading order
- [x] Content-addressing renders one file for identical bytes
- [x] A vector-only page still yields a figure — the case XObject extraction misses
- [x] Figures absent from `embed_text()`; chunk text and token counts unchanged by them
- [x] A figure with no prose around it is dropped rather than drifting to another chunk
- [x] Storage round trip, one diagram shared by two chunks stored once, cascade delete
- [x] Uncited chunk contributes no figure; refusal shows none; missing tables degrade
- [ ] Association accuracy over a real manual — see the gate

**Verified end to end** (2026-08-31, scratch `DATA_ROOT`, live Gemini): 43 chunks
unchanged, 43/43 embedding cache hits — figures perturbed neither text nor vectors.
3 figures, 3 chunk links. "how do I take a photo" → the p.10 camera-preview figure;
"how do I zoom in while taking a picture" → the p.11 zoom figure; "what is the warranty
period" → refusal, no figures.

**Known false positive.** Of the 3 figures found, 2 are correct and 1 is the decorative
chapter-opener mark, attached to the "Introduction" chunk. It did not surface in any of
the three answers above because that chunk was never cited, but it will surface if it
ever is. **It was left in deliberately**: the obvious filters (page word count, outline
level, vector-only) would each also drop a legitimate full-page device-layout diagram,
and these excerpts carry **no PDF outline at all** (`get_toc()` returns 0 entries), so a
structural rule cannot be validated here. Revisit against a real manual; do not tune the
thresholds on the placeholder.

**Exit gate:** ⏳ **human, and blocked on corpus.** Sample 20 chunks that carry a figure
and read whether the picture matches the text — the same kind of gate as Phase 2's
30-chunk read, and for the same reason: an illustration attached to the wrong procedure
passes every assertion you could write for it. Three figures across 14 pages is not a
sample. The thresholds in `ingest/figures.py` are the first thing to revisit when a real
manual lands.

---

## Corpus replaced (2026-08-31) — real A05 manual

The two placeholder excerpts were deleted and replaced with a single real manual.

| | Placeholder | Now |
|---|---|---|
| Source | 2 A05 excerpts, 14 pages | `SM-A055F_UG_EU_Eng_Rev1.0_250507.pdf`, 32 pages |
| Chunks | 43 | **76** (median 89 tokens) |
| Figures | 3 (1 decorative) | **9**, on 8 chunks |
| Embedding | 43 cache hits | 76 new vectors, **2 API calls** |
| Ingest | 16s | 20s |

**The file had to be renamed.** It arrived as `SM-A05X_E055F_M055F_UG_EU_15_Eng_Rev.1.0_250507(2).pdf`
and scanned as model `unknown`, which would have printed "unknown" under every
citation. `_CODE_RE` needs `[SFAN]` + exactly three digits: `A05X` has a wildcard where
a digit belongs, and `E055F`/`M055F` start outside the letter set. Renamed to
`SM-A055F_…` so `A055` → "Galaxy A05". **The scanner accepting a file is not the same as
the scanner understanding it** — check the model it reports, not just that it indexed.

**No PDF outline.** `get_toc()` returns 0 entries, so `parse.py` ran on font heuristics
alone. It held up better than expected: **0 of 76 chunks have an empty `section_path`**,
and the names are specific ("Pairing with other Bluetooth devices", "Wi-Fi Direct").
The cost is that every path is **flat** — one level, no `chapter > section > subsection`
ancestry — because `_SectionTracker` only builds ancestry from the outline. Citations
read "Galaxy A05 p.24 — Pairing with other Bluetooth devices" rather than a full path.

**Retrieval spot-check** (5 questions, live): correct section and page on all four
answerable ones, clean refusal on "battery capacity in mAh" (the manual has no specs
table). No hallucinated citations.

### Figure association: the finding that matters

Figures land where the manual puts them, which is **not** where the answer usually
comes from. Samsung places the illustration under the section *intro*; a "how do I…"
question cites the *procedure* subsection beneath it. Measured:

| Question | Cited | Figure? |
|---|---|---|
| "how do I use split screen with two apps" | `Launching Multi window` | ✗ |
| "what is multi window and what views does it support" | `Multi window` | ✓ 2 |
| "how do I delete photos from the gallery" | `Deleting images or videos` | ✗ |
| "what can I do in the Gallery app" | `Using Gallery`, `Viewing images` | ✓ 2 |
| "how do I browse the internet" | `Samsung Internet` | ✓ 1 |

The association is *literally* correct — the figure is physically in the intro chunk —
but under the cited-chunks-only rule, figures fire on "what is X" and often miss on
"how do I X", which is the more common question.

**Decision (2026-08-31): keep it strict. Do not extend figures to sibling chunks under
the same parent section.** A figure renders only on the chunk it physically sits in, and
only when that chunk is cited. Missing an illustration is a cosmetic loss; showing one
next to a procedure it does not depict is a claim the manual never made, and it would
carry the same visual authority as the cited text. Spreading a figure across siblings
also breaks the property that makes the current rule defensible — that a rendered figure
is always physically part of the passage the answer used.

Do not re-open this as a "figures rarely show" bug. The low hit rate is the intended
cost. If it is ever revisited, the lever is **chunking** — the figure and the procedure
it illustrates landing in one chunk — not a looser figure-to-chunk mapping.

---

## Corpus reset (2026-08-20)

The 28-manual corpus was deleted at the user's request and replaced with a placeholder
pending a real manual. What changed:

| | Before | After |
|---|---|---|
| Manuals | 28 (5,108 pages, 197 MB) | 2 A05 excerpts (14 pages, 648 KB) |
| Chunks | 4,630 | 43 |
| Embedder | `bge-small-en-v1.5`, local, 384-dim | `gemini-embedding-001`, 768-dim |
| Generation | `gemini-3.7-flash` | `gemini-3.5-flash-lite` |
| Ingest wall time | ~14 min | **16s** |

**The two PDFs are excerpts, not manuals** — 3 pages of "Getting started" and 11 pages
of "Apps and features" starting at manual page 30. Page numbers in citations therefore
do not correspond to a real A05 manual's pagination. They were renamed to the
convention `ingest/metadata.py` expects (`SM-A055F_UG_EN_*.pdf`) because the scanner
skips anything whose filename carries no language token.

**Why the embedder changed.** The local backend cost ~150s of cold start per process,
of which ~140s was `import torch` + `import sentence_transformers` — before any weights
loaded. Measured warm: sentence-transformers 116.4s, torch 24.0s, faiss 2.7s, BGE
weights 8.6s, first encode 0.8s, subsequent encodes 0.08s. In the Streamlit app this
surfaced as a ~3-minute wait on first page render. Gemini embeddings remove the imports
entirely.

**The original rationale for local embeddings still stands and still applies later:**
the free tier caps at 1,000 items/day and the old corpus needed 4,630. At 43 chunks that
constraint is inert. If a real manual pushes the chunk count back into the thousands,
either re-quota or move BGE to an ONNX runtime (same weights, same vector space, seconds
of import instead of minutes) rather than reverting to torch.

`GeminiEmbedder` and `LocalEmbedder` remain interchangeable behind `build_embedder()`,
as CLAUDE.md requires. The embedding cache keys on `(model, task_type, dim, text)`, so
the backend switch was a clean full miss rather than a silent poisoning — the 43 stale
384-dim vectors were deleted from `data/cache/embeddings.db` by hand.

**Still outstanding from this reset:**
- [ ] Real A05 manual — everything above is placeholder
- [ ] Rebuild `eval/questions.yaml` gold set, then re-run the ablation
- [ ] `README.md` still says "Phase 0"
- [ ] Cost constants in `query/generate.py` are 2.5-flash rates applied to flash-lite
- [ ] Rotate the API key — it was pasted into `.env.example` (never committed; caught
      and reverted before the Phase 7 commit) and appears in a chat transcript

---

## Cross-cutting

- [x] `pytest -m "not live"` green at every phase gate — **286 passed, 7 deselected**
      (2026-08-20). No longer under 60s: 130s, dominated by Windows Defender scanning
      the venv during import. Real-time protection is on; excluding `.venv/` is the fix.
- [ ] Live tests runnable on demand and documented in the README
- [x] No secrets in the repo; `data/` never committed — verified 2026-08-20 with
      `git log -S`, which confirms no key ever reached history
- [ ] Every phase's exit gate recorded (pass/fail + date) as you go — Phases 5, 6 and 7
      all still carry ⏳ gates; 5 and 7 are blocked on corpus, 6 on a human run-through
