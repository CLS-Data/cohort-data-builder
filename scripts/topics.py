"""Connect the Topic Tagger to the site's data: export a cohort for tagging, merge tags back.

The tagger (``tools/topic-tagger``) knows nothing about the site. This script converts
between the two, relying only on the tagger's documented file formats:

    uv run python scripts/topics.py export site/data/<key> --out variables.jsonl
    uv run python scripts/topics.py merge  site/data/<key> --tags DIR

``export`` writes every variable of a cohort, except its identifier, as the tagger's input.
``merge`` writes the tagger's scheme and tags into the cohort's manifest, dictionaries and
index, gives the identifier its fixed topic, and runs the site's data checks. Standard
library only. Exit codes: 0 done, 1 merged but the checks found problems, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from checks import check_data

OK, CHECKS_FAILED, BAD_INPUT = 0, 1, 2


class TopicsError(Exception):
    """The cohort or the tags cannot be used; nothing has been written."""


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise TopicsError(f"cannot read {path}: {e.strerror}") from e
    except json.JSONDecodeError as e:
        raise TopicsError(f"{path} is not valid JSON: {e}") from e


def _write(path: Path, data) -> None:
    """Write JSON as the site's files are (compact, UTF-8), replacing the file at once."""
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


@dataclass
class _Cohort:
    """A cohort's site data, loaded."""

    folder: Path
    manifest: dict
    index: list
    dicts: dict[str, dict]  # file name -> dictionary

    @classmethod
    def load(cls, folder: Path) -> _Cohort:
        if not (folder / "manifest.json").exists():
            raise TopicsError(f"{folder} has no manifest.json: is it a cohort folder?")
        manifest = _read(folder / "manifest.json")
        dicts = {f["name"]: _read(folder / "dict" / f"{f['name']}.json") for f in manifest["files"]}
        return cls(folder, manifest, _read(folder / "index.json"), dicts)

    def is_identifier(self, name: str) -> bool:
        return name.lower() == self.manifest["identifier"].lower()


def export(cohort_dir: Path, out: Path) -> int:
    """Write a cohort's variables in the tagger's input format.

    One line per index row, in index order, leaving out the cohort's identifier (the merge
    tags it). Each line has ``file``, ``variable``, ``label``, ``values`` and ``sweep``.

    Args:
        cohort_dir: The cohort's folder in the site data, e.g. ``site/data/bcs70``.
        out: The ``variables.jsonl`` to write.

    Returns:
        The number of variables written.

    Raises:
        TopicsError: If the cohort cannot be read.
    """
    c = _Cohort.load(Path(cohort_dir))
    files = c.manifest["files"]
    by_key = {(name, v["variable"]): v for name, d in c.dicts.items() for v in d["variables"]}
    lines = []
    for row in c.index:
        file = files[row[2]]
        if c.is_identifier(row[0]):
            continue
        v = by_key.get((file["name"], row[0]), {})
        values = [[str(x["value"]), str(x["label"])] for x in v.get("values") or []]
        line = {
            "file": file["name"],
            "variable": row[0],
            "label": v.get("label", row[1]),
            "values": values,
            "sweep": c.dicts[file["name"]].get("wave", file["wave"]),
        }
        lines.append(json.dumps(line, ensure_ascii=False))
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


@dataclass
class Merged:
    """What a merge found besides the tags it wrote.

    Attributes:
        unknown: ``file/variable`` of records for variables not in the cohort.
        untagged: Variables, other than the identifier, with no current record.
        stale: Records skipped because they were made with another scheme.
        problems: What the site's data checks found after the merge.
    """

    unknown: list[str] = field(default_factory=list)
    untagged: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    problems: list = field(default_factory=list)


