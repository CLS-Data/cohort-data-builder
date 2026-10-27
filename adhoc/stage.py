"""Stage 1: the raw CLS metadata CSV to one staging folder per cohort.

    uv run python adhoc/stage.py

Reads ``data/raw/CLS_studies_metadata.csv`` and writes, for each study in
``cohorts.json``, ``data/staging/<key>/``:

    variables.jsonl   one record per variable: the site's fields, worked out, plus every
                      CSV column unchanged under "csv" and the human-assigned topics
    files.json        the data files, with their sweep, UKDS study, licence and whether
                      they hold the identifier
    sweeps.json       the sweeps in time order, cross-sweep last
    tagger/variables.jsonl   the Topic Tagger's input

and ``data/staging/report.md``. Where the live site already has a variable
(``site/data``), its type, measurement level, value labels and missing codes are taken
from there: they come from the data files themselves, which the CSV does not have.
Nothing is lost: the CSV row is always kept. Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from cls_metadata import derive_na, fix_text, parse_value_labels, sweep_key, sweep_label

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read_csv(path: Path) -> list[dict]:
    """The CSV's rows, with C1 characters repaired; its first line is a title, not a header."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        f.readline()
        return [{k: fix_text(v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def load_site(folder: Path) -> tuple[dict, dict]:
    """A live cohort's variables keyed by (file, variable) ignoring case, and its files."""
    if not (folder / "manifest.json").exists():
        return {}, {}
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    variables, files = {}, {}
    for f in manifest["files"]:
        files[f["name"].lower()] = f
        d = json.loads((folder / "dict" / f"{f['name']}.json").read_text(encoding="utf-8"))
        for v in d["variables"]:
            variables[(f["name"].lower(), v["variable"].lower())] = v
    return variables, files


def _file(row: dict) -> str:
    return row["dataset_name"].rsplit(".", 1)[0]


def unify_files(rows: list[dict], site_files: dict) -> tuple[list[dict], dict, list[str]]:
    """Treat file names that differ only in case as one file.

    The CSV sometimes spells one data file two ways. The live site's spelling wins,
    otherwise the spelling with the most rows. A variable listed under both spellings is
    kept once, from the rows with the winning spelling.

    Returns:
        The rows without those duplicates, the spelling for each lower-cased name, and
        notes for the report.
    """
    spellings: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        spellings[_file(row).lower()][_file(row)] += 1
    names, notes = {}, []
    for low, c in spellings.items():
        live = site_files.get(low)
        names[low] = live["name"] if live else c.most_common(1)[0][0]
        if len(c) > 1:
            notes.append(f"{' and '.join(sorted(c))} are one file, named {names[low]}")
    keep, seen, dropped = [], set(), Counter()
    # Rows with the winning spelling first, so theirs is the copy kept.
    for row in sorted(rows, key=lambda r: _file(r) != names[_file(r).lower()]):
        key = (_file(row).lower(), row["variable_name"].lower())
        if key in seen:
            dropped[names[key[0]]] += 1
            continue
        seen.add(key)
        keep.append(row)
    notes += [
        f"{name}: {n} variables listed under both spellings, kept once"
        for name, n in dropped.items()
    ]
    order = {id(r): i for i, r in enumerate(rows)}
    keep.sort(key=lambda r: order[id(r)])
    return keep, names, notes


def stage_variable(row: dict, site: dict | None, file: str) -> dict:
    """One staging record from a CSV row and, if the live site has it, its site entry."""
    numeric = row["var_spss_type"] == "0"
    values, cut = parse_value_labels(row["value_labels_to_2000_chars"], numeric=numeric)
    rec = {
        "file": file,
        "variable": row["variable_name"],
        "label": row["variable_label"],
        "sweep": sweep_key(row["sweep"]),
        "pos": row["var_order"],
        "type": "numeric" if numeric else "string",
        "format": row["var_spss_format"],
        "measurement": None,
        "missing": None,
        "values": values,
        "valuesCut": cut,
        "valuesFrom": "csv",
        "na": derive_na(values) if numeric else None,
        "naFrom": "derived",
        "human": {
            "topic": [row["research_topic_code"], row["research_topic"].strip()],
            "subtopic": [row["research_subtopic_code"], row["research_subtopic"].strip()],
        },
        "csv": row,
    }
    if rec["na"] is None:
        rec["naFrom"] = None
    if site:
        rec["type"] = site.get("type") or rec["type"]
        rec["measurement"] = site.get("measurement")
        rec["missing"] = site.get("missing")
        rec["na"], rec["naFrom"] = site.get("na"), "site"
        if site.get("values"):
            rec["values"] = [[x["value"], x["label"]] for x in site["values"]]
            rec["valuesCut"], rec["valuesFrom"] = False, "site"
    return rec


def stage_files(records: list[dict], rows: list[dict], site_files: dict) -> list[dict]:
    """The cohort's data files, each with one sweep (``xwave`` if its rows span several)."""
    by_file: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    for rec, row in zip(records, rows, strict=True):
        by_file[rec["file"]].append((rec, row))
    out = []
    for name, pairs in by_file.items():
        sweeps = sorted({rec["sweep"] for rec, _ in pairs})

        def common(col: str, pairs=pairs) -> str:
            return Counter(row[col] for _, row in pairs).most_common(1)[0][0]

        live = site_files.get(name.lower())
        out.append(
            {
                "name": name,
                "wave": sweeps[0] if len(sweeps) == 1 else "xwave",
                "sweeps": sweeps,
                "study": live["study"] if live else common("ukds_sn"),
                "description": live["description"] if live else common("ukds_sn_title"),
                # The CSV lists no identifiers. Files the live site has say whether they
                # hold it; every other file is assumed to, as CLS files do.
                "hasId": live["hasId"] if live else True,
                "hasIdFrom": "site" if live else "assumed",
                "licence": sorted({row["data_sharing_licence"] for _, row in pairs}),
                "category": common("ukds_sn_category"),
                "ukdsDeposit": common("ukds_deposit"),
                "ukdsSeries": [common("ukds_gn"), common("ukds_gn_title")],
                "variables": len(pairs),
            }
        )
    return out


def stage_sweeps(rows: list[dict]) -> list[dict]:
    """The sweeps in time order, cross-sweep last, each with the CSV's own text."""
    seen = {}
    for row in rows:
        seen.setdefault(row["sweep"], row["sweep-year-age"])
    order = sorted(seen, key=lambda s: (float(s) < 0, float(s)))
    return [{"key": sweep_key(s), "label": sweep_label(seen[s]), "csv": seen[s]} for s in order]


def tagger_line(rec: dict, sweeps: dict) -> str:
    """The Topic Tagger's input line for a variable (docs/formats.md in the tool)."""
    line = {
        "file": rec["file"],
        "variable": rec["variable"],
        "label": rec["label"],
        "values": rec["values"],
        "sweep": sweeps[rec["sweep"]],
    }
    return json.dumps(line, ensure_ascii=False)


def write_jsonl(path: Path, lines: list[str]) -> None:
    """Write lines with a final newline, creating the folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(x + "\n" for x in lines), encoding="utf-8")


def stage(raw: Path, out: Path, cohorts: dict, site: Path) -> str:
    """Stage every cohort and return the report as Markdown."""
    rows = read_csv(raw)
    unknown = sorted({r["study"] for r in rows} - set(cohorts))
    if unknown:
        sys.exit(f"Studies not in cohorts.json: {', '.join(unknown)}")

    report = ["# Staging report", "", f"Source: `{raw.name}`, {len(rows):,} rows.", ""]
    for study, cohort in cohorts.items():
        key = cohort["key"]
        mine = [r for r in rows if r["study"] == study]
        site_vars, site_files = load_site(site / key)
        mine, names, notes = unify_files(mine, site_files)
        records = []
        for r in mine:
            file = names[_file(r).lower()]
            live = site_vars.get((file.lower(), r["variable_name"].lower()))
            records.append(stage_variable(r, live, file))
        files = stage_files(records, mine, site_files)
        sweeps = stage_sweeps(mine)
        folder = out / key
        folder.mkdir(parents=True, exist_ok=True)
        write_jsonl(
            folder / "variables.jsonl", [json.dumps(r, ensure_ascii=False) for r in records]
        )
        for name, data in (("files", files), ("sweeps", sweeps), ("cohort", cohort)):
            (folder / f"{name}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        labels = {s["key"]: s["csv"] for s in sweeps}
        write_jsonl(
            folder / "tagger" / "variables.jsonl", [tagger_line(r, labels) for r in records]
        )

        kept = Counter(
            k[1]
            for r in records
            if r["naFrom"] == "derived" and r["na"]
            for k in r["na"].get("kept", [])
        )
        csv_names = {f["name"].lower() for f in files}
        report += [
            f"## {cohort['name']} (`{key}`)",
            "",
            f"- {len(records):,} variables in {len(files)} files over {len(sweeps)} sweeps",
            f"- From the live site: {sum(r['naFrom'] == 'site' for r in records):,} variables"
            f" (type, level, values, missing codes); {sum(f['hasIdFrom'] == 'site' for f in files)}"
            " files (identifier)",
            f"- Missing codes worked out from labels: "
            f"{sum(r['naFrom'] == 'derived' for r in records):,} variables",
            f"- Value labels cut off in the CSV: {sum(r['valuesCut'] for r in records):,}",
            f"- Files assumed to hold `{cohort['identifier']}`: "
            f"{sum(f['hasIdFrom'] == 'assumed' for f in files)}",
            f"- Files spanning several sweeps (put under cross-sweep): "
            f"{', '.join(f['name'] for f in files if len(f['sweeps']) > 1) or 'none'}",
        ]
        report += [f"- {n}" for n in notes]
        if site_files:
            gone = sorted(set(site_files) - csv_names)
            report.append(
                f"- Live site files not in the CSV ({len(gone)}): {', '.join(gone) or 'none'}"
            )
        if kept:
            report.append("- Negative codes kept as answers (label: variables), most common:")
            report += [f"  - {label}: {n}" for label, n in kept.most_common(15)]
        report.append("")
    return "\n".join(report)


def main() -> None:
    """Run stage 1 from the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--raw", type=Path, default=HERE / "data/raw/CLS_studies_metadata.csv")
    parser.add_argument("--out", type=Path, default=HERE / "data/staging")
    parser.add_argument("--cohorts", type=Path, default=HERE / "cohorts.json")
    parser.add_argument("--site", type=Path, default=ROOT / "site/data", help="the live data")
    args = parser.parse_args()
    cohorts = {k: v for k, v in json.loads(args.cohorts.read_text()).items() if k[0] != "_"}
    text = stage(args.raw, args.out, cohorts, args.site)
    (args.out / "report.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
