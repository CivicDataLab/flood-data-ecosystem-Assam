"""
Deterministic normalisation helpers. No network, fully unit-testable.
"""
from __future__ import annotations
import re
import datetime as _dt
from typing import Optional
import config


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------
_UNIT_WORD_RE = re.compile(r"\b(crores?|cr|lakhs?|lacs?|thousand)\b\.?", re.I)
_CURRENCY_RE = re.compile(r"(rs\.?|inr|₹)", re.I)
_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _unit_mult(word: str) -> float:
    w = (word or "").lower().strip(" .")
    for key, m in config.UNIT_MULTIPLIERS.items():
        if key and key in w:
            return m
    return 1.0


def parse_amount(raw, unit_hint: str = "") -> dict:
    """Parse one amount cell into rupees with an explicit decision basis.

    Returns {'inr': float|None, 'basis': str, 'flag': str|None}.

    Decision rule (order matters):
      1. raw carries an explicit unit word (Cr/crore/lakh/...) -> the number is a
         COUNT in that unit; multiply. The page default unit is IGNORED so the
         multiplier can't be applied twice.
      2. raw uses comma grouping (e.g. 17,00,000 or Rs.7,15,000/-) -> it is an
         ABSOLUTE rupee figure; strip separators, NO unit multiplier. (Indian and
         western grouping both collapse to the same integer once commas go.)
      3. bare number with >= 6 integer digits and no unit -> almost certainly
         already rupees, not a lakh/crore count; treat as rupees and FLAG for
         source verification.
      4. otherwise (small bare number like 206.10) -> a COUNT in the column's
         unit (unit_hint or the configured default); multiply.
    """
    if raw is None:
        return {"inr": None, "basis": "empty", "flag": None}
    s = str(raw)

    explicit = _UNIT_WORD_RE.search(s)
    # remove currency tokens and unit words BEFORE pulling out the number, so a
    # 'Rs.' period or a 'Cr' can never leak into the numeric token.
    cleaned = _CURRENCY_RE.sub(" ", s)
    cleaned = _UNIT_WORD_RE.sub(" ", cleaned).replace("/-", " ")
    m = _NUM_RE.search(cleaned)
    if not m:
        return {"inr": None, "basis": "no_number", "flag": None}
    num = m.group(0).rstrip(".")
    digits = num.replace(",", "")
    if digits in ("", "."):
        return {"inr": None, "basis": "no_number", "flag": None}
    try:
        value = float(digits)
    except ValueError:
        return {"inr": None, "basis": "no_number", "flag": None}

    int_digits = digits.split(".")[0].lstrip("0") or "0"

    if explicit:
        return {"inr": value * _unit_mult(explicit.group(0)),
                "basis": "explicit_unit", "flag": None}
    if "," in num:
        flag = "small_value_check" if value < 1000 else None
        return {"inr": value, "basis": "comma_grouped_absolute", "flag": flag}
    if len(int_digits) >= 6:
        return {"inr": value, "basis": "bare_long_assumed_rupees",
                "flag": "ambiguous_unit_check_source"}
    return {"inr": value * _unit_mult(unit_hint or config.DEFAULT_UNIT),
            "basis": "count_in_unit", "flag": None}


def to_inr(raw, unit_hint: str = "") -> Optional[float]:
    """Backward-compatible thin wrapper returning just the rupee value."""
    return parse_amount(raw, unit_hint)["inr"]


def to_lakh(raw, unit_hint: str = "") -> Optional[float]:
    """Convenience: rupees expressed back in lakh (for human-readable tables)."""
    inr = to_inr(raw, unit_hint)
    return None if inr is None else inr / 1e5


# ---------------------------------------------------------------------------
# Controlled-vocab snapping
# ---------------------------------------------------------------------------
def _snap(value: str, alias_map: dict) -> Optional[str]:
    if not value:
        return None
    key = re.sub(r"\s+", " ", str(value).strip().lower())
    key = key.strip(" .:-")
    if key in alias_map:
        return alias_map[key]
    # substring / containment match (handles "kamrup (m) district" etc.)
    best = None
    for alias, canon in alias_map.items():
        if alias and alias in key:
            if best is None or len(alias) > len(best[0]):
                best = (alias, canon)
    return best[1] if best else None


