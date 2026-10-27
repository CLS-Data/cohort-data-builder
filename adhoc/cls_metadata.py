"""Parsing the CLS studies metadata CSV: text, value labels, missing codes and sweeps.

Shared by ``stage.py`` and ``build.py``. Standard library only.
"""

from __future__ import annotations

import re

# The CSV stores some cp1252 characters as C1 control characters (e.g. U+0092 for ’).
_C1 = {c: bytes([c]).decode("cp1252", errors="replace") for c in range(0x80, 0xA0)}

# "(CODE   ) Label" pairs, separated by two or more spaces. A label may itself hold
# "(…)" after a single space, e.g. "No (not now)".
_PAIR = re.compile(r"\(([^()]*)\)\s*(.*?)(?=\s{2,}\([^()]*\)|\s*$)", re.S)
_CUT = "... AND MORE"  # how the CSV ends a list cut off at 2,000 characters
_DROPPED_CODES = {"", "sysmiss"}

# Labels of negative codes that mean "missing" in CLS data. A negative code whose label
# matches none of these is treated as a real answer and kept (e.g. "Armed Services").
_MISSING = re.compile(
    r"not applicable|not appl|n/a|^na$|does not apply|don'?t know|dont know|do not know"
    r"|not known|refus|don'?t want|not stated|not answered|unanswered|no answer|not asked"
    r"|missing|no information|insufficient|not specified|not interviewed|no questionnaire"
    r"|script|routing|undecipherable|illegible|blank|no response|ns/|not carried out"
    r"|not attempted|not recorded|out of range|vague|multicode|more than 1|interpreter"
    r"|not done|not received|not measured|inappropriate|cannot be|can'?t be|rejected"
    r"|not present|no parent|no sp|no tests|lost|error|unclassifiable|not available"
    r"|not given|no data|not coded|no reply|not in|unknown|not app|non.?response|unable to"
    r"|not codeable|no measurement|no test|not entered|do not wish|no idea|invalid"
    r"|more than one|not required|not issued|declined|not completed|not computed"
    r"|not enough|not collected|no .*collected|void|not yet|not published|no entries"
    r"|no interview|not main|dead|died|counted elsewhere|no \d+ ?yr|not possible"
    r"|\bna\b|\bdna\b|\bd/?k\b|multi.?cod|inconsistent|conflicting|no capi|misrouted"
    r"|not on route|not taken|incomplete|didn'?t complete|did not complete|not codable"
    r"|uncodeable|imformation|equipment|not calculated|not converted|\d\+ answers|no blood",
)


def fix_text(text: str) -> str:
    """Replace C1 control characters with the cp1252 characters they stand for."""
    return text.translate(_C1)


def _is_number(code: str) -> bool:
    try:
        float(code)
    except ValueError:
        return False
    return True


def parse_value_labels(text: str, *, numeric: bool) -> tuple[list[list[str]], bool]:
    """Split the CSV's value-label text into ``[code, label]`` pairs.

    System-missing and blank codes are dropped, and so are text codes on a numeric
    variable. A list the CSV cut off loses its last, incomplete label.

    Args:
        text: The ``value_labels_to_2000_chars`` cell.
        numeric: Whether the variable is numeric.

    Returns:
        The pairs, and whether the list was cut off.
    """
    cut = text.rstrip().endswith(_CUT)
    if cut:
        text = text.rstrip()[: -len(_CUT)]
    pairs = [[c.strip(), " ".join(label.split())] for c, label in _PAIR.findall(text)]
    if cut and pairs:
        pairs.pop()
    keep = [
        p for p in pairs if p[0].lower() not in _DROPPED_CODES and (not numeric or _is_number(p[0]))
    ]
    return keep, cut


def _number(code: str) -> int | float:
    x = float(code)
    return int(x) if x.is_integer() else x


def derive_na(values: list[list[str]]) -> dict | None:
    """Work out missing codes from value labels, following the CLS convention.

    Negative codes are missing values when their label reads as missing; other negative
    codes are real answers and go in ``kept``.

    Args:
        values: ``[code, label]`` pairs.

    Returns:
        An ``na`` object in the site's format, or None if there are no negative codes.
    """
    missing, kept = [], []
    for code, label in values:
        if not _is_number(code) or float(code) >= 0:
            continue
        if _MISSING.search(label.lower().replace("’", "'").replace("''", "'")):
            missing.append(_number(code))
        else:
            kept.append([_number(code), label])
    if not missing and not kept:
        return None
    na = {"values": missing, "ranges": []}
    if kept:
        na["kept"] = kept
    return na


def sweep_key(sweep: str) -> str:
    """The site's key for a CSV ``sweep`` number: ``s6_1`` for 6.1, ``xwave`` for -1."""
    x = float(sweep)
    if x < 0:
        return "xwave"
    return "s" + (str(int(x)) if x.is_integer() else str(x).replace(".", "_"))


_SWEEP = re.compile(r"Sweep\s*([\d.]+)\s*-\s*(\S+)\s*-\s*(.+?)\s*$")


def sweep_label(text: str) -> str:
    """A readable label for a CSV ``sweep-year-age`` value.

    ``Sweep6.1 - 2002/04 - 44/45 years old`` becomes ``Sweep 6.1: age 44/45, 2002/04``.
    Text in any other form is returned as it is, except ``cross-sweep``.
    """
    if text.strip().lower() == "cross-sweep":
        return "Cross-sweep"
    m = _SWEEP.fullmatch(text.strip())
    if not m:
        return text
    number, year, age = m.groups()
    age = re.sub(r"\s*years old$", "", age)
    age = re.sub(r"\s*old$", "", age)
    when = age if age == "birth" else f"age {age}"
    return f"Sweep {number}: {when}, {year}"
