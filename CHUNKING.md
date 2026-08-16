# From PDF to Chunk

How a 217-page Samsung manual becomes retrievable pieces of text.

Two modules do the work, and they are deliberately separate:

| Module | Responsibility | Output |
|---|---|---|
| `ingest/parse.py` | Understand the **page** | ordered `Block`s (heading / body / table) |
| `ingest/chunk.py` | Understand the **passage** | `Chunk`s sized for embedding |

Parsing knows about fonts, coordinates and PDF outlines. Chunking knows nothing
about PDFs at all — it only sees labelled blocks. That split is why the chunker
can be tuned and re-tuned without touching PDF handling.

---

## Part 1 — Parsing

### What a PDF actually gives you

A PDF has no paragraphs, no headings, no sections. It has *glyphs at coordinates*.
PyMuPDF groups them into lines and spans, so one line looks like this:

```python
{'text': 'Wireless power sharing', 'size': 19.5, 'font': 'SamsungOne-700',
 'bbox': (45.4, 67.5, 234.1, 88.3)}
```

That is all the structure that exists. Everything else has to be reconstructed.

### Step 1: read the outline instead of guessing

The first thing I checked — before writing any parser — was whether these PDFs
carry an embedded outline. All 28 do:

```python
doc.get_toc()
# [1, 'Getting started',              5]
# [2, 'Introduction',                 5]
# [2, 'Device layout and functions',  6]
# [2, 'Charging the battery',        20]
```

This is **authoritative structure**: level, title, page. It is the difference
between guessing that 19.5pt bold means "section" and *knowing* that
"Charging the battery" is a level-2 section starting on page 20.