def canon_district(value: str) -> Optional[str]:
    return _snap(value, config.DISTRICT_ALIASES)


def canon_department(value: str) -> Optional[str]:
    return _snap(value, config.DEPARTMENT_ALIASES)


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
_MONTHS = ("january february march april may june july august september "
           "october november december").split()
_MON_RE = "|".join(_MONTHS + [m[:3] for m in _MONTHS])

_DATE_PATTERNS = [
    # 28 January 2026 / 2nd April, 2009 / 8" October, 2018 (junk-tolerant)
    re.compile(rf"(\d{{1,2}})\s*(?:st|nd|rd|th)?[^\w]{{0,4}}\s*({_MON_RE})[a-z]*[^\w]{{0,4}}\s*(\d{{4}})",
               re.I),
    # January 28, 2026
    re.compile(rf"({_MON_RE})[a-z]*\s+(\d{{1,2}})\s*(?:st|nd|rd|th)?[^\w]{{0,3}}\s*(\d{{4}})",
               re.I),
    # 06/10/2016 or 06-10-2016
    re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})"),
]


def _clean_ocr(s: str) -> str:
    """Collapse newlines and strip the superscript/ordinal junk OCR leaves
    between a day and its month (e.g. '30™ November', '8\" October')."""
    s = s.replace("\n", " ")
    s = re.sub(r"[\"'`^~™”“’°]+", " ", s)
    return re.sub(r"\s+", " ", s)


def parse_meeting_date(text: str) -> Optional[str]:
    """Best-effort ISO date (YYYY-MM-DD) from minute header text.

    Prefers a date anchored to the title phrase 'held on ...', because minutes
    routinely cite OTHER dates (the previous meeting being confirmed, scheme
    years like '2016-17', action-taken-report periods). Only if no anchored
    date is found does it fall back to the first date anywhere in the text.
    """
    if not text:
        return None
    t = _clean_ocr(text)
    # 1) anchored: look only in the window right after "held on"
    m = re.search(r"held\s+on\s+(.{0,80})", t, re.I)
    if m:
        d = _first_date(m.group(1))
        if d:
            return d
    # 2) fallback: first parseable date anywhere (less reliable)
    return _first_date(t)


def _first_date(t: str) -> Optional[str]:
    for pat in _DATE_PATTERNS:
        m = pat.search(t)
        if not m:
            continue
        g = m.groups()
        try:
            if pat is _DATE_PATTERNS[2]:           # numeric d/m/Y
                d, mo, y = int(g[0]), int(g[1]), int(g[2])
            elif pat is _DATE_PATTERNS[1]:         # Month d, Y
                mo = _month_num(g[0]); d = int(g[1]); y = int(g[2])
            else:                                  # d Month Y
                d = int(g[0]); mo = _month_num(g[1]); y = int(g[2])
            if 2000 <= y <= 2035 and 1 <= mo <= 12 and 1 <= d <= 31:
                return _dt.date(y, mo, d).isoformat()
        except (ValueError, TypeError):
            continue
    return None


# dates embedded in filenames, e.g. 46th_sec_meeting_6_12_2022 or ..._10.12.2022
_FNAME_DATE = re.compile(r"(\d{1,2})[._\-](\d{1,2})[._\-](20\d{2})")


def date_from_filename(name: str) -> Optional[str]:
    m = _FNAME_DATE.search(name)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return _dt.date(y, mo, d).isoformat()
    except ValueError:
        return None


def _month_num(s: str) -> int:
    s = s.lower()[:3]
    for i, m in enumerate(_MONTHS, start=1):
        if m.startswith(s):
            return i
    raise ValueError(s)


def fiscal_year(iso_date: str) -> Optional[str]:
    """Indian FY label, e.g. 2016-04..2017-03 -> '2016-17'."""
    if not iso_date:
        return None
    try:
        d = _dt.date.fromisoformat(iso_date)
    except ValueError:
        return None
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{str(start + 1)[-2:]}"
