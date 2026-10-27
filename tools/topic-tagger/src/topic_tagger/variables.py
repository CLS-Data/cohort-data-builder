"""Reading the variables to tag from ``variables.jsonl``.

One JSON object per line: ``file`` and ``variable`` (required), and optionally ``label`` and
``values`` (``[value, label]`` pairs). Any other fields are kept as given, for grouping the
statistics, and are never sent to the model. See docs/formats.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KNOWN = ("file", "variable", "label", "values")


class InputError(Exception):
    """The variables file cannot be used; the message lists every problem found."""


@dataclass(frozen=True)
class Variable:
    """One variable to tag.

    Attributes:
        file: The data file it belongs to.
        variable: Its name.
        label: Its label, or None.
        values: Its value labels as ``(value, label)`` pairs.
        extra: Any other fields from its input line, as given.
    """

    file: str
    variable: str
    label: str | None = None
    values: tuple[tuple[str, str], ...] = ()
    extra: dict[str, Any] = field(default_factory=dict, hash=False)

    @property
    def key(self) -> str:
        """The variable's key, ``file/variable``."""
        return f"{self.file}/{self.variable}"


def read_variables(path: Path) -> list[Variable]:
    """Read and check a variables file.

    Args:
        path: The ``variables.jsonl`` file.

    Returns:
        The variables, in file order.

    Raises:
        InputError: If the file is missing, a line is not a valid variable, or a key
            (``file/variable``, ignoring case) appears more than once. Every problem is
            listed, not only the first.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise InputError(f"cannot read {path}: {e.strerror}") from e

    rows: list[Variable] = []
    problems: list[str] = []
    seen: dict[str, list[int]] = {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = _parse(line)
        except ValueError as e:
            problems.append(f"line {n}: {e}")
            continue
        rows.append(row)
        seen.setdefault(row.key.lower(), []).append(n)

    for key, lines in seen.items():
        if len(lines) > 1:
            problems.append(f"{key} appears more than once: lines {', '.join(map(str, lines))}")
    if problems:
        raise InputError(f"{path}:\n  " + "\n  ".join(problems))
    return rows


def _parse(line: str) -> Variable:
    try:
        data = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON ({e.msg})") from e
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    for name in ("file", "variable"):
        if not isinstance(data.get(name), str) or not data[name]:
            raise ValueError(f"'{name}' is missing or empty")
    values = data.get("values") or []
    if not all(isinstance(v, list) and len(v) == 2 for v in values):
        raise ValueError("'values' must be a list of [value, label] pairs")
    return Variable(
        file=data["file"],
        variable=data["variable"],
        label=data.get("label") or None,
        values=tuple((str(v), str(lab)) for v, lab in values),
        extra={k: v for k, v in data.items() if k not in KNOWN},
    )
