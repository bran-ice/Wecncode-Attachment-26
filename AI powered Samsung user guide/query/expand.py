"""Rewrite a follow-up question into one that stands on its own.

"Does it do that too?" is unanswerable by a retriever: it shares no content
words with anything in the manuals. The previous turns are what make it mean
something, so they are used *here*, to produce a self-contained query.

The hard rule this module exists to protect: **history feeds expansion only,
never the grounding context.** The generator sees retrieved chunks and nothing
else. If a prior turn could reach the grounding prompt, the model could ground
a claim in something it said earlier — which is how a system with citations
starts citing itself and drifts away from the manual without any single step
looking wrong.

Expansion is skipped when the question already stands alone. Most questions do,
the rewrite costs a model call, and a rewrite of a clear question is a chance to
make it worse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

from core.logging_setup import get_logger

log = get_logger(__name__)

# Words that only resolve against something already said. "it", "that", "those"
# and bare "the one" are the common shapes a follow-up takes.
_DEPENDENT = re.compile(
    r"\b(it|its|it's|that|this|those|these|there|them|they|he|she|"
    r"same|also|too|instead|as well|the one|what about|how about)\b",
    re.IGNORECASE,
)

# An opening that is grammatically a continuation, not a new question.
_CONTINUATION = re.compile(
    r"^\s*(and|but|so|then|what about|how about|why|ok|okay|yes|no)\b", re.IGNORECASE
)

MAX_HISTORY_TURNS = 4
SHORT_QUESTION_WORDS = 6

EXPANSION_INSTRUCTION = """\
Rewrite the user's latest question so it stands alone, using the conversation \
for context. Resolve pronouns and implied subjects into explicit nouns.

Rules:
- Output ONLY the rewritten question. No preamble, no explanation.
- Keep the user's wording where it is already explicit. This is a rewrite, not \
an improvement.
- Never invent a device model, setting name or feature that does not appear in \
the conversation.
- If the question already stands alone, output it unchanged."""


@dataclass
class Turn:
    """One exchange. `answer` is stored for expansion context only."""

    question: str
    answer: str = ""


@dataclass
class Expansion:
    """The queries to search with, and how they were arrived at."""

    queries: list[str] = field(default_factory=list)
    rewritten: Optional[str] = None
    used_history: bool = False

    @property
    def primary(self) -> str:
        return self.queries[0] if self.queries else ""


def looks_dependent(question: str, history: Sequence[Turn]) -> bool:
    """Does this question need earlier turns to make sense?

    Deliberately generous: a needless rewrite of a clear question is cheap, but
    failing to rewrite a genuine follow-up retrieves nothing at all.
    """
    if not history:
        return False
    if _CONTINUATION.match(question):
        return True
    if _DEPENDENT.search(question):
        return True
    # A very short question with no verb is usually an elliptical follow-up
    # ("the S24?", "battery life?").
    return len(question.split()) <= SHORT_QUESTION_WORDS and "?" in question


def render_history(history: Sequence[Turn], max_turns: int = MAX_HISTORY_TURNS) -> str:
    lines = []
    for turn in list(history)[-max_turns:]:
        lines.append(f"User: {turn.question}")
        if turn.answer:
            # Only the gist is needed to resolve a pronoun; a full prior answer
            # would crowd out the actual question.
            lines.append(f"Assistant: {turn.answer[:300]}")
    return "\n".join(lines)


def expand_query(
    question: str,
    history: Sequence[Turn] = (),
    generator=None,
) -> Expansion:
    """Return the queries to retrieve with.

    Both the rewrite and the original are searched: the rewrite may have
    resolved a pronoun wrongly, and RRF is unbothered by an extra list.
    """
    question = question.strip()
    if not looks_dependent(question, history) or generator is None:
        return Expansion(queries=[question])

    prompt = (
        f"CONVERSATION:\n{render_history(history)}\n\n"
        f"LATEST QUESTION: {question}\n\nREWRITTEN QUESTION:"
    )
    try:
        rewritten = generator.generate_with_instruction(
            prompt, EXPANSION_INSTRUCTION
        ).strip()
    except Exception as exc:
        # A failed rewrite must not fail the turn — retrieving on the raw
        # question is worse, not fatal.
        log.warning("Query expansion failed (%s); using the raw question", exc)
        return Expansion(queries=[question])

    rewritten = rewritten.strip().strip('"')
    if not rewritten or rewritten.lower() == question.lower():
        return Expansion(queries=[question], used_history=True)

    log.info("Expanded %r -> %r", question, rewritten)
    return Expansion(
        queries=[rewritten, question], rewritten=rewritten, used_history=True
    )
