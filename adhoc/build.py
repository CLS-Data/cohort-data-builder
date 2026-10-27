"""Stage 3: the staged cohorts, and their tags if there are any, to the site's data format.

    uv run python adhoc/build.py

Reads ``data/staging/<key>/`` (from ``stage.py``) and, when the Topic Tagger has been run
for a cohort, ``data/staging/<key>/tags/``. Writes ``data/processed/`` exactly as
``site/data`` is laid out (docs/data-format.md): ``datasets.json`` and, per cohort,
``manifest.json``, ``index.json`` and ``dict/<file>.json``. Then merges the tags with
``scripts/topics.py`` and runs the site's data checks (``scripts/checks.py``).

Besides the documented fields, each variable keeps ``question`` (the question text),
``human`` (the CSV's research topic and subtopic) and ``clsId``; each file keeps its
``licence``, ``category`` and UKDS deposit. The site ignores fields it does not know.
The CSV lists no identifiers, so each file that holds the identifier gets it added as
its first variable. Exits 1 if the checks find problems.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))

from checks import check_data  # noqa: E402
from topics import merge  # noqa: E402

LEVELS = ["NOMINAL", "ORDINAL", "SCALE"]


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def _pos(rec: dict) -> tuple[int, str]:
    try:
        return int(rec["pos"]), rec["variable"]
    except (TypeError, ValueError):
        return 10**9, rec["variable"]


def dict_variable(rec: dict) -> dict:
    """A staged record as a dictionary entry: the site's fields, then the kept extras."""
    out = {
        "variable": rec["variable"],
        "label": rec["label"] or None,
        "pos": rec["pos"],
        "type": rec["type"],
        "measurement": rec["measurement"],
        "missing": rec["missing"],
        "na": rec["na"],
        "values": [{"value": v, "label": label} for v, label in rec["values"]] or None,
        "question": rec["csv"].get("question_text") or None,
        "human": rec["human"],
        "clsId": rec["csv"].get("CLS_variable_id") or None,
    }
    if rec["valuesCut"]:
        out["valuesCut"] = True
    return out


def identifier_variable(name: str) -> dict:
    """The identifier, added to a file's dictionary because the CSV does not list it."""
    return {"variable": name, "label": "Participant identifier", "pos": "0", "added": True}


def build_cohort(staged: Path, out: Path, built: str) -> dict:
    """Write one cohort in the site's format and return its ``datasets.json`` entry."""
    cohort = _read(staged / "cohort.json")
    files = _read(staged / "files.json")
    sweeps = _read(staged / "sweeps.json")
    records: dict[str, list[dict]] = {f["name"]: [] for f in files}
    with (staged / "variables.jsonl").open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            records[rec["file"]].append(rec)

    sweep_index = {s["key"]: i for i, s in enumerate(sweeps)}
    # Files in sweep order, then by name; cross-sweep files last.
    files.sort(key=lambda f: (sweep_index[f["wave"]], f["name"].lower()))
    ident = cohort["identifier"]
    index = []
    for i, f in enumerate(files):
        recs = sorted(records[f["name"]], key=_pos)
        variables = [dict_variable(r) for r in recs]
        if f["hasId"] and not any(r["variable"].lower() == ident.lower() for r in recs):
            variables.insert(0, identifier_variable(ident.upper()))
            index.append([ident.upper(), "Participant identifier", i, sweep_index[f["wave"]], -1])
        for r in recs:
            level = LEVELS.index(r["measurement"]) if r["measurement"] in LEVELS else -1
            index.append([r["variable"], r["label"], i, sweep_index[r["sweep"]], level])
        _write(
            out / "dict" / f"{f['name']}.json",
            {
                "file": f["name"],
                "wave": f["wave"],
                "variables": variables,
            },
        )

    manifest = {
        **{k: cohort[k] for k in ("key", "name", "fullName", "description", "identifier")},
        "ukdsUrl": cohort.get("ukdsUrl"),
        "built": built,
        "wave": {
            "term": "sweep",
            "plural": "sweeps",
            "list": [{"key": s["key"], "label": s["label"]} for s in sweeps],
        },
        "levels": LEVELS,
        "files": [
            {
                "name": f["name"],
                "wave": f["wave"],
                "study": f["study"],
                "description": f["description"],
                "hasId": f["hasId"],
                "licence": f["licence"],
                "category": f["category"],
                "ukdsDeposit": f["ukdsDeposit"],
            }
            for f in files
        ],
        "counts": {"variables": len(index), "files": len(files)},
    }
    _write(out / "manifest.json", manifest)
    _write(out / "index.json", index)
    return {
        **{k: cohort[k] for k in ("key", "name", "fullName", "description")},
        "variables": len(index),
        "files": len(files),
    }


def main() -> int:
    """Run stage 3 from the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--staging", type=Path, default=HERE / "data/staging")
    parser.add_argument("--out", type=Path, default=HERE / "data/processed")
    parser.add_argument("--cohorts", type=Path, default=HERE / "cohorts.json")
    parser.add_argument("--identifier-topic", default="identifiers")
    args = parser.parse_args()

    order = [v["key"] for k, v in _read(args.cohorts).items() if k[0] != "_"]
    keys = [k for k in order if (args.staging / k / "variables.jsonl").exists()]
    built = date.today().isoformat()
    for k in keys:
        shutil.rmtree(args.out / k, ignore_errors=True)
    entries = [build_cohort(args.staging / k, args.out / k, built) for k in keys]
    _write(args.out / "datasets.json", {"built": built, "datasets": entries})
    for e in entries:
        print(f"{e['name']}: {e['variables']:,} variables in {e['files']} files")

    for k in keys:
        tags = args.staging / k / "tags"
        if not (tags / "tags.jsonl").exists():
            print(f"{k}: no tags in {tags}; built without topics")
            continue
        result = merge(args.out / k, tags, args.identifier_topic)
        print(
            f"{k}: tags merged; {len(result.untagged):,} variables untagged, "
            f"{len(result.stale):,} stale tags skipped, {len(result.unknown):,} unknown"
        )

    problems = check_data(args.out)
    for p in problems[:50]:
        print(p)
    print(f"Data checks: {len(problems)} problems" if problems else "Data checks pass.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
