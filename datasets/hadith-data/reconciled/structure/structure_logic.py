"""Pure parsing and numbering rules for the structure sidecars (see README.md). No I/O, standard library only."""

import re
from collections import Counter
from decimal import Decimal, InvalidOperation

ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# ---------------------------------------------------------------------------------------------------------------------
# Numbers as the sources write them
# ---------------------------------------------------------------------------------------------------------------------

_INT = re.compile(r"^\d+$")
_BRACKET = re.compile(r"^(\d+)\]$")
_SERIES = re.compile(r"^(\d+)×(\d+)$")
_SUB = re.compile(r"^(\d+)\.(\d+)$")
_LETTER = re.compile(r"^(\d+)([a-z])$")
_RANGE = re.compile(r"^(\d+)\s*-\s*(\d+)$")


def parse_number(raw):
    """A source's hadith-number cell -> {raw, value, sub, series, letter, flags}.

    `value` is the leading integer only when the cell really is that number; a cell that is a marker, a grade word or
    empty gets value None. Flags name every irregularity so a loader can refuse or show them.
    `1]` is the Musnad Ahmad section-opener row: it is NOT hadith 1 (the next row is), so value stays None.
    """
    text = (raw if raw is not None else "").translate(ARABIC_INDIC).strip()
    out = {"raw": raw, "value": None, "sub": None, "series": None, "letter": None, "flags": []}
    if text == "":
        out["flags"].append("empty")
    elif _INT.match(text):
        out["value"] = int(text)
        if out["value"] == 0:
            out["value"] = None
            out["flags"].append("zero_means_unnumbered")
    elif _BRACKET.match(text):
        out["flags"] += ["trailing_bracket", "section_opener_marker_not_a_number"]
    elif _SERIES.match(text):
        value, series = _SERIES.match(text).groups()
        out["value"], out["series"] = int(value), int(series)
        out["flags"].append("second_numbering_series")
    elif _SUB.match(text):
        value, fraction = _SUB.match(text).groups()
        if len(fraction) > 6:  # spreadsheet float noise such as 8.1999999999999993 (really 8.2)
            fraction = format(Decimal(text).quantize(Decimal("0.000001")).normalize(), "f").partition(".")[2]
            out["flags"].append("float_noise_cleaned")
        out["value"], out["sub"] = int(value), fraction
        out["flags"].append("decimal_sub_number")
    elif _LETTER.match(text):
        value, letter = _LETTER.match(text).groups()
        out["value"], out["letter"] = int(value), letter
        out["flags"].append("letter_suffix")
    elif _RANGE.match(text):
        out["value"] = int(_RANGE.match(text).group(1))
        out["flags"].append("range_uses_first")
    else:
        try:  # spreadsheet float noise such as 8.1999999999999993
            decimal = Decimal(text).quantize(Decimal("0.000001")).normalize()
            whole, _, fraction = format(decimal, "f").partition(".")
            if whole.isdigit() and fraction:
                out["value"], out["sub"] = int(whole), fraction
                out["flags"].append("decimal_sub_number")
                out["flags"].append("float_noise_cleaned")
            else:
                out["flags"].append("unparseable")
        except InvalidOperation:
            out["flags"].append("non_numeric_text")
    return out


def display_number(parsed):
    """Printed form of a parsed number (`8.2`, `1×2`, `3604b`), or None."""
    if parsed["value"] is None:
        return None
    text = str(parsed["value"])
    if parsed["sub"]:
        text += "." + parsed["sub"]
    if parsed["letter"]:
        text += parsed["letter"]
    if parsed["series"]:
        text += f"×{parsed['series']}"
    return text


_LEAD_AR = re.compile(r"^[\s‏‎]*(\d{1,5})\s*[\-ـ\.\):،]")
_LEAD_EN = re.compile(r"^\s*(\d{1,5})\s*[\.\-\):]")


def printed_lead_number(text, language):
    """The number a provider text opens with (`1ـ أخبرنا`, `1. Abu Ja'far`), or None. `language` is 'ar' or 'en'."""
    pattern = _LEAD_AR if language == "ar" else _LEAD_EN
    match = pattern.match((text or "").translate(ARABIC_INDIC))
    return int(match.group(1)) if match else None


_THAQALAYN_PATH = re.compile(r"/hadith/(\d+)/(\d+)/(\d+)/(\d+)/?$")


def parse_thaqalayn_url(url):
    """Thaqalayn's `/hadith/<file>/<category>/<chapter-in-category>/<hadith>` -> ints, or None."""
    match = _THAQALAYN_PATH.search(url or "")
    return tuple(int(part) for part in match.groups()) if match else None


_PAGE = re.compile(r"^V0*(\d+)P0*(\d+)$")


