"""Where tags are kept: the output folder's ``tags.jsonl`` and ``scheme.json``.

Records are appended a batch at a time and flushed, so stopping at any point loses at most
the batches in flight; a line cut off by a crash is ignored on load. A variable may appear
more than once while a run is going; the last line wins, and ``compact`` rewrites the file
with one sorted line per variable when the run ends. ``.lock`` holds the process id of the
run in progress. See docs/formats.md.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from topic_tagger.scheme import Scheme
from topic_tagger.variables import Variable


class LockedError(Exception):
    """Another run is using the output folder."""


class StaleLockError(Exception):
    """A run that has ended left its lock behind."""


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
        self.lock_path = self.folder / ".lock"
        self.records: dict[str, dict] = {}

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

    def load(self) -> None:
        """Read existing records; for a variable recorded twice, the last line wins."""
        self.records = {}
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue  # cut off by a crash; that variable is simply tagged again
                self.records[_key(r["file"], r["variable"])] = r

    def state(self, key: str, scheme_hash: str) -> str:
        """``missing``, ``stale`` (made with another scheme) or ``current``."""
        r = self.records.get(key.lower())
        if r is None:
            return "missing"
        return "current" if r["scheme"] == scheme_hash else "stale"

    def compact(self) -> None:
        """Rewrite ``tags.jsonl`` with one line per variable, sorted by file and variable.

        Written to a temporary file and renamed, so the file is never half-written.
        """
        self.load()
        tmp = self.path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for r in sorted(self.records.values(), key=lambda r: (r["file"], r["variable"])):
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, self.path)

    def lock(self, force: bool = False) -> None:
        """Mark the folder as in use by this process.

        Raises:
            LockedError: Another live process holds the lock.
            StaleLockError: The process that took the lock has ended; pass ``force`` to
                take it anyway.
        """
        if self.lock_path.exists():
            try:
                pid = int(self.lock_path.read_text().strip())
            except ValueError:
                pid = -1
            if _alive(pid):
                raise LockedError(f"another run (process {pid}) is using {self.folder}")
            if not force:
                raise StaleLockError(
                    f"{self.lock_path} was left by a run that has ended (process {pid}); "
                    "run again with --force to clear it"
                )
        self.lock_path.write_text(f"{os.getpid()}\n")

    def unlock(self) -> None:
        """Release the lock."""
        self.lock_path.unlink(missing_ok=True)


def _key(file: str, variable: str) -> str:
    return f"{file}/{variable}".lower()


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform == "win32":
        # os.kill would terminate the process on Windows, so a lock always counts as live
        # there and the maintainer clears it with --force.
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # it exists but belongs to someone else
    return True
