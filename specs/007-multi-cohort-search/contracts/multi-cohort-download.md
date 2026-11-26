# Contract: multi-cohort download

Extends [download-project.md](../../001-cohort-data-builder/contracts/download-project.md).

## One cohort in the selection

Exactly today's project and zip name, `<key>-merge-<date>.zip` (FR-024).

## Several cohorts

```text
cohorts-merge-<YYYY-MM-DD>/
  README.md                       NEW: from site/templates/cohorts-README.md
  ncds-merge-<YYYY-MM-DD>/        the single-cohort NCDS project, unchanged
  bcs70-merge-<YYYY-MM-DD>/       the single-cohort BCS70 project, unchanged
```

Zip name: `cohorts-merge-<YYYY-MM-DD>.zip`. Cohort folders in catalogue order.

Every file under `<key>-merge-<date>/` is byte-identical to the file at the same path in
that cohort's own download for the same variables, column names and options (SC-005). The
options (languages, output format, missing values) are the same for every folder (FR-022).

## Top-level `README.md`

Placeholders filled by `buildBundle`:

| Placeholder | Value |
|---|---|
| `{{created}}` | date |
| `{{count}}` | `5 variables from 2 cohorts` |
| `{{cohorts}}` | one line per cohort: `- **NCDS** (National Child Development Study): 3 variables, in \`ncds-merge-<date>/\`` |
| `{{languages}}` | as in the single-cohort README |

Fixed text says: each folder is a complete project; put each cohort's data in that folder's
`data/` (see its `data/README.md`); run each folder's code on its own; each produces that
cohort's merged dataset, keyed on its own identifier; **the cohorts are different people
and are not merged with each other**; harmonising variables across cohorts is up to the
researcher (FR-023).

## `buildBundle`

```text
buildBundle(projects, templates, options, today) -> {name, files}
  projects: [{selection, manifest, dicts}]   catalogue order, each selection non-empty
```

One project → `buildProject(...)` result. Several → files of each `buildProject` result
prefixed with `cohorts-merge-<date>/`, plus the README. Throws if `projects` is empty.
