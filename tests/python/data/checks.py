"""Check supplied cohort data against its documented format (contracts/site-data.md).

The data team supplies `site/data/` ready to use, and the site uses it as it is. These checks
are what stop a malformed drop from being published: every problem is collected and reported
as `<path>[: <location>]: <message>`, so one run lists everything to fix.

One function per rule, D1-D8. Standard library only. Later rules skip what an earlier rule
has already reported (a file that is not valid JSON is not also checked for its contents).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
MISSING = object()


@dataclass(frozen=True)
class Problem:
    """One way the supplied data breaks the format.

    Attributes:
        path: The file, relative to the data folder, e.g. `bcs70/index.json`.
        location: Where in the file, e.g. `row 12 (BD1AGEFB)`, or "" for the whole file.
        message: What is wrong.
    """

    path: str
    location: str
    message: str

    def __str__(self) -> str:
        """Return `<path>[: <location>]: <message>`."""
        where = f": {self.location}" if self.location else ""
        return f"{self.path}{where}: {self.message}"


@dataclass
class _Report:
    """The problems found so far."""

    problems: list[Problem] = field(default_factory=list)

    def add(self, path: str, location: str, message: str) -> None:
        self.problems.append(Problem(path, location, message))


# ── Small type tests ────────────────────────────────────────────────────


def _is_int(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _is_num(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_str(x: object) -> bool:
    return isinstance(x, str)


def _fields(report, path, location, obj, required, optional=()):
    """Check an object's fields have the right types; return False if it is not an object.

    Args:
        report: Where problems go.
        path: The file being checked.
        location: Where the object is in the file.
        obj: The object.
        required: (name, test, description) for fields that must be present.
        optional: The same for fields that may be absent or null.

    Returns:
        Whether every required field is present with the right type.
    """
    if not isinstance(obj, dict):
        report.add(path, location, "should be an object")
        return False
    ok = True
    for name, test, what in required:
        value = obj.get(name, MISSING)
        if value is MISSING:
            report.add(path, location, f"missing required field '{name}'")
            ok = False
        elif not test(value):
            report.add(path, location, f"'{name}' should be {what}")
            ok = False
    for name, test, what in optional:
        value = obj.get(name, MISSING)
        if value is not MISSING and value is not None and not test(value):
            report.add(path, location, f"'{name}' should be {what}")
    return ok


def _list_of(test):
    return lambda x: isinstance(x, list) and all(test(i) for i in x)


STR = (_is_str, "a string")
INT = (_is_int, "a whole number")
LIST = (lambda x: isinstance(x, list), "a list")
OBJ = (lambda x: isinstance(x, dict), "an object")


def _req(name, kind):
    return (name, *kind)


# ── D1: readable JSON of the right shape ────────────────────────────────


def _load(report: _Report, data_dir: Path, rel: str):
    """D1: read one file as UTF-8 JSON, or report why it cannot be.

    Returns:
        The parsed value, or MISSING if the file is absent or unreadable.
    """
    path = data_dir / rel
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.add(rel, "", "file is missing")
    except UnicodeDecodeError as err:
        report.add(rel, "", f"not valid UTF-8 ({err.reason} at byte {err.start})")
    except json.JSONDecodeError as err:
        report.add(rel, f"line {err.lineno}", f"not valid JSON ({err.msg})")
    return MISSING


def check_catalogue_shape(report: _Report, catalogue) -> list[dict]:
    """D1: `datasets.json` has `built` and a list of datasets with their required fields.

    Returns:
        The well-formed dataset entries.
    """
    rel = "datasets.json"
    if not _fields(report, rel, "", catalogue, [_req("built", STR), _req("datasets", LIST)]):
        return []
    good = []
    for i, d in enumerate(catalogue["datasets"]):
        req = [_req("key", STR), _req("name", STR), _req("variables", INT), _req("files", INT)]
        opt = [_req("fullName", STR), _req("description", STR)]
        if _fields(report, rel, f"datasets[{i}]", d, req, opt):
            good.append(d)
    return good


def check_manifest_shape(report: _Report, rel: str, m) -> bool:
    """D1: a manifest has every required field with the right type.

    Returns:
        Whether the manifest is usable by the later rules.
    """
    req = [
        _req("key", STR),
        _req("name", STR),
        _req("fullName", STR),
        _req("identifier", STR),
        _req("wave", OBJ),
        _req("files", LIST),
        _req("counts", OBJ),
    ]
    opt = [
        _req("description", STR),
        _req("ukdsUrl", STR),
        _req("built", STR),
        ("levels", _list_of(_is_str), "a list of strings"),
        _req("topics", OBJ),
    ]
    ok = _fields(report, rel, "", m, req, opt)
    if not ok:
        return False
    wave_req = [_req("term", STR), _req("plural", STR), _req("list", LIST)]
    if _fields(report, rel, "wave", m["wave"], wave_req):
        for i, w in enumerate(m["wave"]["list"]):
            ok &= _fields(
                report, rel, f"wave.list[{i}]", w, [_req("key", STR)], [_req("label", STR)]
            )
    else:
        ok = False
    for i, f in enumerate(m["files"]):
        req = [
            _req("name", STR),
            _req("wave", STR),
            ("hasId", lambda x: isinstance(x, bool), "true or false"),
        ]
        opt = [_req("study", STR), _req("description", STR)]
        ok &= _fields(report, rel, f"files[{i}]", f, req, opt)
    ok &= _fields(report, rel, "counts", m["counts"], [_req("variables", INT), _req("files", INT)])
    if "topics" in m and isinstance(m["topics"], dict):
        ok &= _check_scheme_shape(report, rel, m["topics"])
    return ok


def _check_scheme_shape(report, rel, scheme) -> bool:
    if not _fields(report, rel, "topics", scheme, [_req("domains", LIST)]):
        return False
    ok = True
    for di, d in enumerate(scheme["domains"]):
        where = f"topics.domains[{di}]"
        if not _fields(
            report, rel, where, d, [_req("id", STR), _req("label", STR), _req("topics", LIST)]
        ):
            ok = False
            continue
        for ti, t in enumerate(d["topics"]):
            ok &= _fields(
                report, rel, f"{where}.topics[{ti}]", t, [_req("id", STR), _req("label", STR)]
            )
    return ok


def check_index_shape(report: _Report, rel: str, index) -> list[tuple[int, list]]:
    """D1: the index is a list of rows `[name, label, file, sweep, level, topics?]`.

    Returns:
        (row number, row) for the well-formed rows.
    """
    if not isinstance(index, list):
        report.add(rel, "", "should be a list of rows")
        return []
    good = []
    for i, row in enumerate(index):
        where = f"row {i}"
        if not isinstance(row, list) or len(row) not in (5, 6):
            report.add(
                rel, where, "should be [name, label, file, sweep, level] plus optional topics"
            )
            continue
        if not (_is_str(row[0]) and _is_str(row[1])):
            report.add(rel, where, "name and label should be strings")
        elif not all(_is_int(x) for x in row[2:5]):
            report.add(rel, f"{where} ({row[0]})", "file, sweep and level should be whole numbers")
        elif len(row) == 6 and not _list_of(_is_num)(row[5]):
            report.add(rel, f"{where} ({row[0]})", "topics should be a list of numbers")
        else:
            good.append((i, row))
    return good


def check_dict_shape(report: _Report, rel: str, d) -> list[dict] | None:
    """D1: a dictionary has `file`, `wave` and a list of variables, each named.

    Returns:
        The well-formed variable entries, or None when the dictionary itself is malformed.
    """
    if not _fields(
        report, rel, "", d, [_req("file", STR), _req("wave", STR), _req("variables", LIST)]
    ):
        return None
    good = []
    for i, v in enumerate(d["variables"]):
        opt = [_req(n, STR) for n in ("label", "pos", "type", "measurement", "missing")]
        if _fields(report, rel, f"variables[{i}]", v, [_req("variable", STR)], opt):
            good.append(v)
    return good


# ── D2: the catalogue ───────────────────────────────────────────────────


def check_catalogue(report: _Report, data_dir: Path, datasets: list[dict]) -> list[dict]:
    """D2: keys are unique and well formed, and each has its manifest and index.

    Returns:
        The datasets whose folders can be checked.
    """
    rel = "datasets.json"
    seen = set()
    usable = []
    for i, d in enumerate(datasets):
        key = d["key"]
        where = f"datasets[{i}] ({key})"
        if not KEY_RE.match(key):
            report.add(
                rel, where, "key should be lower-case letters, digits and _, starting with a letter"
            )
            continue
        if key in seen:
            report.add(rel, where, f"key '{key}' is listed twice")
            continue
        seen.add(key)
        missing = [n for n in ("manifest.json", "index.json") if not (data_dir / key / n).is_file()]
        if missing:
            report.add(rel, where, f"no {' or '.join(f'{key}/{n}' for n in missing)}")
            continue
        usable.append(d)
    return usable


def check_catalogue_counts(report: _Report, i: int, entry: dict, m: dict) -> None:
    """D2: the catalogue's variable and file counts match the manifest's."""
    for name in ("variables", "files"):
        if entry[name] != m["counts"][name]:
            report.add(
                "datasets.json",
                f"datasets[{i}] ({entry['key']})",
                f"'{name}' is {entry[name]} but {entry['key']}/manifest.json says "
                f"{m['counts'][name]}",
            )


# ── D3: the manifest ────────────────────────────────────────────────────


def check_manifest(report: _Report, rel: str, key: str, m: dict, index_len: int | None) -> set[str]:
    """D3: key, sweeps, file names, file sweeps and counts are consistent.

    Returns:
        The declared sweep keys.
    """
    if m["key"] != key:
        report.add(rel, "key", f"is '{m['key']}' but the folder is '{key}'")
    waves = [w["key"] for w in m["wave"]["list"]]
    for i, w in enumerate(waves):
        if not w:
            report.add(rel, f"wave.list[{i}]", "sweep key is empty")
        elif waves.index(w) != i:
            report.add(rel, f"wave.list[{i}]", f"sweep '{w}' is listed twice")
    names = []
    for i, f in enumerate(m["files"]):
        where = f"files[{i}] ({f['name']})"
        if not FILE_RE.match(f["name"]):
            report.add(rel, where, "file name should be letters, digits, _, . and - only")
        if f["name"] in names:
            report.add(rel, where, f"file '{f['name']}' is listed twice")
        names.append(f["name"])
        if f["wave"] not in waves:
            report.add(rel, where, f"sweep '{f['wave']}' is not declared in wave.list")
    if m["counts"]["files"] != len(m["files"]):
        report.add(
            rel, "counts.files", f"is {m['counts']['files']} but {len(m['files'])} files are listed"
        )
    if index_len is not None and m["counts"]["variables"] != index_len:
        report.add(
            rel,
            "counts.variables",
            f"is {m['counts']['variables']} but index.json has {index_len} rows",
        )
    return set(waves)


# ── D4: the index rows ──────────────────────────────────────────────────


def check_index(
    report: _Report, rel: str, rows: list[tuple[int, list]], m: dict, n_topics: int
) -> list:
    """D4: names are non-empty and every index (file, sweep, level, topic) is in range.

    Returns:
        The rows whose file index is in range, for D5.
    """
    n_files, n_waves = len(m["files"]), len(m["wave"]["list"])
    n_levels = len(m.get("levels") or [])
    good = []
    for i, row in rows:
        where = f"row {i} ({row[0]})"
        if not row[0]:
            report.add(rel, f"row {i}", "variable name is empty")
        file_ok = 0 <= row[2] < n_files
        if not file_ok:
            report.add(rel, where, f"file index {row[2]} is out of range (0-{n_files - 1})")
        if not 0 <= row[3] < n_waves:
            report.add(rel, where, f"sweep index {row[3]} is out of range (0-{n_waves - 1})")
        if not -1 <= row[4] < n_levels:
            report.add(rel, where, f"level index {row[4]} is out of range (-1-{n_levels - 1})")
        if len(row) == 6:
            topics = row[5]
            if len(topics) % 2:
                report.add(
                    rel, where, "topic list should be [topic, percent, ...] pairs (odd length)"
                )
            else:
                for t, pct in zip(topics[::2], topics[1::2], strict=True):
                    if not (_is_int(t) and 0 <= t < n_topics):
                        report.add(
                            rel, where, f"topic index {t} is out of range (0-{n_topics - 1})"
                        )
                    if not 0 <= pct <= 100:
                        report.add(rel, where, f"topic percent {pct} should be 0-100")
        if file_ok:
            good.append((i, row))
    return good


# ── D5: dictionaries ────────────────────────────────────────────────────


def check_dict_header(report: _Report, rel: str, d: dict, file: dict, waves: set[str]) -> None:
    """D5: a dictionary's `file` and `wave` match the manifest's entry for it."""
    if d["file"] != file["name"]:
        report.add(rel, "file", f"is '{d['file']}' but should be '{file['name']}'")
    if file["wave"] in waves and d["wave"] != file["wave"]:
        report.add(rel, "wave", f"is '{d['wave']}' but manifest.json says '{file['wave']}'")


def check_unique_variables(report: _Report, rel: str, variables: list[dict]) -> None:
    """D5: variable names are unique within a file, ignoring case."""
    seen = {}
    for v in variables:
        low = v["variable"].lower()
        if low in seen:
            report.add(
                rel, f"variable {v['variable']}", f"same name as '{seen[low]}' (ignoring case)"
            )
        else:
            seen[low] = v["variable"]


def check_rows_in_dicts(
    report: _Report, rel: str, rows: list, m: dict, names: dict[int, set[str]]
) -> None:
    """D5: every index row's variable is in its file's dictionary."""
    for i, row in rows:
        known = names.get(row[2])
        if known is not None and row[0] not in known:
            report.add(
                rel, f"row {i} ({row[0]})", f"not in the dictionary of {m['files'][row[2]]['name']}"
            )


# ── D6: value labels and missing codes ──────────────────────────────────


def _pair_list(x) -> bool:
    return isinstance(x, list) and all(
        isinstance(p, list) and len(p) == 2 and _is_num(p[0]) and _is_str(p[1]) for p in x
    )


def check_values_and_na(report: _Report, rel: str, v: dict) -> None:
    """D6: value labels have `value` and `label` strings; `na` has numeric codes and ranges."""
    where = f"variable {v['variable']}"
    values = v.get("values")
    if values is not None:
        if not isinstance(values, list):
            report.add(rel, where, "'values' should be a list")
        else:
            for j, item in enumerate(values):
                if not (
                    isinstance(item, dict)
                    and _is_str(item.get("value"))
                    and _is_str(item.get("label"))
                ):
                    report.add(rel, where, f"values[{j}] should have 'value' and 'label' strings")
    na = v.get("na")
    if na is None:
        return
    if not isinstance(na, dict):
        report.add(rel, where, "'na' should be an object")
        return
    if not _list_of(_is_num)(na.get("values")):
        report.add(rel, where, "na.values should be a list of numbers")
    ranges = na.get("ranges")
    if not isinstance(ranges, list):
        report.add(rel, where, "na.ranges should be a list of [low, high] pairs")
    else:
        for j, r in enumerate(ranges):
            ends_ok = (
                isinstance(r, list) and len(r) == 2 and all(e is None or _is_num(e) for e in r)
            )
            if not ends_ok:
                report.add(rel, where, f"na.ranges[{j}] should be [low, high], numbers or null")
            elif None not in r and r[0] > r[1]:
                report.add(rel, where, f"na.ranges[{j}] {r} has low above high")
    for name in ("kept", "lossy"):
        if name in na and not _pair_list(na[name]):
            report.add(rel, where, f"na.{name} should be a list of [code, label] pairs")


# ── D7: topics ──────────────────────────────────────────────────────────


def check_scheme(report: _Report, rel: str, scheme: dict | None) -> set[str]:
    """D7: domain and topic ids in a scheme are unique.

    Returns:
        The topic ids, empty when the cohort has no scheme.
    """
    if not scheme:
        return set()
    seen: set[str] = set()
    for d in scheme["domains"]:
        for item in (d, *d["topics"]):
            if item["id"] in seen:
                report.add(rel, f"topics ({item['id']})", "id is used twice in the scheme")
            seen.add(item["id"])
    return {t["id"] for d in scheme["domains"] for t in d["topics"]}


def check_tags(report: _Report, rel: str, v: dict, topic_ids: set[str]) -> None:
    """D7: a variable's topic tags name topics in the scheme, with confidences 0-1."""
    tags = v.get("topics")
    if tags is None:
        return
    where = f"variable {v['variable']}"
    if not isinstance(tags, list):
        report.add(rel, where, "'topics' should be a list of [id, confidence] pairs")
        return
    for tag in tags:
        if not (isinstance(tag, list) and len(tag) == 2 and _is_str(tag[0]) and _is_num(tag[1])):
            report.add(rel, where, f"topic tag {tag!r} should be [id, confidence]")
            continue
        if tag[0] not in topic_ids:
            report.add(rel, where, f"topic '{tag[0]}' is not in the cohort's topic scheme")
        if not 0 <= tag[1] <= 1:
            report.add(rel, where, f"confidence {tag[1]} for '{tag[0]}' should be between 0 and 1")


