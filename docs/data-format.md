# Supplied data format

This is for the data team who prepare each cohort's data, and for maintainers who add it to
the site. The site reads these files exactly as supplied. It does not convert dictionaries,
derive missing codes or tag topics: all of that is done before the data arrives here.

Every file is UTF-8 JSON. The checks described in [Checking the data](#checking-the-data)
must pass before anything is published.

```text
site/data/
  datasets.json              the list of cohorts
  <key>/manifest.json        one cohort: sweeps, files, topic scheme
  <key>/index.json           one row per variable, for search
  <key>/dict/<file>.json     one data dictionary per data file
```

`<key>` is the cohort's short name: lower-case letters, digits and `_`, starting with a letter
(for example `bcs70`, `next_steps`). The site's address for a cohort is `…/#<key>`.

## `datasets.json`

```json
{ "built": "2026-10-09",
  "datasets": [ { "key": "bcs70", "name": "BCS70", "fullName": "1970 British Cohort Study",
                  "description": "…", "variables": 32452, "files": 84 } ] }
```

| Field | Required | Meaning |
|---|---|---|
| `built` | yes | Date the data was prepared, `YYYY-MM-DD`. |
| `datasets[].key` | yes | The cohort's folder name. Unique. |
| `datasets[].name` | yes | Short name shown in the cohort picker. |
| `datasets[].fullName`, `description` | no | Shown on the site. |
| `datasets[].variables`, `files` | yes | Must equal the manifest's `counts`. |

Cohorts appear in the picker in this order. On a first visit the first one opens.

## `<key>/manifest.json`

```json
{ "key": "bcs70", "name": "BCS70", "fullName": "1970 British Cohort Study",
  "description": "…", "identifier": "bcsid",
  "ukdsUrl": "https://…", "built": "2026-10-09",
  "wave": { "term": "sweep", "plural": "sweeps",
            "list": [ { "key": "0y", "label": "Birth, 1970" } ] },
  "levels": ["NOMINAL", "ORDINAL", "SCALE"],
  "files": [ { "name": "bcs1derived", "wave": "0y", "study": "2666",
               "description": "Derived Variables for the Birth Sweep Data", "hasId": true } ],
  "counts": { "variables": 32452, "files": 84 },
  "topics": { … } }
```

| Field | Required | Meaning |
|---|---|---|
| `key` | yes | Same as the folder name. |
| `name`, `fullName` | yes | Shown on the site. |
| `description` | no | One or two sentences about the study. |
| `identifier` | yes | The participant identifier column. Every download includes it and joins on it. Matched ignoring case. |
| `ukdsUrl` | no | Where researchers get the data; linked from the download page. |
| `built` | no | Shown in the footer. |
| `wave.term`, `wave.plural` | yes | What a collection round is called ("sweep", "sweeps"). |
| `wave.list` | yes | Sweeps **in time order**: `key` (short and unique, e.g. `16y`) and `label`. A last entry such as `xwave` can hold files that span sweeps. |
| `levels` | no | Measurement level names, referred to by index from `index.json`. |
| `files[].name` | yes | The data file's name without extension: letters, digits, `_`, `.`, `-`. Unique. The generated scripts find the file by this name in any format. |
| `files[].wave` | yes | One of the `wave.list` keys. |
| `files[].study`, `description` | no | UK Data Service study number and a description. |
| `files[].hasId` | yes | `true` exactly when the file's dictionary has the identifier. Variables in files without it cannot be selected. |
| `counts` | yes | `variables` = rows in `index.json`; `files` = entries in `files`. |
| `topics` | no | The topic scheme (below). Leave it out and the site hides every topic feature. |

### Topic scheme

```json
"topics": { "name": "CLOSER topics", "version": 1, "hash": "c87a35ec8bc2",
            "domains": [ { "id": "health_behaviour", "label": "Health behaviour",
                           "description": "…",
                           "topics": [ { "id": "smoking", "label": "Smoking",
                                         "description": "…" } ] } ] }
```

Two levels: domains (topic areas) and their topics. Every `id`, domain or topic, must be unique
within the scheme. `name`, `version` and `hash` identify the scheme; the site does not use
them. Topics are numbered across the whole scheme in order (the first domain's topics, then
the second's, and so on), and `index.json` refers to them by that number.

## `<key>/index.json`

One row per variable, in the order the site lists them:

```json
[ ["BD1AGEFB", "1970: Age of mother at first birth", 0, 0, 2, [12, 90, 3, 55]] ]
```

| Position | Meaning |
|---|---|
| 0 | Variable name. Not empty. Must exist, spelled exactly the same, in the file's dictionary. |
| 1 | Label, `""` if none. |
| 2 | File: index into `manifest.files`. |
| 3 | Sweep: index into `manifest.wave.list`. |
| 4 | Measurement level: index into `manifest.levels`, or `-1` if not recorded. |
| 5 | Optional topics: flat `[topic, percent, topic, percent, …]`, strongest first. `topic` is the scheme-wide topic number; `percent` is 0–100. |

## `<key>/dict/<file>.json`

One per entry in `manifest.files`, named after it:

```json
{ "file": "bcs1derived", "wave": "0y",
  "variables": [ { "variable": "BD1MAGE", "label": "…", "pos": "4", "type": "numeric",
                   "measurement": "SCALE", "missing": "-999.0 thru -1.0",
                   "na": { "values": [], "ranges": [[-999, -1]],
                           "kept": [[-1, "Dislike"]], "lossy": [] },
                   "values": [ { "value": "-92.0", "label": "Refused" } ],
                   "topics": [ ["smoking", 0.9] ] } ] }
```

`file` and `wave` must match the manifest. Variable names must be unique within a file, ignoring
case. Only `variable` is required on each variable. Any other field may be left out or set to
`null`.

| Field | Meaning |
|---|---|
| `label` | The variable label. |
| `pos`, `type`, `measurement` | Position in the file, storage type, measurement level. Shown in the details. |
| `missing` | The dictionary's own missing-value text, shown as is. |
| `values` | Value labels: `value` and `label`, both strings. |
| `na` | Missing-value codes. See below. |
| `topics` | Topic tags: `[topic id, confidence]`, the id from the scheme and the confidence between 0 and 1. |

### Missing codes (`na`)

The site and the generated scripts use `na` exactly as supplied. They never work codes out for
themselves.

| Field | Meaning |
|---|---|
| `values` | Single codes that mean "missing", e.g. `[-9, -8]`. Required within `na`. |
| `ranges` | Ranges of codes as `[low, high]`, inclusive. `null` is an open end: `[null, -1]` is every code up to -1. `low` must not be above `high`. Required within `na`. |
| `kept` | Optional. `[code, label]` pairs: negative codes that are real answers (e.g. `[-1, "Dislike"]`). Never converted, so they should sit outside `values` and `ranges`. |
| `lossy` | Optional. `[code, label]` pairs: declared missing codes whose label reads like an answer. They are converted like any other code, and the site marks them with a warning. |

When a researcher asks for missing codes to become NA, exactly the `values` and `ranges` are
converted, and nothing else. A variable with no `na` (or `na: null`) has nothing converted.

## Checking the data

The checks run in CI on every pull request, and publishing waits for them. To run them
yourself:

```sh
uv run pytest tests/python/data
```

Each problem is listed as `<file>[: <location>]: <message>`, for example:

```text
bcs70/index.json: row 12 (BD1AGEFB): file index 90 is out of range (0-83)
```

All problems are listed in one run. The rules:

| Rule | Checks |
|---|---|
| D1 | Every file is UTF-8 JSON of the shape above, with required fields present and of the right type. |
| D2 | `datasets.json` keys are unique and well formed, each has `<key>/manifest.json` and `<key>/index.json`, and its counts match the manifest. |
| D3 | The manifest's `key` matches its folder. Sweep keys are unique and not empty. File names are unique and well formed. Each file's sweep is declared. `counts` match `index.json` and `files`. |
| D4 | Index rows have a name, file, sweep and level indices in range, and topics in pairs with topic numbers in range and percents 0–100. |
| D5 | Every manifest file has its dictionary, whose `file` and `wave` match. Every index row's variable is in that dictionary. Variable names are unique per file, ignoring case. |
| D6 | `values` entries have `value` and `label` strings. `na` has numeric `values`, `ranges` of `[low, high]` with `low ≤ high`, and `kept`/`lossy` as `[code, label]` pairs. |
| D7 | Scheme ids are unique. Every topic tag names a topic in the scheme, with a confidence from 0 to 1. |
| D8 | `hasId` is true exactly when the file's dictionary has the identifier (ignoring case). |

The checks live in `tests/python/data/checks.py`. A change to this format is a change to
`specs/001-cohort-data-builder/contracts/site-data.md`, this page and the checks, together.

## Adding or updating a cohort

1. Branch from the integration branch, e.g. `git switch -c data-add-mcs 001-cohort-data-builder`.
2. Put the cohort's folder in `site/data/<key>/`, containing `manifest.json`, `index.json` and
   `dict/`. To update a cohort, replace its folder.
3. Add or update its entry in `site/data/datasets.json`, with counts matching the manifest.
4. Run `uv run pytest tests/python/data` and fix anything it lists.
5. Run `uv run python -m http.server -d site 8000`, open `http://localhost:8000/#<key>`, and
   check that the cohort opens and a search finds its variables.
6. Open a pull request. Once it is merged and reaches `main`, the site is republished
   automatically.

No code changes are needed. The site lists whatever `datasets.json` lists.
