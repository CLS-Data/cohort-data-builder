# Quickstart: checking the updates from user testing

## Setup

```sh
uv sync && uv run playwright install chromium && npm ci
uv run python -m http.server -d site 8000      # then open http://localhost:8000/
```

For the Stata check, Stata 16+ must be installed. If it is not on the usual path, set
`CDB_STATA` to its binary, e.g.
`export CDB_STATA=/Applications/StataNow/StataMP.app/Contents/MacOS/stata-mp`.

## Automated

```sh
npm test                                             # do-file text, tag-suggestion URL
uv run pytest tests/python/e2e/test_us2_selection.py # one list, download in view
uv run pytest tests/python/e2e/test_us3_download.py  # Stata option in the zip
uv run pytest tests/python/generated                 # R, Python and (if found) Stata agree
uv run pytest                                        # everything
```

Expected: all pass. Without Stata, the Stata comparison shows as skipped, never failed.

## By hand

1. **One list** (US1): select 3 variables, open **Selection**. Each appears once. Rename
   one; remove another with ✕ → it leaves the list and the Selection count drops.
2. **Download in view** (US2): select 80 variables (search a common word, **Select all**),
   open **Selection** in a 1366×768 window. The options and **Download** are visible; only
   the list scrolls. Shrink to phone width → the download bar sticks to the bottom and
   **Download options** opens the options.
3. **Stata** (US3): tick **Stata** only, download, unzip. Put the fixture data in `data/`,
   run `stata-mp -b do stata/merge.do` from the project folder → `output/merged.dta`
   matches what `Rscript R/merge.R` writes.
4. **Tag suggestion** (US4): open any variable's details, click **Suggest a tag change** →
   a new tab opens GitHub's new-issue form with cohort, variable, file, label and current
   tags filled in, labelled `tag-suggestion`. The builder tab is unchanged.

See [contracts/](contracts/) for exact structure and behaviour.
