"""Pack parsed blocks into retrievable chunks.

The rule that matters: **a chunk never crosses a section boundary.** Fixed-size
windows would splice the end of "Wireless power sharing" onto the start of
"Reducing battery consumption", and the resulting chunk answers neither question
well while ranking plausibly for both.

Within a section, blocks are packed up to a target size with a small overlap so
a procedure split across two chunks keeps its lead-in on both sides.

Each chunk carries its `section_path`, which is prefixed onto the text at embed
time. That is what lets a two-word question ("fast charging?") match, and what
makes a citation legible.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from core.logging_setup import get_logger
from core.schema import Chunk
from ingest.parse import Block, ParsedDoc

log = get_logger(__name__)

TARGET_TOKENS = 500
OVERLAP_TOKENS = 80
MIN_TOKENS = 20  # below this a chunk is a stray caption, not an answer
MAX_TOKENS = 800


def estimate_tokens(text: str) -> int:
    """Approximate token count without calling the API.

    Chunking runs over thousands of candidate splits while tuning, so a network
    round-trip per measurement is out of the question. English averages ~1.3
    tokens per whitespace word for this kind of instructional prose; the
    tolerance in `TARGET_TOKENS` absorbs the error.
    """
    words = len(text.split())
    return int(words * 1.3) + text.count("|") // 4


def _tail_overlap(text: str, tokens: int = OVERLAP_TOKENS) -> str:
    """The last ~`tokens` worth of words, cut at a sentence boundary if possible."""
    words = text.split()
    take = max(1, int(tokens / 1.3))
    tail = " ".join(words[-take:]) if len(words) > take else text

    # Prefer starting the overlap at a sentence break, so the carried-over text
    # reads as a fragment of prose rather than starting mid-clause.
    match = re.search(r"(?<=[.!?])\s+", tail)
    return tail[match.end() :] if match and match.end() < len(tail) - 20 else tail


def chunk_document(
    parsed: ParsedDoc,
    doc_id: str,
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    """Turn one parsed manual into chunks, in reading order."""
    chunks: list[Chunk] = []

    for section_path, blocks in _merge_small_siblings(
        _group_by_section(parsed.blocks), target_tokens
    ):
        chunks.extend(
            _chunk_section(
                section_path, blocks, doc_id, target_tokens, overlap_tokens
            )
        )

    log.info(
        "%s: %d chunks (median %d tokens)",
        parsed.path.name,
        len(chunks),
        _median([c.token_count for c in chunks]) if chunks else 0,
    )
    return chunks


def _group_by_section(blocks: Iterable[Block]) -> list[tuple[str, list[Block]]]:
    """Consecutive blocks sharing a section path, headings excluded from content.

    The heading text is not repeated in the chunk body — it is already carried
    in `section_path` and prefixed at embed time, so including it inline would
    double-count it in the ranking.
    """
    groups: list[tuple[str, list[Block]]] = []
    for block in blocks:
        if block.is_heading():
            continue
        if groups and groups[-1][0] == block.section_path:
            groups[-1][1].append(block)
        else:
            groups.append((block.section_path, [block]))
    return groups


def _parent_of(section_path: str) -> str:
    parts = section_path.split(" > ")
    return " > ".join(parts[:-1]) if len(parts) > 1 else section_path


def _leaf_of(section_path: str) -> str:
    return section_path.split(" > ")[-1] if section_path else ""


def _merge_small_siblings(
    groups: list[tuple[str, list[Block]]], target_tokens: int
) -> list[tuple[str, list[Block]]]:
    """Combine short sibling subsections that share a parent section.

    Samsung subsections are small — "Forcing restart" is one sentence. Left
    alone, each becomes a 30-token chunk with almost no context, and retrieval
    on such fragments is noisy. Siblings under one parent ("Turning the device
    on and off") are genuinely related, so merging them up to the target size
    yields a chunk that reads like a coherent passage.

    Each merged subsection keeps its own heading inline, so the detail the
    section path would otherwise lose stays in the text.
    """
    merged: list[tuple[str, list[Block]]] = []
    buffer: list[tuple[str, list[Block]]] = []  # (section_path, blocks) per sibling
    buffer_parent: Optional[str] = None
    buffer_tokens = 0

    def flush() -> None:
        """Emit the buffered siblings as one group.

        Sub-headings are added only when siblings actually combined. A lone
        section keeps its own specific path, and labelling it would repeat text
        the path already carries — which is then double-counted at embed time.
        """
        nonlocal buffer, buffer_parent, buffer_tokens
        if buffer:
            if len(buffer) == 1:
                merged.append((buffer[0][0], buffer[0][1]))
            else:
                combined: list[Block] = []
                for path, blocks in buffer:
                    if leaf := _leaf_of(path):
                        combined.append(Block(f"{leaf}:", blocks[0].page, "body", 0, path))
                    combined.extend(blocks)
                merged.append((buffer_parent or "", combined))
        buffer, buffer_parent, buffer_tokens = [], None, 0

    for section_path, blocks in groups:
        tokens = sum(estimate_tokens(b.text) for b in blocks)
        parent = _parent_of(section_path)

        if tokens >= target_tokens * 0.6:
            flush()  # big enough to stand alone
            merged.append((section_path, blocks))
            continue

        if buffer and (parent != buffer_parent or buffer_tokens + tokens > target_tokens):
            flush()

        buffer_parent = parent
        buffer.append((section_path, blocks))
        buffer_tokens += tokens

    flush()
    return merged


def _chunk_section(
    section_path: str,
    blocks: list[Block],
    doc_id: str,
    target_tokens: int,
    overlap_tokens: int,
) -> list[Chunk]:
    out: list[Chunk] = []
    buffer: list[str] = []
    tokens = 0
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    carry = ""

    def emit() -> None:
        nonlocal buffer, tokens, page_start, page_end, carry
        text = "\n\n".join(buffer).strip()
        if not text:
            buffer, tokens = [], 0
            return
        count = estimate_tokens(text)
        if count >= MIN_TOKENS or not out:
            out.append(
                Chunk(
                    doc_id=doc_id,
                    text=text,
                    section_path=section_path,
                    page_start=page_start or 1,
                    page_end=page_end or page_start or 1,
                    token_count=count,
                )
            )
            carry = _tail_overlap(text, overlap_tokens)
        elif out:
            # Too small to stand alone: fold it into the previous chunk rather
            # than emit a fragment that can never answer anything.
            previous = out[-1]
            previous.text = f"{previous.text}\n\n{text}"
            previous.page_end = page_end or previous.page_end
            previous.token_count = estimate_tokens(previous.text)
        buffer, tokens = [], 0

    for block in _split_oversized(blocks, target_tokens):
        block_tokens = estimate_tokens(block.text)

        # A table is a unit: splitting it strands rows from their header row.
        if block.kind == "table" and buffer and tokens + block_tokens > target_tokens:
            emit()
            page_start = page_end = None

        if tokens and tokens + block_tokens > target_tokens:
            emit()
            page_start = page_end = None
            if carry:
                buffer.append(carry)
                tokens = estimate_tokens(carry)

        if page_start is None:
            page_start = block.page
        page_end = block.page
        buffer.append(block.text)
        tokens += block_tokens

        if tokens > MAX_TOKENS:
            emit()
            page_start = page_end = None

    emit()
    return out


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _atoms(text: str, target_tokens: int) -> list[str]:
    """Sentences, with any single over-long sentence cut into word windows.

    Sentence boundaries are the natural seam, but they are not guaranteed:
    bullet runs and table-ish text extracted from a PDF can arrive as one
    unpunctuated blob, and without a fallback such a block would refuse to split
    at all.
    """
    atoms: list[str] = []
    for sentence in _SENTENCE_END.split(text):
        if estimate_tokens(sentence) <= target_tokens:
            atoms.append(sentence)
            continue
        words = sentence.split()
        span = max(1, int(target_tokens / 1.3))
        atoms.extend(" ".join(words[i : i + span]) for i in range(0, len(words), span))
    return atoms


def _split_oversized(blocks: list[Block], target_tokens: int) -> list[Block]:
    """Break up any single block larger than the target.

    Packing only ever splits *between* blocks, so one long paragraph would
    otherwise become one oversized chunk — and oversized chunks dilute the
    embedding: the passage's actual topic gets averaged with everything else in
    it. Tables are exempt; their rows must stay with their header row.
    """
    out: list[Block] = []
    for block in blocks:
        if block.kind == "table" or estimate_tokens(block.text) <= target_tokens:
            out.append(block)
            continue

        piece: list[str] = []
        tokens = 0
        for sentence in _atoms(block.text, target_tokens):
            sentence_tokens = estimate_tokens(sentence)
            if piece and tokens + sentence_tokens > target_tokens:
                out.append(Block(" ".join(piece), block.page, block.kind, 0, block.section_path))
                piece, tokens = [], 0
            piece.append(sentence)
            tokens += sentence_tokens
        if piece:
            out.append(Block(" ".join(piece), block.page, block.kind, 0, block.section_path))
    return out


def _median(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[len(ordered) // 2]