# ── D8: the identifier ──────────────────────────────────────────────────


def check_has_id(
    report: _Report, rel: str, i: int, file: dict, names: set[str], identifier: str
) -> None:
    """D8: `hasId` is true exactly when the file's dictionary has the identifier."""
    has = identifier.lower() in {n.lower() for n in names}
    if file["hasId"] != has:
        report.add(
            rel,
            f"files[{i}] ({file['name']})",
            f"hasId is {str(file['hasId']).lower()} but the dictionary "
            f"{'has' if has else 'has no'} {identifier}",
        )


# ── Putting it together ─────────────────────────────────────────────────


def _check_cohort(report: _Report, data_dir: Path, i: int, entry: dict) -> None:
    key = entry["key"]
    mrel, irel = f"{key}/manifest.json", f"{key}/index.json"
    m = _load(report, data_dir, mrel)
    index = _load(report, data_dir, irel)
    if m is MISSING or not check_manifest_shape(report, mrel, m):
        return
    check_catalogue_counts(report, i, entry, m)
    rows = check_index_shape(report, irel, index) if index is not MISSING else None
    waves = check_manifest(report, mrel, key, m, None if index is MISSING else len(index))
    topic_ids = check_scheme(report, mrel, m.get("topics"))
    n_topics = sum(len(d["topics"]) for d in (m.get("topics") or {}).get("domains", []))
    rows = check_index(report, irel, rows, m, n_topics) if rows is not None else []

    names: dict[int, set[str]] = {}
    for fi, file in enumerate(m["files"]):
        if not FILE_RE.match(file["name"]):
            continue
        drel = f"{key}/dict/{file['name']}.json"
        d = _load(report, data_dir, drel)
        if d is MISSING:
            continue
        variables = check_dict_shape(report, drel, d)
        if variables is None:
            continue
        check_dict_header(report, drel, d, file, waves)
        check_unique_variables(report, drel, variables)
        for v in variables:
            check_values_and_na(report, drel, v)
            check_tags(report, drel, v, topic_ids)
        names[fi] = {v["variable"] for v in variables}
        check_has_id(report, mrel, fi, file, names[fi], m["identifier"])
    check_rows_in_dicts(report, irel, rows, m, names)


def check_data(data_dir: Path) -> list[Problem]:
    """Check a site data folder against every rule, D1-D8.

    Args:
        data_dir: The folder holding `datasets.json` and one folder per cohort.

    Returns:
        Every problem found, in the order found; empty when the data is valid.
    """
    report = _Report()
    catalogue = _load(report, data_dir, "datasets.json")
    if catalogue is MISSING:
        return report.problems
    datasets = check_catalogue_shape(report, catalogue)
    for entry in check_catalogue(report, data_dir, datasets):
        _check_cohort(report, data_dir, datasets.index(entry), entry)
    return report.problems
