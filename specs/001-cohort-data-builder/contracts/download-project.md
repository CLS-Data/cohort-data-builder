# Contract: Downloaded project

What the researcher receives (FR-019–FR-028). Behaviour matches `PoC/templates/` and
`PoC/site/js/codegen.js`.

## Layout

```text
<key>-merge-<YYYY-MM-DD>/
  README.md               which files to get, how to run, what you get
  codebook.csv            one row per output column (identifier first)
  data/README.md          where the data files go
  <project>.Rproj         R only
  R/load_data.R           R only
  R/merge.R               R only: settings, selection, merge
  python/load_data.py     Python only
  python/merge.py         Python only
  python/requirements.txt Python only
```

Zip name: `<key>-merge-<YYYY-MM-DD>.zip`.

## `codebook.csv`

Header: `column,variable,file,wave,label,missing_codes,negative_kept,value_labels,topics`.
First row is the identifier. `value_labels` and `negative_kept` are `code=label` joined by
`; `. `topics` is `Label (0.90)` joined by `; `. RFC 4180 quoting.

## Merge script settings (top of `merge.R` / `merge.py`, editable)

| Setting | Values |
|---|---|
| `DATA_DIR` | default `data` |
| `OUTPUT_DIR` | default `output` |
| `OUTPUT_FORMAT` | `csv`, `dta`, `sav` |
| `MISSING_TO_NA` | `TRUE`/`FALSE` (R), `True`/`False` (Python) |
| `IDENTIFIER` | cohort identifier |
| `SELECTION` | per file: `output_column = "source variable"` |
| `MISSING_CODES` | per column: values and ranges |
| `LABELS`, `VALUE_LABELS` | for Stata/SPSS output |

## Runtime behaviour

1. Index `DATA_DIR` recursively; find each file by base name ignoring extension; accepted
   extensions `.tab`, `.csv`, `.dta`, `.sav`.
2. If any file is missing: stop before reading, listing every missing file.
3. Per file: read identifier + selected columns only; identifier matched ignoring case and
   normalised (trimmed). Missing selected columns: warn and skip.
4. If `MISSING_TO_NA`: replace the column's listed values and ranges (copied verbatim from
   the supplied `na.values` / `na.ranges`) with NA; nothing else.
5. Drop exact duplicate rows; if identifier still repeats, write
   `output/<file>_long.<ext>` and exclude from the merge.
6. Full outer join remaining files on the identifier; write `output/merged.<ext>`.
7. Stata/SPSS: attach variable labels and whole-number value labels.
8. R and Python produce identical cell values and column order for the same input.

## Template placeholders

Templates live in `site/templates/` (same file names as the PoC's `templates/`) and are
fetched by the browser at download time. A test fails if any listed placeholder is missing.

| Template | Required placeholders |
|---|---|
| `r/merge.R`, `python/merge.py` | dataset, created, identifier, missing_to_na, selection, missing_codes, output_format, labels, value_labels |
| `README.md` | dataset, full_name, created, count, files, languages, contents, ext, format_note, identifier, ukds_url, missing_note, run |
| `data-README.md` | dataset, files, ukds_url |

All dictionary text inserted into code is escaped (backslash, double quote; newlines → space).
