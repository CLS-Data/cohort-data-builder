# Contract: Stata in the downloaded project

Extends [001's download-project contract](../../001-cohort-data-builder/contracts/download-project.md).
Everything there still holds; this adds the Stata files.

## Layout (Stata chosen)

```text
<key>-merge-<YYYY-MM-DD>/
  README.md               now also says how to run the do-file
  codebook.csv            unchanged
  data/README.md          unchanged
  stata/load_data.do      Stata only: finding, reading, cleaning, writing
  stata/merge.do          Stata only: settings, selection, merge
  …                       R and Python files as before, when chosen
```

## How it is run

From the folder that holds `README.md`:

- Stata window: `cd` to that folder, then `do stata/merge.do`.
- Batch: `stata-mp -b do stata/merge.do` (or `stata-se`, `stata`).

Needs Stata 16 or later. No user-written packages.

## Settings (top of `merge.do`, editable)

| Setting | Stata form | Values |
|---|---|---|
| `DATA_DIR` | `local DATA_DIR "data"` | folder searched, with subfolders |
| `OUTPUT_DIR` | `local OUTPUT_DIR "output"` | |
| `OUTPUT_FORMAT` | `local OUTPUT_FORMAT "csv"` | `csv`, `dta`; `sav` writes `.dta` with a note |
| `MISSING_TO_NA` | `local MISSING_TO_NA 1` | `1` or `0` |
| `IDENTIFIER` | `local IDENTIFIER "PID"` | |
| Selection | one block per file: `local f1_file "mini_age5"`, `local f1_vars "sex smoke5"`, `local f1_cols "sex smoke5"` | source names and output names, in the same order |
| Missing codes | per column: values and ranges as `replace col = . if …` lines | from the dictionary's missing codes |
| Labels | `label variable` / `label define` lines | from `LABELS` / `VALUE_LABELS` |

## Behaviour (same as R and Python)

1. Every data file is located before any is read; missing files are listed and the do-file
   stops with `exit 601`.
2. Each file is read by extension (`.dta`, `.csv`, `.tab`, `.sav`); only the identifier and
   the selected variables are kept. A selected variable missing from the file is skipped
   with a warning; a missing identifier stops the run.
3. The identifier column is matched case-insensitively and trimmed of spaces.
4. Variables are renamed to their output columns; with `MISSING_TO_NA` on, missing codes
   become `.`.
5. Exact duplicate rows are dropped. A file still having several rows per person is written
   to `output/<file>_long.<ext>` and left out of the merge.
6. The rest are merged one-to-one on the identifier, keeping everyone in any file, and
   written to `output/merged.<ext>` with variable and value labels (`dta`).
7. For the fixture data and the test selection, `output/merged` has the same rows,
   columns and values as the R and Python output (compared after sorting by identifier).