Font heuristics still exist, but only as a fallback for headings the outline
omits (Samsung's outline stops at level 3; deeper sub-headings are inferred).

> **Why this matters:** it works identically on a 2019 S10e manual and a 2026
> Fold manual, whose templates and font sizes differ.

### Step 2: find the body text size

Everything else is defined *relative* to body text, so the parser measures it —
per document, weighted by characters rather than lines:

```python
volume = {13.6: 40461, 16.6: 1802, 19.5: 641, 25.3: 337}   # size -> chars
body_size = 13.6
```

Character-weighting matters: a page can carry more heading lines than body lines
while body text still dominates the actual content.

### Step 3: drop the page furniture

Every page has a running chapter title at the top and a page number at the
bottom. Left in, they would appear in **every chunk** — 4,630 copies of the word
"Getting started" polluting the index.

They are removed by position, as fractions of page height:

```
y = 0                    ┌──────────────────────────┐
                         │  Getting started      ← header (y ≈ 2%)      DROP
y = 0.06 × height  ──────┼──────────────────────────┤
                         │  Wireless power sharing   ← heading (y ≈ 8%) KEEP
                         │  You can charge another…  ← body            KEEP
y = 0.94 × height  ──────┼──────────────────────────┤
                         │            22          ← page number (96%)   DROP
                         └──────────────────────────┘
```

The bands are wide enough to catch chrome and narrow enough that the first real
heading — consistently at ~8% — is never touched.

Front matter goes too: everything before the outline's first target page is
cover art and the manual's own printed contents list, which would otherwise
become chunks of disconnected section titles.

### Step 4: classify each line

For every surviving line, is it a heading or is it prose?

```python
def _heading_level(line, body_size, expected):
    if line.text matches an outline title on this page:
        return that outline level          # authoritative — always wins
    if len(text) < 3 or no letters in text:
        return 0                           # diagram callout: "1", "2"
    if _looks_like_prose(text):
        return 0                           # step, bullet, lead-in, continuation
    if line.size >= body_size + 1.5:
        return 3                           # unlisted sub-heading
    if line.bold and line.size > body_size and len(text) < 60:
        return 3
    return 0
```

`_looks_like_prose` rejects four patterns that *look* like headings typographically:

| Pattern | Example | Why it's not a heading |
|---|---|---|
| Numbered step | `1 Open Settings, tap Battery` | Steps are set in bold here |
| Bullet / note | `• Use only approved chargers` | ditto |
| Ends in punctuation | `Battery.` | Headings never end in `.` `,` `:` `;` |
| Starts lowercase/symbol | `→Settings→Auto-update apps` | A continuation line, mid-thought |

**Two bugs this logic exists because of:**

1. **The dominant-span bug.** I originally took each line's *largest* span to
   decide size. But body lines embed oversized icon glyphs and step numerals, so
   ordinary prose was promoted to heading — 181 headings against 109 body
   paragraphs. The fix is to take the span carrying the **most characters**:

   ```python
   dominant = max(spans, key=lambda s: len(s["text"].strip()))
   ```

2. **Wrapped headings.** A heading spanning two visual lines arrived split, so
   the first half became a truncated section title and the second half opened a
   bogus section. Real, visible damage — section paths are printed under every
   citation:

   ```
   Health and Safety > Warning: Failure to comply with safety warnings and
   Health and Safety > be covered by the warranty service
   ```

   Consecutive lines of identical size and weight, vertically adjacent, with no
   sentence-ending punctuation, are now rejoined before classification.

### Step 5: track the section path

A page can begin mid-section and contain several headings, so the parser keeps a
stack that updates whenever a heading is *seen*:

```
"Getting started"        (level 1) → stack: [Getting started]
"Charging the battery"   (level 2) → stack: [Getting started, Charging the battery]
"Wireless power sharing" (level 3) → stack: [Getting started, Charging the battery,
                                             Wireless power sharing]

section_path = "Getting started > Charging the battery > Wireless power sharing"
```

One subtlety: a chapter title drawn *only* as a running header gets stripped in
step 3 and would never enter the stack — silently costing every section beneath
it its chapter. So each outline entry's full ancestry is precomputed from the
outline itself and applied on match.

### Step 6: tables stay tables

Reference tables — button functions, status icons, specifications — are exactly
what spec questions ask about. Flattened to prose, the row/column pairing is
lost. So they are detected, excluded from the flowing text (to avoid
duplication), and serialized as markdown:

```markdown
| Button | Function |
|---|---|
| Recents ( ) | Tap to open the list of recent apps. |
| Home ( ) | • Tap to return to the Home screen. • Touch and hold to launch… |
| Back ( ) | Tap to return to the previous screen. |
```

### Parser output

```python
Block(text="You can charge another device with your phone's battery…",
      page=22,
      kind="body",
      section_path="Getting started > Charging the battery > Wireless power sharing")
```

A flat list of these, in reading order. The chunker takes it from here.

---

## Part 2 — Chunking

### The one rule

**A chunk never crosses a section boundary.**

A fixed-size window would splice the end of "Wireless power sharing" onto the
start of "Reducing battery consumption". The result answers neither question
well, yet ranks plausibly for both — the worst possible retrieval behaviour,
because it displaces a chunk that *would* have answered.

### Step 1: group by section

Blocks are grouped into runs sharing a section path. Heading text is **excluded**
from the body — it already lives in `section_path`, and repeating it inline would
double-count it at embed time.

### Step 2: merge short siblings

This was the biggest correction to the original plan. Section-bounded chunking
alone produced a **median of 66 tokens**, because Samsung subsections are tiny:

```
Turning the device off       ~90 tokens
Forcing restart              ~35 tokens
Emergency calls              ~87 tokens
```

Three separate chunks of near-nothing. Individually they carry almost no context,
and short chunks retrieve noisily.

But they share a parent — "Turning the device on and off" — so they are genuinely
related. Siblings under one parent merge up to the target size, each keeping its
own heading inline so no detail is lost:

```
section_path: Getting started > Turning the device on and off

  Turning the device off:
  1 Press and hold the Side button and the Volume Down button…

  Forcing restart:
  If your device is frozen and unresponsive, press and hold…

  Emergency calls and medical information:
  You can make an emergency call or check the medical information…
```

Rules:
- only siblings sharing the same parent merge
- a section already ≥60% of target stands alone, keeping its specific path
- a lone section keeps its own path and gets **no** inline label (it would repeat
  what the path already says)

**Result: median 66 → 308 tokens.**

### Step 3: pack, split and overlap

Within a group, blocks are packed until the target (~500 tokens) is reached:

```
target reached → emit chunk → carry ~80 tokens of tail into the next chunk
```

The overlap prefers to start at a sentence boundary, so a procedure cut across
two chunks keeps its lead-in on both sides.

Two special cases:

- **An oversized single paragraph** must split *within* the block, since packing
  only splits *between* blocks. It splits on sentence boundaries; if a "sentence"
  is still too long (unpunctuated bullet runs do occur), it falls back to word
  windows.
- **A table never splits.** Its rows would be stranded from the header row that
  names them.

### Step 4: the size floor

A fragment below ~20 tokens can never answer anything, so it is folded into the
previous chunk rather than emitted as its own.

### Chunker output

```python
Chunk(doc_id  = "S93X_S92X_UG_CA_16_ENG_D3",
      text    = "You can charge another device with your phone's battery…",
      section_path = "Getting started > Charging the battery > Wireless power sharing",
      page_start = 22, page_end = 22,
      token_count = 314)
```

### Why `section_path` is carried separately

It is prefixed onto the text **at embed time**, not stored inline:

```python
def embed_text(self):
    return f"{self.section_path}\n\n{self.text}"
```

This does two jobs at once:

1. **Retrieval.** A two-word question — "fast charging?" — has little to match
   against in a paragraph that never repeats its own title. The path supplies it.
2. **Citations.** The reader sees *Galaxy S24/S25 series, p.22 — Getting started >
   Charging the battery > Wireless power sharing*, which is checkable.

---

## The numbers

Across all 28 manuals (5,108 pages):

| Metric | Value |
|---|---|
| Chunks | 4,630 |
| Tokens p25 / p50 / p95 | 149 / 308 / 497 |
| Max tokens | 575 |
| Chunks over 800 tokens | 0 |
| Chunks with no section path | 0 |

Token counts are estimated (`words × 1.3`) rather than measured by API call —
chunking runs over thousands of candidate splits while tuning, and a network
round-trip per measurement would make that impossible.

## Inspecting it yourself

```bash
python -m scripts.dump_chunks --stats            # size distribution only
python -m scripts.dump_chunks --sample 30        # 30 random chunks
python -m scripts.dump_chunks --manual S93X --full --sample 5
```

The Phase 2 exit gate is a **person reading chunks**. No assertion catches text
that is well-formed but incoherent, and incoherent chunks stay invisible until
Phase 5, where they look like a generation problem instead of a parsing one.