def parse_page_ref(ref):
    """OpenITI `V01P059` -> (1, 59); anything else -> None."""
    match = _PAGE.match((ref or "").strip())
    return (int(match.group(1)), int(match.group(2))) if match else None


_ARABIC_LETTER = re.compile(r"[؀-ۿ]")


def split_kitab_title(label):
    """K6 kitab labels read `English - عربي`. Returns (english, arabic); either may be None; the raw label is kept by caller."""
    text = (label or "").strip()
    if " - " in text:
        english, arabic = text.rsplit(" - ", 1)
        if _ARABIC_LETTER.search(arabic) and not _ARABIC_LETTER.search(english):
            return english.strip() or None, arabic.strip() or None
    if _ARABIC_LETTER.search(text):
        return (None, text) if not re.search(r"[A-Za-z]", text) else (None, text)
    return text or None, None


def natural_key(text):
    """Sort key where digit runs compare as numbers (`rabi_0001b` after `rabi_0001`, before `rabi_0002`)."""
    return [(0, int(part), "") if part.isdigit() else (1, 0, part) for part in re.split(r"(\d+)", text or "") if part != ""]


def assign_source_order(keys):
    """Dense 1-based ranks for a list of sortable keys (ties broken by input position, so the result is deterministic)."""
    ranked = sorted(range(len(keys)), key=lambda index: (keys[index], index))
    order = [0] * len(keys)
    for rank, index in enumerate(ranked, start=1):
        order[index] = rank
    return order


# ---------------------------------------------------------------------------------------------------------------------
# Musnad Ahmad: sections recovered from number restarts
# ---------------------------------------------------------------------------------------------------------------------

def ahmad_section_ordinals(parsed_numbers):
    """Section ordinal per row (rows in shelf order). A new section starts at an opener `1]` or wherever the main number
    falls below the previous one (numbers only ascend inside a section; the first rows of a section may be missing from
    the corpus, so the restart is not always at 1). A section is derived from the numbering, not a heading the source
    gives. Second-series numbers (`1×2`) and sub-numbers (`8.1`) never start or end a section by themselves."""
    ordinals, section, previous = [], 0, None
    for parsed in parsed_numbers:
        opener = "trailing_bracket" in parsed["flags"]
        value = parsed["value"] if parsed["series"] is None else None
        if section == 0 or opener or (value is not None and previous is not None and value < previous):
            section += 1
            previous = None
        ordinals.append(section)
        if value is not None:
            previous = value
    return ordinals


# ---------------------------------------------------------------------------------------------------------------------
# Uniqueness measurement
# ---------------------------------------------------------------------------------------------------------------------

def unique_rows(keys):
    """(rows with a key, rows whose key occurs exactly once, distinct keys that repeat). Keys of None are ignored."""
    counts = Counter(key for key in keys if key is not None)
    covered = sum(counts.values())
    unique = sum(1 for count in counts.values() if count == 1)
    repeated = sum(1 for count in counts.values() if count > 1)
    return covered, unique, repeated


def rows_in_unique_groups(keys):
    """For each key, True when it occurs exactly once (None -> False)."""
    counts = Counter(key for key in keys if key is not None)
    return [key is not None and counts[key] == 1 for key in keys]


# ---------------------------------------------------------------------------------------------------------------------
# What the live site cites today (port of src/lib/citation/reference.ts, for the "before" column)
# ---------------------------------------------------------------------------------------------------------------------

def _positive(value):
    text = (value or "").strip()
    return str(int(text)) if re.fullmatch(r"\d+", text) and int(text) > 0 else None


def site_reference_today(hadith_id, hadith_no, url, volume, page_ref, book_number):
    """The string `reportReference` returns for these stored fields. Two reports with the same string are not told apart."""
    namespace = hadith_id.split(":")[1] if hadith_id.count(":") >= 2 else "other"
    number = _positive(hadith_no)
    record_key = ":".join(hadith_id.split(":")[2:])
    if namespace == "thaqalayn":
        path = parse_thaqalayn_url(url)
        number = str(path[3]) if path else None
        volume_number = volume or book_number
        prefix = f"Volume {volume_number}, " if volume_number else ""
        return (f"{prefix}Book {path[1]}, Chapter {path[2]}, Hadith {path[3]}" if path else f"{prefix}record {record_key}")
    if namespace == "k6":
        book = f"Book {book_number}, " if book_number else ""
        return f"{book}Hadith {number}" if number else f"{book}unnumbered (record {record_key})"
    if namespace == "openiti":
        page = parse_page_ref(page_ref)
        label = f"vol. {page[0]}, p. {page[1]}" if page else (page_ref or "").strip() or None
        base = f"No. {number}" if number else f"Record {record_key}"
        return f"{base} ({label})" if label else base
    return f"No. {number}" if number else f"Record {record_key} (no number in this copy)"
