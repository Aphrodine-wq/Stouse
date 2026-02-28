"""Natural-language parser for homeowner vibe descriptions.

Converts free-form text such as:

    "I want a modern 4-bedroom home with 3 bathrooms, two stories,
     around 2500 sqft on our half-acre lot.  Budget is 400-550k.
     Must have a 3-car garage, home office, and big outdoor patio."

into a structured ``RequirementSpecification`` (RSO).

This is a mock / heuristic implementation.  A production version would call
an LLM for extraction, but the keyword-based approach here is deterministic
and fast enough for development and testing.
"""

from __future__ import annotations

import re

from vibehouse.core.vibe_engine.schemas import RequirementSpecification


# ---------------------------------------------------------------------------
# Keyword maps
# ---------------------------------------------------------------------------

_STYLE_KEYWORDS: dict[str, str] = {
    "modern": "modern",
    "contemporary": "contemporary",
    "farmhouse": "farmhouse",
    "farm house": "farmhouse",
    "craftsman": "craftsman",
    "colonial": "colonial",
    "ranch": "ranch",
    "mid-century": "contemporary",
    "mid century": "contemporary",
    "minimalist": "modern",
    "traditional": "colonial",
    "rustic": "farmhouse",
    "industrial": "modern",
    "mediterranean": "contemporary",
    "tudor": "colonial",
    "victorian": "colonial",
    "cape cod": "colonial",
}

