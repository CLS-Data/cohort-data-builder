# Data Model: Cohort Data Builder

Entities from the [spec](spec.md). All cohort entities are **supplied** by the data team in
the format in [contracts/site-data.md](contracts/site-data.md) and are read-only to the
project; only the Selection and settings are created by the site. Nothing here is study
data.

```text
Cohort 1──* Sweep
Cohort 1──* DataFile *──1 Sweep
DataFile 1──* Variable 1──* ValueLabel
Variable 1──1 MissingCodes
Variable 1──* TopicTag *──1 Topic *──1 TopicArea   (Cohort 0..1──1 TopicScheme)
Selection *──1 Cohort;  Selection 1──* SelectedVariable *──1 Variable
GeneratedProject  = Selection + DownloadOptions + Cohort data
```

## Cohort

Supplied in `datasets.json` and `<key>/manifest.json`.

| Field | Type | Rules |
|---|---|---|
| key | string | `^[a-z][a-z0-9_]*$`; unique; equals its folder. |
| name, fullName, description | string | `name` required. |
| identifier | string | Required; compared ignoring case. |
| ukdsUrl | URL | Optional. |
| wave.term / wave.plural | string | e.g. `sweep` / `sweeps`. |
| wave.list | Sweep[] | At least one, in time order. |
| levels | string[] | Measurement levels; index used by `index.json`. |
| counts | {variables, files} | Must match `index.json` and `files`. |

## Sweep

| Field | Type | Rules |
|---|---|---|
| key | string | Unique within cohort (e.g. `16y`, `xwave`). |
| label | string | Optional (e.g. `Age 16, 1986`). |

List position is the sweep's position on every axis.

## DataFile

| Field | Type | Rules |
|---|---|---|
| name | string | `^[A-Za-z0-9][A-Za-z0-9_.\-]*$`, no extension; unique within cohort. |
| wave | Sweep.key | Must be declared. |
| description, study | string | Optional. |
| hasId | bool | True exactly when its dictionary contains the identifier. |

Variables in a file with `hasId = false` are searchable but not selectable.

## Variable

Summary row in `index.json`; full entry in `dict/<file>.json`.

| Field | Type | Rules |
|---|---|---|
| variable | string | Non-empty; unique within file ignoring case. |
| label | string | May be empty. |
| pos, type, measurement, missing | string | Optional; shown in details. |
| values | ValueLabel[] | Optional. |
| na | MissingCodes | Optional; absent = no codes. |
| topics | [topicId, confidence][] | Optional. |

Identity: (`DataFile.name`, `Variable.name`).

## ValueLabel

`{ value: string, label: string }`; `value` is numeric where parseable (e.g. `-9.0`).

## MissingCodes (supplied, used verbatim)

| Field | Type | Meaning |
|---|---|---|
| values | number[] | Codes converted to NA when asked. |
| ranges | [lo\|null, hi\|null][] | Ranges converted; null = open end; lo ≤ hi. |
| kept | [code, label][] | Negative codes that are answers: never converted; shown in details and codebook. |
| lossy | [code, label][] | Converted, but flagged ⚠ in details as losing an answer. |

## TopicScheme, TopicArea, Topic, TopicTag

Scheme in `manifest.topics` (absent = cohort untagged; topic features hidden).

| Entity | Fields | Rules |
|---|---|---|
| TopicScheme | name, version, hash, domains | |
| TopicArea | id, label, description, topics | id unique. |
| Topic | id, label, description | id unique across the scheme. |
| TopicTag | topic, confidence | Topic in scheme; 0 ≤ confidence ≤ 1 (percent 0–100 in index). |

## Selection and SelectedVariable (browser only)

`localStorage` key `cohort-data-builder:<cohortKey>:selection`.

| Field | Type | Rules |
|---|---|---|
| name, file | string | Must resolve in current data; dropped on restore if not. |
| label, wave | string | Copied for display. |
| column | string | Output name: unique ignoring case, ≠ identifier, `^[A-Za-z][A-Za-z0-9_.]*$`. |

Default column: sanitised variable name; if taken `<name>_<sweep>`; then `_<n>` from 2.
Blocking format rules: Stata — `^[A-Za-z_][A-Za-z0-9_]*$`, ≤ 32 chars; SPSS — ≤ 64 chars,
no trailing `.`.

## DownloadOptions and settings (browser only)

`localStorage` key `cohort-data-builder:_site:options`.

| Field | Values | Default |
|---|---|---|
| languages | non-empty subset of {r, python} | both |
| outputFormat | csv \| dta \| sav | csv |
| missingToNa | bool | false |
| minConf | 30 \| 50 \| 70 \| 90 | 50 |
| gridOpen, gridShade, panelOpen, panelGroup | UI preferences | closed, row, closed, wave |

## GeneratedProject

Built in the browser; see [contracts/download-project.md](contracts/download-project.md).
Named `<cohortKey>-merge-<YYYY-MM-DD>`.
