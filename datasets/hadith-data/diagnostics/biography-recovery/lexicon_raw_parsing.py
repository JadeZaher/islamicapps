"""Pure parsers for the free-text cells of all_rawis.csv (see README.md in this directory).

Nothing here decides a date: each parser returns what the cell literally says, with
qualifiers and ranges preserved, plus flags for anything it had to infer.
Years in the BH era are stored negative (53 BH -> -53); the hijri/gregorian split is
by era token, with a magnitude-based inference flagged when the token is missing.
"""

import re

ERA_TOKEN = re.compile(r"(\d+)\s*(AH|BH|CE)?", re.I)
AFTER = re.compile(r"(\bafter\b|\blater\b|>)", re.I)
BEFORE = re.compile(r"(\bbefore\b|<)", re.I)
MONTH_DAY_GROUP = re.compile(
    r"^\d+(st|nd|rd|th)\b|muharram|safar|rabi|jumada|rajab|sha.?ban|ramadan|shawwal|dhu|dhul|^\d+\s*[a-z]+$",
    re.I,
)
ESTIMATE_GROUP = re.compile(r"\.?\s*(est|approx|approximately|about)\.?", re.I)
REASON_TAIL = re.compile(r"\[\s*([^\]]*?)\s*\]\s*$")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_cell(cell: str):
    """Split a raw `date (place) [ reason ]` cell into date text, paren groups, reason."""
    text = normalize_space(cell)
    reason = None
    match = REASON_TAIL.search(text)
    if match:
        reason = match.group(1)
        text = text[: match.start()].strip()
    first_paren = text.find("(")
    date_text = text if first_paren < 0 else text[:first_paren].strip()
    groups, depth, start = [], 0, None
    for index, char in enumerate(text):
        if char == "(":
            if depth == 0:
                start = index + 1
            depth += 1
        elif char == ")" and depth:
            depth -= 1
            if depth == 0:
                groups.append(text[start:index].strip())
    if depth and start is not None:  # unbalanced "(Dhul Hijja (Madinah)" style cell
        groups.append(text[start:].strip())
    return date_text, groups, reason


def parse_year_expression(date_text: str) -> dict:
    """Parse `~12 AH/633 CE`, `42-55 AH/662-74 CE`, `63 AH or after` ... into per-calendar spans."""
    flags = []
    text = normalize_space(date_text)
    if not re.search(r"\d", text):
        return {"present": False, "verbatim": text, "calendars": {}, "qualifiers": [], "flags": []}
    qualifiers = []
    if "~" in text:
        qualifiers.append("circa")
    has_after, has_before = bool(AFTER.search(text)), bool(BEFORE.search(text))
    if has_after and has_before:
        qualifiers.append("unresolved_after_and_before")
        flags.append("qualifier_unresolved")
    elif has_after:
        qualifiers.append("after")
    elif has_before:
        qualifiers.append("before")

    tokens = [(m.start(), m.end(), int(m.group(1)), (m.group(2) or "").upper() or None)
              for m in ERA_TOKEN.finditer(text)]
    explicit_hijri = [v for _, _, v, era in tokens if era in ("AH", "BH")]
    reference = min(explicit_hijri) if explicit_hijri else None
    resolved = []  # (value, era, separator_before, inferred)
    previous_end = 0
    for start, end, value, era in tokens:
        separator = text[previous_end:start]
        previous_end = end
        inferred = False
        if era is None:
            if reference is not None:
                era, inferred = ("CE" if value > reference + 500 else "AH"), True
            elif len(tokens) > 1 and max(v for _, _, v, _ in tokens) - min(v for _, _, v, _ in tokens) > 400:
                era, inferred = ("CE" if value > 580 + min(v for _, _, v, _ in tokens) else "AH"), True
            if inferred:
                flags.append("era_inferred_by_magnitude")
        resolved.append([value, era, separator, inferred])

    by_calendar = {}
    for value, era, separator, _ in resolved:
        by_calendar.setdefault(era, []).append((value, separator))
    calendars = {}
    for era, entries in by_calendar.items():
        values = [v for v, _ in entries]
        relation = "single"
        if len(entries) > 1:
            joined = " ".join(sep for _, sep in entries[1:])
            relation = "range" if "-" in joined and "or" not in joined else "alternatives"
            if relation == "range" and len(values) == 2 and values[1] < values[0]:
                tail = str(values[1])
                values[1] = int(str(values[0])[: len(str(values[0])) - len(tail)] + tail)
                flags.append("range_end_expanded_from_abbreviation")
        signed = [-v if era == "BH" else v for v in values]
        calendar = "gregorian" if era == "CE" else "hijri" if era in ("AH", "BH") else "unspecified"
        low, high = min(signed), max(signed)
        if "after" in qualifiers:
            high = None
        elif "before" in qualifiers:
            low = None
        elif "unresolved_after_and_before" in qualifiers:
            low = high = None
        calendars[era or "NONE"] = {
            "calendar": calendar,
            "era": era,
            "relation": relation,
            "values_as_written": values,
            "year_min": low,
            "year_max": high,
        }
        if era is None:
            flags.append("no_calendar_stated")
    return {"present": True, "verbatim": text, "calendars": calendars, "qualifiers": qualifiers,
            "flags": sorted(set(flags))}


