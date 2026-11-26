# Contract: the Variables view with several cohorts

With one cohort chosen, everything below collapses to today's view (FR-005): no cohort
headings, sweeps as columns, topic cells shaded.

## Overview

Sketch; the ages and counts are illustrative, not real. Each bar is stacked by cohort
(█ NCDS, ▒ BCS70), first cohort at the bottom.

```text
ALL VARIABLES 7,328   ▒        ▒   ▒       ▒
                      █   █    █   █   █   █
                      0   7   10  11  16  23 …  ?
▸ Topics …
  Smoking      412    ▁   ▂    ▃   ▄   ▆   ▅
```

- No description text (FR-011): what a cohort is shows in its header toggle's title.
- One row (FR-012): `#spine-track li[data-col=j]`, one per age-axis column (research R2,
  FR-012a); `?` = "age not known", only when needed. Each `button.node[data-col]` holds
  `.node-fill.is-stack` with one `.coh-seg[data-cohort][data-coh]` per cohort with matches
  there, `flex-grow` = its count, catalogue order bottom up.
- Bar title: `Age 11 — 4 variables: NCDS 3 (s2), BCS70 1 (s3)`. Click sets
  `waveFilter = {col, label, sweeps: {cohort: i}}`; chip reads `age 11 ✕`; again clears it.
  The age filter is dropped when the chosen cohorts change (the axis changes).
- Empty column: `is-empty` bar (FR-013).
- Topic and domain rows (FR-014): label and total across cohorts, then `.tg-cell.is-stack
  [data-col]` per column with `.tg-stack` of `.coh-seg`s; aria-label `Smoking at age 11: 3
  (NCDS 2, BCS70 1)`. Height scales "within topic" to the row's busiest cell, "across
  topics" to the busiest domain cell. Untagged cohorts: `X has no topic tags.` above the
  rows (FR-015).

## Filter bar and results

- Result count: `412 · NCDS 230 · BCS70 182`; each cohort part is a button that jumps to
  its group (FR-009).
- File filter chip names the cohort: `NCDS · ncds_2004 ✕`.
- Level dropdown: union of the chosen cohorts' level names, counts summed.
- Result list (FR-009a): a heading row per chosen cohort (`<li class="v-group"
  data-cohort>`: mark, full name, count or "no matches" / "no topic tags"), then that
  cohort's rows in today's order. Each row shows a cohort tag (mark + short name) before
  its sweep (FR-008). Row key `data-key="<cohort>:<fileIndex>:<name>"`. While a sweep or file filter on
  another cohort is active, a group heading reads "filtered to <cohort> · <sweep or file>"
  with a "Clear filter" button instead of "no matches".
- Details name the cohort in full; the tag-suggestion issue includes the cohort (already
  does via the manifest).
- "Select all": limit 500 across cohorts; the message gives per-cohort numbers.

## Selected panel and Selection view

- Groups: cohort heading (mark, name, count), then sweep or file as chosen (FR-018).
- A cohort not chosen in the header still shows its group, with "not being searched" beside
  its name (FR-017).
- Column-name problems are reported within a cohort (FR-019).
- Download button: `Download 5 variables from 2 cohorts` (FR-025); one cohort: as today.
