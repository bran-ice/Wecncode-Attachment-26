"""Turn a manual filename + PDF properties into Document metadata.

Samsung's filenames are semi-structured and inconsistent across years, e.g.

    SAM_S911_S916_S918_EN_UM_OS13_030223.pdf   -> Galaxy S23 family, English, Android 13
    SM-S928U_UM_EN_OS14.pdf                    -> Galaxy S24 Ultra, English, Android 14
    galaxy-s24-ultra_en_um.pdf                 -> Galaxy S24 Ultra, English

The model code is what matters most: it is the only reliable identifier, and it
is what a user's question ("my S24 Ultra") has to be matched against later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Samsung model codes -> marketing names. Codes are the stable identifier; the
# trailing letter is a regional/carrier variant (U=US, B=Europe, N=Korea...)
# and is deliberately stripped before lookup.
MODEL_CODES: dict[str, str] = {
    # Galaxy S
    "S901": "Galaxy S22",
    "S906": "Galaxy S22+",
    "S908": "Galaxy S22 Ultra",
    "S911": "Galaxy S23",
    "S916": "Galaxy S23+",
    "S918": "Galaxy S23 Ultra",
    "S921": "Galaxy S24",
    "S926": "Galaxy S24+",
    "S928": "Galaxy S24 Ultra",
    "S931": "Galaxy S25",
    "S936": "Galaxy S25+",
    "S937": "Galaxy S25 Edge",
    "S938": "Galaxy S25 Ultra",
    # Foldables
    "F700": "Galaxy Z Flip",
    "F707": "Galaxy Z Flip 5G",
    "F711": "Galaxy Z Flip3",
    "F721": "Galaxy Z Flip4",
    "F731": "Galaxy Z Flip5",
    "F741": "Galaxy Z Flip6",
    "F900": "Galaxy Fold",
    "F916": "Galaxy Z Fold2",
    "F926": "Galaxy Z Fold3",
    "F936": "Galaxy Z Fold4",
    "F946": "Galaxy Z Fold5",
    "F956": "Galaxy Z Fold6",
    # A series
    "A505": "Galaxy A50",
    "A515": "Galaxy A51",
    "A526": "Galaxy A52 5G",
    "A536": "Galaxy A53 5G",
    "A546": "Galaxy A54 5G",
    "A556": "Galaxy A55 5G",
    "A055": "Galaxy A05",
    "A057": "Galaxy A05s",
    "A065": "Galaxy A06",
    "A155": "Galaxy A15",
    "A156": "Galaxy A15 5G",
    "A165": "Galaxy A16",
    "A166": "Galaxy A16 5G",
    "A256": "Galaxy A25 5G",
    "A266": "Galaxy A26 5G",
    "A336": "Galaxy A33 5G",
    "A346": "Galaxy A34",
    "A356": "Galaxy A35 5G",
    # Galaxy S10 era
    "G970": "Galaxy S10e",
    "G973": "Galaxy S10",
    "G975": "Galaxy S10+",
    "G977": "Galaxy S10 5G",
    # Codes deliberately absent (S942/S947/S948, F766, F966, F971, F976, F776,
    # A566, A576, A366, A376): naming them would be a guess, and the guess would
    # be printed under every citation from that manual. `display_model` falls
    # back to the raw code instead, which is ugly but true.
}

# Marketing names appearing directly in a filename, e.g. "galaxy-s24-ultra".
_NAME_RE = re.compile(
    r"galaxy[\s_-]*(s|a|z[\s_-]*fold|z[\s_-]*flip)[\s_-]*(\d{1,2})[\s_-]*(ultra|plus|\+)?",
    re.IGNORECASE,
)

# `\b` is useless here: underscore counts as a word character, so `\b` never
# fires in `SM-S928U_UM` or `SAM_S911_S916`, which is most Samsung filenames.
# These lookarounds treat `_` and `-` as separators, which is what they are.
_CODE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:SM[-_])?([SFAN]\d{3})([A-Z])?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
# Same underscore caveat as _CODE_RE: `_OS14` has no word boundary before OS.
_OS_RE = re.compile(
    r"(?<![A-Za-z0-9])OS[\s_-]?(\d{1,2})(?![A-Za-z0-9])", re.IGNORECASE
)
_ONEUI_RE = re.compile(
    r"(?<![A-Za-z0-9])one[\s_-]?ui[\s_-]?(\d(?:\.\d)?)(?![A-Za-z0-9])", re.IGNORECASE
)

LANGUAGES = {
    "EN": "en", "ES": "es", "FR": "fr", "DE": "de", "IT": "it", "PT": "pt",
    "KO": "ko", "ZH": "zh", "JA": "ja", "AR": "ar", "RU": "ru", "NL": "nl",
    "PL": "pl", "TR": "tr", "SV": "sv", "ENG": "en",
}

REGIONS = {"US", "UK", "EU", "CA", "AU", "IN", "KR", "SEA", "LATIN", "MEA"}


@dataclass
class ManualMeta:
    model: str
    model_codes: list[str]
    language: str
    region: Optional[str] = None
    os_version: Optional[str] = None
    title: Optional[str] = None

    @property
    def is_english(self) -> bool:
        return self.language == "en"


# Trailing words that mark a variant within one family, not a family of its own.
_VARIANT_WORDS = {"ultra", "+", "plus", "5g", "edge", "fe"}


def _family_of(name: str) -> str:
    """"Galaxy S24 Ultra" -> "Galaxy S24"; "Galaxy Z Fold5" stays whole.

    Truncating to a fixed word count would fold Z Fold5 and Z Fold6 together
    (both start "Galaxy Z"), so only known variant suffixes are stripped.
    """
    words = name.split()
    while len(words) > 2 and words[-1].lower() in _VARIANT_WORDS:
        words.pop()
    words[-1] = words[-1].rstrip("+") or words[-1]  # "S24+" and "S24" are one family
    return " ".join(words)


def display_model(model_codes: list[str]) -> str:
    """Name the device(s) one manual covers.

    A Samsung manual usually serves a whole family, so the label has to describe
    a set: `S93X_S92X` covers the S24 *and* S25 lines, and calling it "Galaxy S25
    series" would put a wrong device name under every citation drawn from it.

    Codes with no confident mapping are shown verbatim rather than guessed.
    """
    codes = [re.sub(r"^SM-", "", c.upper()).rstrip("W") for c in model_codes]
    codes = [c[:4] for c in codes if c]

    named = [MODEL_CODES[c] for c in codes if c in MODEL_CODES]
    unknown = sorted({c for c in codes if c not in MODEL_CODES})

    families: list[str] = []
    for name in named:
        family = _family_of(name)
        if family not in families:
            families.append(family)

    families.sort()  # deterministic label: "Z Flip3/Z Flip4/Z Flip5", never shuffled

    if families:
        if len(named) == 1:
            label = named[0]
        elif len(families) == 1:
            label = f"{families[0]} series"
        else:
            head = families[0]
            rest = [f.replace("Galaxy ", "") for f in families[1:]]
            label = f"{head}/{'/'.join(rest)} series"
        return f"{label} (+{'/'.join(unknown)})" if unknown else label

    return f"Galaxy {'/'.join(unknown)}" if unknown else ""


def _tokens(stem: str) -> list[str]:
    return [t for t in re.split(r"[\s_\-.]+", stem) if t]


def parse_model(text: str) -> tuple[str, list[str]]:
    """Return (marketing name, model codes found). Name is "" when unknown."""
    codes: list[str] = []
    for match in _CODE_RE.finditer(text):
        code = match.group(1).upper()
        if code not in codes:
            codes.append(code)

    known = [c for c in codes if c in MODEL_CODES]
    if known:
        # A multi-model manual (S911_S916_S918) is named for its family; the
        # highest code is the Ultra, and using it alone would mislabel the file.
        names = [MODEL_CODES[c] for c in known]
        return (names[0] if len(names) == 1 else _family_name(names), codes)

    if name_match := _NAME_RE.search(text):
        series, number, variant = name_match.groups()
        series = re.sub(r"[\s_-]+", " ", series).title().replace("Z ", "Z ")
        variant = {"plus": "+", "+": "+"}.get(
            (variant or "").lower(), (variant or "").title()
        )
        joined = f"Galaxy {series.upper() if len(series) == 1 else series}{number}"
        return (f"{joined} {variant}".strip(), codes)

    return ("", codes)


def _family_name(names: list[str]) -> str:
    """"Galaxy S23 / S23+ / S23 Ultra" -> "Galaxy S23 series"."""
    base = names[0].split()[:2]  # e.g. ["Galaxy", "S23"]
    return " ".join(base) + " series"


def parse_language(tokens: list[str]) -> str:
    for tok in tokens:
        if (code := tok.upper()) in LANGUAGES:
            return LANGUAGES[code]
    return "unknown"


def parse_region(tokens: list[str]) -> Optional[str]:
    for tok in tokens:
        if (code := tok.upper()) in REGIONS:
            return code
    return None


def parse_os_version(text: str) -> Optional[str]:
    if m := _ONEUI_RE.search(text):
        return f"One UI {m.group(1)}"
    if m := _OS_RE.search(text):
        return f"Android {m.group(1)}"
    return None


def from_filename(path: str | Path) -> ManualMeta:
    stem = Path(path).stem
    tokens = _tokens(stem)
    model, codes = parse_model(stem)
    return ManualMeta(
        model=model,
        model_codes=codes,
        language=parse_language(tokens),
        region=parse_region(tokens),
        os_version=parse_os_version(stem),
    )


def enrich_from_pdf(meta: ManualMeta, pdf_metadata: dict, first_page_text: str = "") -> ManualMeta:
    """Fill gaps using the PDF's own properties and cover page.

    Filenames are the primary source because PDF `title` fields are frequently
    empty or boilerplate ("Microsoft Word - UM.doc"), but they usefully fill in
    a missing model or OS version.
    """
    title = (pdf_metadata.get("title") or "").strip()
    if title and not _looks_like_boilerplate(title):
        meta.title = title

    if not meta.model:
        model, codes = parse_model(f"{title} {first_page_text[:2000]}")
        if model:
            meta.model = model
            meta.model_codes = meta.model_codes or codes

    if not meta.os_version:
        meta.os_version = parse_os_version(f"{title} {first_page_text[:2000]}")

    if not meta.title:
        meta.title = f"{meta.model} User Manual" if meta.model else Path("").name

    return meta


def _looks_like_boilerplate(title: str) -> bool:
    lowered = title.lower()
    return (
        lowered.endswith((".doc", ".docx", ".indd", ".pdf"))
        or lowered.startswith("microsoft word")
        or lowered in {"untitled", "user manual", "um"}
    )