def _records(path: Path) -> dict[tuple[str, str], dict]:
    """The tagger's records, keyed by (file, variable) ignoring case; the last line wins."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise TopicsError(f"cannot read {path}: {e.strerror}") from e
    out = {}
    for line in text.splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue  # a line cut off when a run was killed
        out[(r["file"].lower(), r["variable"].lower())] = r
    return out


def merge(cohort_dir: Path, tags_dir: Path, identifier_topic: str = "identifiers") -> Merged:
    """Merge the tagger's scheme and tags into a cohort's site data.

    Writes the scheme into the manifest's ``topics``, each tagged variable's ``topics`` as
    ``[[id, confidence], ...]`` and each index row's topics as ``[number, percent, ...]``,
    strongest first. The identifier gets ``[[identifier_topic, 1.0]]`` in every file that
    has it. Untagged variables are left without topics. Then runs the site's data checks.

    Args:
        cohort_dir: The cohort's folder in the site data.
        tags_dir: The folder the tagger wrote (``scheme.json`` and ``tags.jsonl``).
        identifier_topic: The topic for the identifier; must be in the scheme.

    Returns:
        What was found besides the tags.

    Raises:
        TopicsError: On bad input, before anything is written.
    """
    cohort_dir, tags_dir = Path(cohort_dir), Path(tags_dir)
    c = _Cohort.load(cohort_dir)
    scheme = _read(tags_dir / "scheme.json")
    records = _records(tags_dir / "tags.jsonl")
    number = {t["id"]: i for i, t in enumerate(t for d in scheme["domains"] for t in d["topics"])}
    if identifier_topic not in number:
        raise TopicsError(
            f"the identifier topic '{identifier_topic}' is not in {tags_dir / 'scheme.json'}; "
            "choose one with --identifier-topic"
        )

    result = Merged()
    current = {}
    for key, r in records.items():
        if r.get("scheme") == scheme["hash"]:
            current[key] = r
        else:
            result.stale.append(f"{r['file']}/{r['variable']}")

    def ordered(topics: list) -> list:
        # Strongest first, ties in scheme order.
        return sorted(([t, c] for t, c in topics), key=lambda x: (-x[1], number[x[0]]))

    tags: dict[tuple[str, str], list] = {}
    for name, d in c.dicts.items():
        for v in d["variables"]:
            key = (name.lower(), v["variable"].lower())
            v.pop("topics", None)
            if c.is_identifier(v["variable"]):
                tags[key] = [[identifier_topic, 1.0]]
            elif key in current:
                tags[key] = ordered(current.pop(key)["topics"])
            else:
                continue
            v["topics"] = tags[key]
    result.unknown = [f"{r['file']}/{r['variable']}" for r in current.values()]

    files = c.manifest["files"]
    for i, row in enumerate(c.index):
        key = (files[row[2]]["name"].lower(), row[0].lower())
        row = row[:5]
        if key in tags:
            row.append([x for t, conf in tags[key] for x in (number[t], round(conf * 100))])
        elif not c.is_identifier(row[0]):
            result.untagged.append(f"{files[row[2]]['name']}/{row[0]}")
        c.index[i] = row

    c.manifest["topics"] = {
        "name": scheme["name"],
        "version": scheme["version"],
        "hash": scheme["hash"],
        "domains": [
            {
                "id": d["id"],
                "label": d["label"],
                "description": d["description"],
                "topics": [
                    {"id": t["id"], "label": t["label"], "description": t["description"]}
                    for t in d["topics"]
                ],
            }
            for d in scheme["domains"]
        ],
    }

    _write(cohort_dir / "manifest.json", c.manifest)
    _write(cohort_dir / "index.json", c.index)
    for name, d in c.dicts.items():
        _write(cohort_dir / "dict" / f"{name}.json", d)
    result.problems = check_data(cohort_dir.parent)
    return result


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _listed(title: str, items: list[str]) -> None:
    if items:
        shown = "\n  ".join(items[:20]) + (
            f"\n  … and {len(items) - 20} more" if len(items) > 20 else ""
        )
        _err(f"{title} ({len(items)}):\n  {shown}")


def main(argv: list[str] | None = None) -> int:
    """Run the command line.

    Args:
        argv: Arguments without the program name; defaults to ``sys.argv[1:]``.

    Returns:
        The exit code: 0 done, 1 merged but the checks found problems, 2 bad input.
    """
    parser = argparse.ArgumentParser(prog="topics.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    exp = sub.add_parser("export", help="write a cohort's variables for the tagger")
    exp.add_argument("cohort", type=Path, help="the cohort's folder, e.g. site/data/bcs70")
    exp.add_argument("--out", type=Path, required=True, help="the variables.jsonl to write")
    mer = sub.add_parser("merge", help="merge the tagger's tags into a cohort")
    mer.add_argument("cohort", type=Path, help="the cohort's folder, e.g. site/data/bcs70")
    mer.add_argument("--tags", type=Path, required=True, help="the folder the tagger wrote")
    mer.add_argument(
        "--identifier-topic", default="identifiers", help="topic for the cohort's identifier"
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "export":
            n = export(args.cohort, args.out)
            print(f"Wrote {n} variables to {args.out}")
            return OK
        result = merge(args.cohort, args.tags, args.identifier_topic)
    except TopicsError as e:
        _err(str(e))
        return BAD_INPUT

    _listed("Tags for variables not in the cohort, ignored", result.unknown)
    _listed("Variables with no tags, left without topics", result.untagged)
    _listed("Tags made with another scheme (stale), skipped", result.stale)
    if result.problems:
        _listed("The data checks found problems", [str(p) for p in result.problems])
        return CHECKS_FAILED
    print(f"Merged the tags into {args.cohort}; the data checks pass.")
    return OK


if __name__ == "__main__":
    sys.exit(main())
