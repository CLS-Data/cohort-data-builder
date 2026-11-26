# Data model: Search several cohorts at once

Browser-side shapes only; the supplied data changes only by the optional sweep age
([contracts/sweep-ages.md](contracts/sweep-ages.md)).

## Cohort (supplied, extended)

`data/datasets.json` entry plus `data/<key>/manifest.json`, as today, with:

| Field | Change |
|---|---|
| `manifest.wave.list[].age` | NEW, optional number: years at that sweep (months as fractions) |
| `manifest.wave.list[].ageRange` | NEW, optional `[min, max]` years |

Derived on the site, not stored:

| Derived | Rule |
|---|---|
| sweep age | `age`, else from key `<n>y` / `<n>m`, else unknown |
| colour token | pinned by key, else catalogue position mod 6 (research R9) |
| short name | `datasets.json` `name` (e.g. "BCS70") |

## Loaded cohort (`state.cohorts`)

`Map<key, LoadedCohort>`; a cohort enters when first chosen or when it has a saved
selection, and stays for the session.

```text
LoadedCohort {
  manifest, vars,                  as loaded today
  topics, domains,                 flattened scheme (empty when untagged)
  topicIndex: Map<id, index>,      topic and domain ids to this cohort's indices
  labelIndex,                      "same label" index, as today
  status: "loading" | "ready" | "failed", error?: string
}
```

## Cohort choice

`state.chosen: string[]`: cohort keys, always in catalogue order, length ≥ 1.

- Written to the page address as `#<key>+<key>…` and to storage as
  `cohort-data-builder:_site:cohorts` (an array).
- Read from the address first, then storage, then the old single-cohort key
  `cohort-data-builder:_site:cohort`, then the first catalogue cohort (clarification Q3).
  Unknown keys are dropped; if none remain, the first catalogue cohort.
- Transitions: add (load if needed, then search); remove (refused if it is the last; clears
  a sweep or file filter on that cohort; selection kept).

## Filters (`state`)

| Field | Scope | Shape |
|---|---|---|
| `query`, `levelFilter`, `topicMode` | all chosen cohorts | as today |
| `topicSel` | all chosen cohorts | `{kind: "d"\|"t", id}[]` (was `{kind, i}`) |
| `waveFilter` | one cohort | `{cohort, i}` or null (was index) |
| `fileFilter` | one cohort | `{cohort, i}` or null (was index) |
| `options.minConf` etc. | site | unchanged |

`levelFilter` is a level **name** across cohorts (each cohort's `levels` list may differ);
`-1` still means unrecorded.

## Search result (`state.results`)

```text
CohortResult { cohort, matches: row[], perWave: number[], perLevel, tally, untagged }
state.results: CohortResult[]  in chosen (catalogue) order
```

The list draws `results` concatenated, each group headed. Row key:
`<cohort>:<fileIndex>:<name>`.

## Age axis

```text
AgeAxis { columns: {age: number|null, label}[] }      null = "age not known", last
cohortRow(cohort) -> cells: (sweepIndex | null)[]     one per column
```

Built by `ageAxis(manifests)` from the chosen cohorts; with one cohort the columns are its
sweeps in manifest order (FR-012a). Two sweeps of one cohort with the same age (should not
happen) share a column, both counts summed, both keys in the tooltip.

## Selected variable

```text
{ cohort, name, label, file, wave, column }
```

`cohort` is new; `keyOf` is `<cohort>:<file>:<name>`. Stored per cohort without `cohort`
(storage unchanged); added on restore. Column problems are checked within a cohort.

## Selection

`state.bundles: Map<key, SelectedVariable[]>`, one per cohort with a selection, including
cohorts not chosen. Shown grouped by cohort (catalogue order), then sweep or file.

## Multi-cohort download

See [contracts/multi-cohort-download.md](contracts/multi-cohort-download.md). One cohort →
today's project. Several → `cohorts-merge-<date>/` holding `README.md` and one
`<key>-merge-<date>/` project per cohort.
