"""Where tags are kept: the output folder's ``tags.jsonl`` and ``scheme.json``.

Records are appended a batch at a time and flushed, so stopping at any point loses at most
the batches in flight. See docs/formats.md.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from topic_tagger.scheme import Scheme
from topic_tagger.variables import Variable


def make_record(
    var: Variable, topics: list[tuple[str, float]], scheme_hash: str, model: str, now: float
) -> dict:
    """One line of ``tags.jsonl``.

    Args:
        var: The variable.
        topics: Its tags, strongest first.
        scheme_hash: The hash of the scheme the tags were made with.
        model: ``provider:model``, or ``rule``.
        now: The time, in seconds since the epoch.
    """
    return {
        "file": var.file,
        "variable": var.variable,
        "topics": [[t, c] for t, c in topics],
        "scheme": scheme_hash,
        "model": model,
        "tagged": datetime.fromtimestamp(now, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


class TagStore:
    """The output folder.

    Args:
        folder: The folder; created if needed.
    """

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / "tags.jsonl"

    def write_scheme(self, scheme: Scheme) -> None:
        """Write the scheme the tags are made with to ``scheme.json``."""
        text = json.dumps(scheme.to_json(), ensure_ascii=False, indent=1)
        (self.folder / "scheme.json").write_text(text + "\n", encoding="utf-8")

    def append(self, records: list[dict]) -> None:
        """Append records to ``tags.jsonl`` and flush them to disk."""
        with self.path.open("a", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
