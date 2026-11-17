"""Tag the fictional labelled set flat and tiered with gpt-oss and tiered with Clef; score them.

The set comes from ``build_labelled_set.py``; runs go to ``adhoc/tiered/runs/`` (git-ignored).
From the repository root, with ``S=specs/004-tiered-tagger/results/scripts``:

    uv run --project tools/topic-tagger python $S/score_labelled_set.py
    uv run --project tools/topic-tagger python $S/score_labelled_set.py --self-check
    uv run --project tools/topic-tagger python $S/score_labelled_set.py \
      --score-only adhoc/tiered/runs/*

Tiered runs are made once at a low descend threshold with no cap on areas. They are then
scored offline at each threshold in --sweep (research R13): a topic counts if its area's
path confidence is at least t (the strongest area always counts, at most --cap areas) and
its own confidence is at least k (each of --keep-sweep). Flat runs are scored at each k.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # the repository
DATA = ROOT / "adhoc/tiered"  # git-ignored: inputs and run folders
SCHEME = ROOT / "tools/topic-tagger/src/topic_tagger/schemes/closer.toml"

RUNS = {
    "flat-gptoss": ["--method", "flat", "--model", "gpt-oss:20b-cloud"],
    "tiered-gptoss": [
        "--method",
        "tiered",
        "--model",
        "gpt-oss:20b-cloud",
        "--descend-at",
        "0.1",
        "--max-areas",
        "0",
    ],
    "tiered-clef": [
        "--provider",
        "ollama-decision",
        "--model",
        "clef:cloud",
        "--method",
        "tiered",
        "--descend-at",
        "0.1",
        "--max-areas",
        "0",
        "--keep-at",
        "0",
    ],
}
COMMON = ["--yes", "--plain", "--workers", "4"]


# --- Reading a finished folder ------------------------------------------------------


def load_folder(folder: Path) -> dict:
    """A run folder's records, settings, scheme areas and timing."""
    run = json.loads((folder / "run.json").read_text())
    scheme = json.loads((folder / "scheme.json").read_text())
    area_of = {t["id"]: d["id"] for d in scheme["domains"] for t in d["topics"]}
    n_topics = len(area_of)
    records = {}
    for line in (folder / "tags.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            records[f"{r['file']}/{r['variable']}"] = r
    started = datetime.fromisoformat(run["started"].replace("Z", "+00:00"))
    ended = datetime.fromisoformat(run["ended"].replace("Z", "+00:00"))
    return {
        "name": folder.name,
        "records": records,
        "settings": run["settings"],
        "counts": run["counts"],
        "area_of": area_of,
        "n_topics": n_topics,
        "seconds": (ended - started).total_seconds(),
        "order": run.get("order"),
    }


# --- Scoring ------------------------------------------------------------------------


def kept_areas(path: list, t: float, cap: int) -> list[str]:
    """Areas a run at descend threshold t would follow: >= t, the strongest always, capped."""
    ranked = sorted(path, key=lambda ac: -ac[1])
    areas = [a for a, c in ranked if c >= t] or [a for a, _ in ranked[:1]]
    return areas[:cap] if cap else areas


def predicted(record: dict, area_of: dict, t: float | None, k: float, cap: int) -> list:
    """The record's topics, as a run at (t, k) would have kept them, strongest first."""
    topics = [(x, c) for x, c in record["topics"] if c >= k] or record["topics"][:1]
    if t is None or "path" not in record:
        return topics
    areas = set(kept_areas(record["path"], t, cap))
    inside = [(x, c) for x, c in record["topics"] if area_of.get(x) in areas]
    return [(x, c) for x, c in inside if c >= k] or inside[:1]


def score(run: dict, expected: dict, t: float | None, k: float, cap: int, keys: list) -> dict:
    """Top-1, recall, precision, area recall, tags and requests per variable at (t, k)."""
    hits = n_expected = n_predicted = top1 = area_hits = scored = failed = 0
    area_of = run["area_of"]
    for key in keys:
        want = set(expected.get(key, []))
        record = run["records"].get(key)
        if record is None:
            failed += 1
            n_expected += len(want)
            continue
        got = predicted(record, area_of, t, k, cap)
        scored += 1
        ids = [x for x, _ in got]
        n_predicted += len(ids)
        n_expected += len(want)
        hits += len(want & set(ids))
        top1 += bool(ids) and ids[0] in want
        if "path" in record:
            followed = set(kept_areas(record["path"], t if t is not None else 0, cap))
            area_hits += sum(area_of.get(x) in followed for x in want)
    tiered = run["settings"].get("method") == "tiered"
    return {
        "top1": top1 / len(keys) if keys else 0,
        "recall": hits / n_expected if n_expected else 0,
        "precision": hits / n_predicted if n_predicted else 0,
        "area_recall": (area_hits / n_expected if n_expected else 0) if tiered else None,
        "tags": n_predicted / scored if scored else 0,
        "failed": failed,
        "requests": requests_per_variable(run, t, cap, keys),
    }


def requests_per_variable(run: dict, t: float | None, cap: int, keys: list) -> float:
    """Requests per variable: as counted for flat runs, estimated at t for tiered ones."""
    s, n = run["settings"], len(keys) or 1
    if s.get("method") != "tiered" or t is None:
        return run["counts"]["requests"] / max(run["counts"]["todo"], 1)
    paths = [run["records"][k].get("path", []) for k in keys if k in run["records"]]
    if s.get("provider") == "ollama-decision":
        per_area = math.ceil(64 / 64)  # an area has far fewer than 64 topics
        return sum(1 + per_area * len(kept_areas(p, t, cap)) for p in paths) / n
    size = s.get("batch_size", 20)
    total = 0
    for start in range(0, len(paths), size):
        batch = paths[start : start + size]
        total += 1 + len({a for p in batch for a in kept_areas(p, t, cap)})
    return total / n


# --- Printing -----------------------------------------------------------------------


def table(runs: list, expected: dict, keys: list, sweep: list, keeps: list, cap: int) -> list:
    """One row per run and setting; returns the rows (dicts) and prints them."""
    rows = []
    for run in runs:
        decision = run["settings"].get("provider") == "ollama-decision"
        ks = keeps if decision else [0.0]
        ts = sweep if run["settings"].get("method") == "tiered" else [None]
        for t in ts:
            for k in ks:
                row = {"run": run["name"], "t": t, "k": k if decision else None}
                row.update(score(run, expected, t, k, cap, keys))
                row["seconds"] = run["seconds"]
                rows.append(row)
    head = f"{'run':<34}{'t':>5}{'k':>5}{'top1':>7}{'recall':>8}{'prec':>7}{'area':>7}"
    head += f"{'tags':>6}{'fail':>6}{'req/var':>9}{'secs':>7}"
    print(head)
    print("-" * len(head))
    for r in rows:
        area = f"{r['area_recall']:.2f}" if r["area_recall"] is not None else "-"
        print(
            f"{r['run']:<34}{_f(r['t']):>5}{_f(r['k']):>5}{r['top1']:>7.2f}{r['recall']:>8.2f}"
            f"{r['precision']:>7.2f}{area:>7}{r['tags']:>6.2f}{r['failed']:>6}"
            f"{r['requests']:>9.2f}{r['seconds']:>7.0f}"
        )
    return rows


def _f(x) -> str:
    return "-" if x is None else f"{x:g}"


def disagreements(runs: list, rows: list, expected: dict, keys: list, cap: int) -> None:
    """Variables where the best flat and best tiered rows pick different topics."""

    def best(method):
        cands = [r for r in rows if _method(runs, r["run"]) == method]
        return max(cands, key=lambda r: (r["recall"] + r["precision"], r["top1"]), default=None)

    a, b = best("flat"), best("tiered")
    if not a or not b:
        return
    ra = next(r for r in runs if r["name"] == a["run"])
    rb = next(r for r in runs if r["name"] == b["run"])
    flat_at = f"k={_f(a['k'])}"
    tiered_at = f"t={_f(b['t'])}, k={_f(b['k'])}"
    print(f"\nDisagreements: {a['run']} ({flat_at}) vs {b['run']} ({tiered_at})")
    for key in keys:
        pa = _picked(ra, key, None, a["k"] or 0, cap)
        pb = _picked(rb, key, b["t"], b["k"] or 0, cap)
        if {x for x, _ in pa} != {x for x, _ in pb}:
            print(f"\n{key}  expected: {', '.join(expected.get(key, [])) or '?'}")
            print(f"  flat:   {_tags(pa)}")
            path = rb["records"].get(key, {}).get("path", [])
            print(f"  tiered: {_tags(pb)}   path: {_tags(path)}")


def _method(runs, name):
    return next(r for r in runs if r["name"] == name)["settings"].get("method")


def _picked(run, key, t, k, cap):
    record = run["records"].get(key)
    return predicted(record, run["area_of"], t, k, cap) if record else [("FAILED", 0)]


def _tags(pairs) -> str:
    return ", ".join(f"{x} {c:g}" for x, c in pairs) or "none"


# --- Running ------------------------------------------------------------------------


def run_one(name: str, variables: Path, out_root: Path) -> Path:
    """Tag ``variables`` one way; returns the output folder."""
    out = out_root / f"{name}-{time.strftime('%Y%m%d-%H%M')}"
    argv = [
        sys.executable,
        "-m",
        "topic_tagger",
        "tag",
        str(variables),
        "--out",
        str(out),
        "--scheme",
        str(SCHEME),
        *RUNS[name],
        *COMMON,
    ]
    print(f"\n=== {name}: {' '.join(argv[2:])}", flush=True)
    code = subprocess.call(argv)
    if code not in (0, 1):
        sys.exit(f"{name} failed with exit {code}")
    return out


def self_check() -> None:
    """Score two hand-made folders whose answers are known; raise if any number is off."""
    scheme = {
        "domains": [
            {"id": "a", "topics": [{"id": "x"}, {"id": "y"}]},
            {"id": "b", "topics": [{"id": "z"}]},
        ]
    }
    expected = {"f/1": ["x"], "f/2": ["y", "z"], "f/3": ["z"]}
    keys = list(expected)

    def folder(root, name, settings, records, requests):
        d = Path(root) / name
        d.mkdir()
        (d / "scheme.json").write_text(json.dumps(scheme))
        (d / "tags.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
        run = {
            "started": "2026-11-13T12:00:00Z",
            "ended": "2026-11-13T12:00:30Z",
            "settings": settings,
            "counts": {"requests": requests, "todo": 3},
        }
        (d / "run.json").write_text(json.dumps(run))
        return load_folder(d)

    def rec(v, topics, path=None):
        r = {"file": "f", "variable": v, "topics": topics}
        return {**r, "path": path} if path is not None else r

    with tempfile.TemporaryDirectory() as root:
        flat = folder(
            root,
            "flat",
            {"method": "flat"},
            [
                rec("1", [["x", 0.9], ["z", 0.2]]),
                rec("2", [["y", 0.8]]),
                rec("3", [["x", 0.6]]),
            ],
            requests=1,
        )
        s = score(flat, expected, None, 0, 3, keys)
        assert s["top1"] == 2 / 3, s
        assert s["recall"] == 2 / 4 and s["precision"] == 2 / 4, s
        assert s["area_recall"] is None and s["tags"] == 4 / 3 and s["requests"] == 1 / 3, s
        s = score(flat, expected, None, 0.5, 3, keys)
        assert s["precision"] == 2 / 3, s

        tiered = folder(
            root,
            "tiered",
            {"method": "tiered", "batch_size": 2},
            [
                rec("1", [["x", 0.9]], [["a", 0.9]]),
                rec("2", [["y", 0.7], ["z", 0.4]], [["a", 0.8], ["b", 0.3]]),
                # "3" failed: no record
            ],
            requests=5,
        )
        s = score(tiered, expected, 0.5, 0, 3, keys)
        # at t=0.5 variable 2 keeps only area a, so z is dropped
        assert s["failed"] == 1 and s["recall"] == 2 / 4 and s["precision"] == 1, s
        assert s["area_recall"] == 2 / 4, s
        assert s["requests"] == 2 / 3, s  # one batch of 2: tier 1 + area a
        s = score(tiered, expected, 0.2, 0, 3, keys)
        assert s["recall"] == 3 / 4 and s["area_recall"] == 3 / 4, s
        assert s["requests"] == 3 / 3, s  # tier 1 + areas a and b
        s = score(tiered, expected, 0.2, 0.5, 3, keys)
        assert s["recall"] == 2 / 4, s  # z at 0.4 is below k

        clef = folder(
            root,
            "clef",
            {"method": "tiered", "provider": "ollama-decision"},
            [
                rec("1", [["x", 0.9]], [["a", 0.9], ["b", 0.1]]),
                rec("2", [["y", 0.7], ["z", 0.6]], [["a", 0.8], ["b", 0.6]]),
                rec("3", [["z", 0.9]], [["b", 0.95]]),
            ],
            requests=0,
        )
        s = score(clef, expected, 0.5, 0, 1, keys)  # cap 1: only the strongest area
        assert s["recall"] == 3 / 4 and s["requests"] == 2, s
        s = score(clef, expected, 0.5, 0, 0, keys)
        assert s["recall"] == 1 and s["requests"] == 7 / 3, s
    print("self-check passed")


def main() -> None:
    """Parse the command line, then self-check, or run and score, or score only."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--self-check", action="store_true", help="check the scoring and stop")
    p.add_argument("--only", help="run only these, comma-separated: " + ", ".join(RUNS))
    p.add_argument("--score-only", nargs="+", type=Path, help="score these folders; run nothing")
    p.add_argument("--variables", type=Path, default=DATA / "variables.jsonl")
    p.add_argument("--sweep", default="0.1,0.2,0.3,0.5,0.7", help="descend thresholds t")
    p.add_argument("--keep-sweep", default="0.1,0.2,0.3,0.5", help="Clef keep thresholds k")
    p.add_argument("--cap", type=int, default=3, help="max areas when scoring; 0 for no cap")
    args = p.parse_args()
    if args.self_check:
        self_check()
        return
    if args.score_only:
        folders = args.score_only
    else:
        names = args.only.split(",") if args.only else list(RUNS)
        unknown = set(names) - set(RUNS)
        if unknown:
            sys.exit(f"unknown runs: {', '.join(sorted(unknown))}")
        folders = [run_one(n, args.variables, DATA / "runs") for n in names]
    runs = [load_folder(f) for f in folders if (f / "run.json").exists()]
    keys = [
        f"{v['file']}/{v['variable']}"
        for v in map(json.loads, args.variables.read_text().splitlines())
        if v
    ]
    expected_path = args.variables.parent / "expected.json"
    expected = json.loads(expected_path.read_text()) if expected_path.exists() else {}
    sweep = [float(x) for x in args.sweep.split(",")]
    keeps = [float(x) for x in args.keep_sweep.split(",")]
    if expected:
        rows = table(runs, expected, keys, sweep, keeps, args.cap)
    else:
        print("No expected.json beside the variables: showing only the disagreements.")
        rows = [
            {
                "run": r["name"],
                "t": sweep[0] if r["settings"].get("method") == "tiered" else None,
                "k": keeps[0],
                "recall": 0,
                "precision": 0,
                "top1": 0,
            }
            for r in runs
        ]
    disagreements(runs, rows, expected, keys, args.cap)


if __name__ == "__main__":
    main()
