# Contract: Supplied cohort data (`site/data/`)

The data team supplies these files ready to use; they are committed to the repository and
served as-is. The project never generates or alters them. The PoC's built `PoC/site/data/`
is a conforming example. A change to this format is a contract change: update this file,
`docs/data-format.md` and the data checks in the same commit.

```text
site/data/
  datasets.json
  <key>/manifest.json
  <key>/index.json
  <key>/dict/<file>.json      one per entry in manifest.files
```

## `data/datasets.json`

```json
{ "built": "YYYY-MM-DD",
  "datasets": [ { "key": "bcs70", "name": "BCS70", "fullName": "…", "description": "…",
                  "variables": 32452, "files": 84 } ] }
```

## `data/<key>/manifest.json`

```json
{ "key": "next_steps", "name": "Next Steps", "fullName": "…", "description": "…",
  "identifier": "NSID", "ukdsUrl": "https://…", "built": "YYYY-MM-DD",
  "wave": { "term": "sweep", "plural": "sweeps",
            "list": [ { "key": "14y", "label": "Sweep 1, 2004" } ] },
  "levels": ["NOMINAL", "ORDINAL", "SCALE"],
  "files": [ { "name": "wave_one_…", "wave": "14y", "study": "5545",
               "description": "…", "hasId": true } ],
  "counts": { "variables": 11430, "files": 52 },
  "topics": { "name": "…", "version": 1, "hash": "c87a35ec8bc2",
              "domains": [ { "id": "demographics", "label": "…", "description": "…",
                             "topics": [ { "id": "age", "label": "Age", "description": "…" } ] } ] } }
```

`topics` is omitted when the cohort has no tags; the site then hides topic features.

## `data/<key>/index.json`

One compact row per variable:

```json
[ ["BD1AGEFB", "1970: Age of mother at first birth", 0, 0, 2, [0, 90, 100, 80]] ]
```

| Index | Meaning |
|---|---|
| 0 | variable name |
| 1 | label (`""` if none) |
| 2 | file index into `manifest.files` |
| 3 | sweep index into `manifest.wave.list` |
| 4 | level index into `manifest.levels`, or `-1` unrecorded |
| 5 | optional flat topic list `[topicIndex, percent, …]`, strongest first; topic index into the flattened `domains[].topics[]` |

## `data/<key>/dict/<file>.json`

```json
{ "file": "…", "wave": "14y",
  "variables": [ { "variable": "W1histres", "label": "…", "pos": "4", "type": "numeric",
                   "measurement": "NOMINAL", "missing": "-999.0 thru -1.0",
                   "na": { "values": [], "ranges": [[-999, -1]], "kept": [], "lossy": [] },
                   "values": [ { "value": "-92.0", "label": "Refused" } ],
                   "topics": [ ["identifiers", 1.0] ] } ] }
```

`na` is used exactly as supplied (FR-024): `values` and `ranges` (null = open end) are
converted when asked; `kept` codes are never converted; `lossy` codes are converted but
flagged in the interface.

Optional fields: `na` itself (absent = no codes; about 7,800 of the launch variables), and
within it `kept` and `lossy` (absent = empty; present on about 2,100). `values`, `measurement`,
`missing`, `type`, `pos` and `topics` may also be absent.

## Format checks (CI; any error blocks publishing)

Each rule has a test that feeds a violating fixture and expects the stated error, reported
as `<path>[: <location>]: <message>`, all problems at once.

| # | Rule |
|---|---|
| D1 | Every file is valid UTF-8 JSON of the shape above; required fields present with the right types. |
| D2 | `datasets.json` keys are unique, match `^[a-z][a-z0-9_]*$`, and each has `<key>/manifest.json` and `<key>/index.json`; its `variables`/`files` counts match the manifest. |
| D3 | Manifest: `key` matches its folder; sweep keys unique and non-empty; file names unique and match `^[A-Za-z0-9][A-Za-z0-9_.\-]*$`; each file's `wave` is a declared sweep; `counts` match `index.json` and `files`. |
| D4 | Index rows: name non-empty; file, sweep and level indices in range (level may be -1); topic list of even length, topic indices in range, percents 0–100. |
| D5 | Every manifest file has `dict/<file>.json` whose `file` matches and `wave` matches the manifest; every index row's variable exists in that file's dictionary; variable names unique per file ignoring case. |
| D6 | `values`, when present, has entries with `value` and `label` strings. `na`, when present, has `values` (numbers) and `ranges` (pairs, `lo ≤ hi` where both non-null); `kept`/`lossy` are optional, and when present are lists of `[code, label]` pairs. |
| D7 | Topic ids in dictionaries exist in the manifest's scheme; confidences 0–1; scheme ids unique. |
| D8 | `hasId` is true exactly when the file's dictionary contains the identifier (ignoring case). |

## Templates (project code, not supplied data)

The download templates live in `site/templates/` and are fetched as text by the browser at
download time. See [download-project.md](download-project.md#template-placeholders).
