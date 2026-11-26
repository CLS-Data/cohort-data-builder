# Contract: the Variables view with several cohorts

With one cohort chosen, everything below collapses to today's view (FR-005): no cohort
headings, no sub-rows, sweeps as columns.

## Overview

Sketch; the names, ages and counts are illustrative, not real.

```text
● NCDS  National Child Development Study — 1958 … 30,112 variables in 61 files.
● BCS70 1970 British Cohort Study — … 32,452 variables in 84 files.

              age  0   7   10  11  16  23  26  …  ?
NCDS   4,210       ▇   ▅       ▆   ▇   ▆           
BCS70  3,118       ▆       ▇       ▆       ▅      ▂
▸ Topics …
  Smoking      412
    NCDS       230 ░   ░       ▒   ▓   ▓
    BCS70      182 ░       ▒       ▓       ▓
```

- One description line per chosen cohort (FR-011), catalogue order, with its mark.
- One sweep row per chosen cohort: label = mark + short name + total (FR-012); columns from
  the age axis (research R2, FR-012a); `?` = "age not known" column, only when needed.
- Bar button: `data-cohort`, `data-wave`; title `<cohort> <sweep key> (age <age>) — n
  variables`. Click sets `waveFilter = {cohort, i}`; chip reads `NCDS · 11y ✕` (FR-007).
- Empty cohort: row shown, total `0`, empty cells (FR-013). Loading: `Loading NCDS…`.
  Failed: message and Retry button.
- Topic and domain rows: total across chosen cohorts; beneath, one sub-row per chosen cohort
  with mark, short name, total and cells on the same columns (FR-014). Untagged cohort:
  sub-row reads "no topic tags" in place of cells (FR-015). Shading "within topic" scales
  each sub-row to its own busiest cell; "across topics" uses one scale for all.
- The chart region scrolls sideways inside itself when narrower than its columns, with row
  labels pinned; the page never scrolls sideways.

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