def parse_place_cell(cell: str) -> dict:
    """Full parse of a birth_date_place / death_date_place cell."""
    verbatim = cell
    date_text, groups, reason = split_cell(cell)
    dates = parse_year_expression(date_text)
    places, day_month = [], []
    for group in groups:
        if not group:
            continue
        if ESTIMATE_GROUP.fullmatch(group):
            if "estimated" not in dates["qualifiers"]:
                dates["qualifiers"].append("estimated")
            continue
        (day_month if MONTH_DAY_GROUP.search(group) else places).append(group)
    return {"verbatim": verbatim, "date": dates, "places": places, "day_month_notes": day_month,
            "reason_text": reason}


GENERATION = re.compile(r"\[\s*(\d+)(?:st|nd|rd|th)\s+generation\s*\]", re.I)
CENTURY = re.compile(r"^(\d+)(?:st|nd|rd|th)\s+Century AH", re.I)
BRACKET = re.compile(r"\[([^\]]*)\]")
CATEGORY_PREFIXES = (
    ("Comp.(RA)", "companion"),
    ("Follower(Tabi')", "follower"),
    ("Succ. (Taba' Tabi')", "successor_of_followers"),
    ("Prophet's Relative", "prophets_relative"),
    ("Rasool Allah", "prophet"),
)


def parse_generation_cell(cell: str) -> dict:
    """Parse the lexicon `grade` cell: a generation marker, not a verdict."""
    text = normalize_space(cell)
    category, century = None, None
    for prefix, label in CATEGORY_PREFIXES:
        if text.startswith(prefix):
            category = label
    century_match = CENTURY.match(text)
    if century_match:
        category, century = "century_marker", int(century_match.group(1))
    generation_match = GENERATION.search(text)
    generation = int(generation_match.group(1)) if generation_match else None
    other = [b.strip() for b in BRACKET.findall(text) if not GENERATION.fullmatch(f"[{b}]")]
    return {"verbatim": cell, "category": category, "century_ah": century,
            "generation_number": generation, "other_bracket_labels": other}


GRADE_CELL = re.compile(r"^(?P<area>[^\[]*?)\s*(?:\[Grade:(?P<label>[^\]]*)\])?\s*(?:\[(?P<tail>[^\]]*)\])?\s*$")


def parse_area_of_interest(cell: str) -> dict:
    """Split `Narrator[Grade:Thiqah] [ ع  -  ثقة ]` into area, English label, symbols, Arabic term."""
    text = normalize_space(cell)
    match = GRADE_CELL.match(text)
    if not match:
        return {"verbatim": cell, "parsed": False}
    tail = normalize_space(match.group("tail") or "")
    symbols, term_ar = None, None
    split = re.match(r"^(.*?)\s*-\s*(.*)$", tail)
    if split:
        symbols, term_ar = split.group(1).strip() or None, split.group(2).strip() or None
    elif tail:
        term_ar = tail
    return {"verbatim": cell, "parsed": True, "area": normalize_space(match.group("area")),
            "english_grade_label": match.group("label"), "symbols_ar": symbols, "term_ar": term_ar}