_WORD_TO_NUM: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_SPECIAL_FEATURES: list[str] = [
    "home office",
    "office",
    "wine cellar",
    "theater",
    "media room",
    "gym",
    "workshop",
    "mudroom",
    "mud room",
    "pantry",
    "walk-in closet",
    "laundry room",
    "bonus room",
    "playroom",
    "library",
    "sunroom",
    "sun room",
    "sauna",
    "pool",
    "hot tub",
    "ev charging",
    "smart home",
    "solar",
    "accessibility",
    "ada",
    "guest suite",
    "in-law suite",
    "mother-in-law",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_number_before(text: str, keyword: str) -> int | None:
    """Find a digit or word-number directly before *keyword* in *text*.

    Examples that match:
        ``"4 bedrooms"``  -> 4
        ``"four bedroom"`` -> 4
        ``"4-bedroom"``    -> 4
    """
    # Digit form: "4 bedrooms", "4-bedroom"
    pattern = rf"(\d+)\s*[-\s]?\s*{keyword}"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Word form: "four bedrooms"
    word_pattern = rf"({'|'.join(_WORD_TO_NUM.keys())})\s+{keyword}"
    match = re.search(word_pattern, text, re.IGNORECASE)
    if match:
        return _WORD_TO_NUM[match.group(1).lower()]

    return None


def _extract_sqft(text: str) -> int | None:
    """Try to pull a square-footage number from the text."""
    patterns = [
        r"(\d[\d,]*)\s*(?:sq\.?\s*ft|square\s*feet|sqft|sf)",
        r"(\d[\d,]*)\s*(?:square\s*foot)",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _extract_budget(text: str) -> tuple[int, int] | None:
    """Extract a budget range like '400-550k' or '$400,000 to $550,000'."""
    # "400-550k" or "400k-550k"
    m = re.search(r"\$?([\d,.]+)\s*k?\s*[-–to]+\s*\$?([\d,.]+)\s*k", text, re.IGNORECASE)
    if m:
        lo = float(m.group(1).replace(",", ""))
        hi = float(m.group(2).replace(",", ""))
        # If values look like they are in thousands
        if lo < 1_000:
            lo *= 1_000
        if hi < 1_000:
            hi *= 1_000
        return int(lo), int(hi)

    # "$400,000 to $550,000"
    m = re.search(
        r"\$?([\d,]+)\s*(?:to|-|–)\s*\$?([\d,]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        lo = int(m.group(1).replace(",", ""))
        hi = int(m.group(2).replace(",", ""))
        if lo > 10_000 and hi > 10_000:
            return lo, hi

    # Single budget figure: "budget of $500k", "budget around 500000"
    m = re.search(r"budget\s*(?:of|around|about|is|:)?\s*\$?([\d,]+)\s*k?", text, re.IGNORECASE)
    if m:
        val = float(m.group(1).replace(",", ""))
        if val < 1_000:
            val *= 1_000
        val = int(val)
        # Create a +/- 20% range
        return int(val * 0.8), int(val * 1.2)

    return None


def _extract_lot_sqft(text: str) -> int | None:
    """Extract lot size.  Understands acres and square feet."""
    # Acres: "half acre", "0.5 acre", "1 acre"
    m = re.search(r"([\d.]+)\s*[-\s]?acre", text, re.IGNORECASE)
    if m:
        return int(float(m.group(1)) * 43_560)

    m = re.search(r"half\s*[-\s]?acre", text, re.IGNORECASE)
    if m:
        return 21_780

    m = re.search(r"quarter\s*[-\s]?acre", text, re.IGNORECASE)
    if m:
        return 10_890

    # Explicit lot sqft: "8000 sqft lot"
    m = re.search(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|sf)\s*lot", text, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(",", ""))

    return None


def _detect_style(text: str) -> str:
    """Return the first matching architectural style keyword found."""
    lower = text.lower()
    for keyword, style in _STYLE_KEYWORDS.items():
        if keyword in lower:
            return style
    return "modern"


def _detect_special_requirements(text: str) -> list[str]:
    """Return any special-feature keywords found in the text."""
    lower = text.lower()
    found: list[str] = []
    for feature in _SPECIAL_FEATURES:
        if feature in lower:
            # Normalise to title case
            found.append(feature.replace("-", " ").title())
    return found


def _detect_bool_feature(text: str, keywords: list[str]) -> bool | None:
    """Return True if any keyword is present, False if 'no <keyword>' is
    present, or None if not mentioned.
    """
    lower = text.lower()
    for kw in keywords:
        if re.search(rf"\bno\s+{kw}", lower):
            return False
        if kw in lower:
            return True
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_vibe(vibe_text: str) -> RequirementSpecification:
    """Parse a natural-language vibe description into a structured RSO.

    Parameters
    ----------
    vibe_text:
        Free-form text from the homeowner describing their dream home.

    Returns
    -------
    RequirementSpecification
        A structured, validated specification with sensible defaults for
        anything not explicitly mentioned in the text.
    """
    bedrooms = _extract_number_before(vibe_text, r"bed(?:room)?s?") or 3
    bathrooms_raw = _extract_number_before(vibe_text, r"bath(?:room)?s?")
    bathrooms: float = float(bathrooms_raw) if bathrooms_raw else max(2.0, bedrooms * 0.75)

    # Check for "half bath" to add 0.5
    if re.search(r"half\s*bath", vibe_text, re.IGNORECASE):
        bathrooms += 0.5

    floors_raw = (
        _extract_number_before(vibe_text, r"stor(?:y|ies)")
        or _extract_number_before(vibe_text, r"floor")
        or _extract_number_before(vibe_text, r"level")
    )
    if floors_raw is None:
        # "two-story" pattern
        m = re.search(
            r"(one|two|three|single|double|triple|\d)\s*[-\s]?stor(?:y|ied|ies)",
            vibe_text,
            re.IGNORECASE,
        )
        if m:
            word = m.group(1).lower()
            floors_raw = {
                "single": 1,
                "double": 2,
                "triple": 3,
            }.get(word) or _WORD_TO_NUM.get(word) or int(word)
    floors = floors_raw if floors_raw else 1

    style = _detect_style(vibe_text)
    budget = _extract_budget(vibe_text) or (250_000, 450_000)
    target_sqft = _extract_sqft(vibe_text) or _default_sqft(bedrooms, floors)
    lot_sqft = _extract_lot_sqft(vibe_text) or max(target_sqft * 3, 6_000)
    special = _detect_special_requirements(vibe_text)

    garage_detected = _detect_bool_feature(vibe_text, ["garage"])
    garage = garage_detected if garage_detected is not None else True

    outdoor_detected = _detect_bool_feature(
        vibe_text, ["outdoor", "patio", "deck", "porch", "yard", "garden"]
    )
    outdoor = outdoor_detected if outdoor_detected is not None else True

    return RequirementSpecification(
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        floors=floors,
        style=style,
        budget_range=budget,
        lot_sqft=lot_sqft,
        target_sqft=target_sqft,
        special_requirements=special,
        garage=garage,
        outdoor_space=outdoor,
    )


def _default_sqft(bedrooms: int, floors: int) -> int:
    """Reasonable default square footage when not specified."""
    base = 800 + bedrooms * 350
    return base * floors
