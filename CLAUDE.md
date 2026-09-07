# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository shape

This is **two things in one repo**, and they do not interact:

- `AI powered Samsung user guide/` — the real project: a hybrid RAG system over Samsung
  Galaxy manuals. It has **its own `CLAUDE.md`, which is the authority for all work
  inside it** — architecture invariants, hard rules, conventions, model defaults. Read it
  before touching anything in that folder. This file only covers what is true at the
  repo root and what the folder move left behind.
- `WEEK 1`–`WEEK 8`, `Bonus week -2`, `Python Foundations/`, `Python for developers1/`,
  and the root notebooks — self-contained coursework exercises. One file per topic, no
  build, no tests, no shared imports. Don't refactor across them; each stands alone.

## The 2026-09-02 move left things at the root (commit `1f47206`)

The RAG project's source moved into `AI powered Samsung user guide/`, but the files it
depends on stayed at the repo root. Four consequences, all verified. The merge behind
that commit also left **conflict markers in `AI powered Samsung user guide/.gitignore`**
— resolved 2026-09-07, keeping the project's own patterns.

- **The store lives at the repo root `data/`, not beside the code** (1 manual, 76
  chunks, 9 figures). `core/config.PROJECT_ROOT` is the folder containing `core/`, so
  `data_root` would resolve to the non-existent `AI powered Samsung user guide/data`
  and everything would report "no store". **Fixed 2026-09-07** by `DATA_ROOT=../data`
  in `AI powered Samsung user guide/.env` — `load_settings` resolves a relative
  `DATA_ROOT` against `PROJECT_ROOT`. `.env` is gitignored, so a fresh clone hits this
  again; that line is not optional configuration.
- **`Implementation.md` and `CHUNKING.md` are at the root.** The project's `CLAUDE.md`
  now links them as `../`; `README.md` still says `./Implementation.md` and
  `./CHUNKING.md` — those two links are still broken.
- **`.venv/` is at the root**, so from inside the project folder the interpreter is
  `../.venv/Scripts/python.exe`.
- **`data/` was committed and pushed; history has been rewritten to remove it.**
  14 files / 2.6 MB lived under the root `data/` — including
  `SM-A055F_UG_EU_Eng_Rev1.0_250507.pdf` (Samsung's copyrighted manual), `corpus.db`,
  `index.faiss`, the embedding cache and the extracted figure PNGs — in violation of the
  project's own "never commit `data/`" rule. It happened because the repo had no root
  `.gitignore` while the project's own one covered only its subtree.

  Cleaned 2026-09-07: root `.gitignore` added, `git rm -r --cached data/`, then
  `git filter-repo --invert-paths --path data/` and a force-push. `data/` now appears in
  zero commits, all 81 original commit messages survive in order, and 35 commit hashes
  changed — **any pre-2026-09-07 commit SHA for this repo is dead.**

  **The old blobs are still served by GitHub.** Unreachable objects survive until
  GitHub garbage-collects, and fetching the old SHA `1f47206` by hand still returns the
  1,058,931-byte PDF. Only GitHub Support can purge them. Until they confirm, treat the
  manual as having been publicly exposed.

## Commands

Run these from `AI powered Samsung user guide/`. Interpreter paths assume the root venv.

```powershell
../.venv/Scripts/python.exe -m pytest -m "not live"      # default suite: 317 tests, no network
../.venv/Scripts/python.exe -m pytest tests/test_retrieve.py::test_name   # one test
../.venv/Scripts/python.exe -m pytest -m live            # hits the real Gemini API, costs quota
../.venv/Scripts/streamlit.exe run app.py                # the chat UI — the product
../.venv/Scripts/python.exe -m ingest.acquire --scan     # data/raw/*.pdf -> catalog/manifest.json
../.venv/Scripts/python.exe -m ingest                    # build the store
../.venv/Scripts/python.exe -m scripts.ask --answer "how do I take a screenshot"
```

The test suite builds its own fixtures and never reads the real store, which is why a
green suite does **not** tell you the app can find its data — check that separately
after touching paths or `DATA_ROOT`.

## Where to look

`AI powered Samsung user guide/Phases.md` is the source of truth for what is built and
what is next — ahead of `README.md`, and ahead of this file. `Implementation.md` (root)
holds architecture and decisions; `CHUNKING.md` (root) explains how a PDF becomes
retrievable chunks and should be read before editing `ingest/chunk.py`.
