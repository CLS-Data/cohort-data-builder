# Research: Updates from user testing

Decisions made before design, one per open question in the plan's Technical Context.

## R1. Which Selection list stays

- **Decision**: Keep the right-hand column list (`#basket-detail` → "Columns") and remove
  the left pane (`#basket-list`, its grip and the two-pane layout). Each column row gains
  the ✕ remove button the left list had. The Selection tab still accepts dropped variables
  (the drop target moves from the left pane to the whole view).
- **Rationale**: The column list already carries what the left list lacks (rename, the
  name-clash and invalid-name messages, file order), so only "remove" has to move. Keeping
  the left list instead would mean moving rename and the problem messages into it.
- **Alternatives considered**: Keep the left list and make the right pane options-only:
  rejected, it moves more code and loses the column order the files are written in.

## R2. Keeping the download in view

- **Decision**: On screens at least 1024×700 the Selection view becomes a fixed-height
  layout (the same `100dvh` technique the Variables view already uses): a header, then a
  scrolling column list, then a download area pinned at the bottom of the view, holding
  the options and the button. The "Data files it needs" list moves into the scrolling
  area, above the columns. Below that size (phones, short windows) the page scrolls as a
  whole and the download area is `position: sticky; bottom: 0`, with the options folded
  behind a "Download options" disclosure so the bar stays short.
- **Rationale**: Uses layout the Variables view already has (no new technique); sticky
  bottom keeps the button reachable on a phone without trapping the list in a tiny box.
- **Alternatives considered**: A floating "Download" button that scrolls to the options:
  still makes users scroll to change options. A modal for options: an extra step for
  everyone.

## R3. Stata as a code language

- **Decision**: Add a third language, `stata`, with two templates in
  `site/templates/stata/`: `load_data.do` (find files under `DATA_DIR`, read by
  extension, normalise the identifier, apply missing codes, write output) and `merge.do`
  (settings, selection, labels and the merge), mirroring `r/merge.R` and `r/load_data.R`.
  `codegen.js` fills it like the other two. Target Stata 16 or later, the first version with
  `import spss`; no user-written packages.
- Reading: `.dta` → `use`; `.csv`/`.tab` → `import delimited` (tab delimiter for `.tab`);
  `.sav` → `import spss`.
- Missing codes: values and ranges become `.` with `replace … if inlist()/inrange()`; open
  ends use `<=`/`>=`.
- Identifier: trimmed (`strtrim`) and matched case-insensitively to the configured name, as
  in R and Python.
- Several rows per person: detected with `duplicates report`/`isid`, written to
  `<file>_long`, skipped from the merge.
- Merge: successive `merge 1:1 id using`, keeping all rows (`drop _merge`), from
  `tempfile`s.
- Output: `csv` → `export delimited`; `dta` → `save`; `sav` → Stata cannot write SPSS files,
  so the do-file writes `.dta` and prints a note, and the README says so.
- Labels: `label variable` and `label define`/`label values` from the same `LABELS` and
  `VALUE_LABELS` data, as for R and Python.
- **Rationale**: The same structure as R/Python keeps the three in step and lets one test
  compare their output. Templates stay reviewable as Stata.
- **Alternatives considered**: A single short "boilerplate" do-file that only `use`s and
  `merge`s: does not handle `.tab`/`.sav` inputs, missing codes or long files, so it would
  give different data from R/Python (fails FR-008).

## R4. Testing Stata code without Stata in CI

- **Decision**: Two levels.
  1. Node unit tests (in CI) on the generated do-file text: the selection, missing codes,
     labels and settings are filled in and correctly quoted, for every option combination.
  2. A `needs_stata` generated-script test that runs the do-file in batch mode on the
     fabricated fixture data and compares its output with the R and Python output. It
     finds Stata through `CDB_STATA` or the usual install paths (e.g.
     `/Applications/StataNow/StataMP.app/Contents/MacOS/stata-mp`) and skips when none is
     found. Unlike `needs_r`, CI does not set a "require" flag, because Stata is licensed
     and cannot be installed on GitHub runners.
- **Rationale**: The constitution requires automated tests in CI; level 1 runs there.
  Running real Stata is the only true check of FR-008, so level 2 runs wherever Stata is
  installed, including the maintainer's machine, and the pull request's "How to review"
  asks the reviewer to run it.
- **Alternatives considered**: Parsing do-files with a third-party Stata parser: none is
  maintained or complete enough to trust. Running Stata in CI with a licence secret:
  licence terms and cost; recorded as a possible later change.
- This is a deviation from "tests MUST run in CI" for one test; it is recorded in the
  plan's Complexity Tracking.

## R5. Suggesting a tag change

- **Decision**: A "Suggest a tag change" link in each variable's details (next to its
  topics, or alone when it has none). It opens
  `https://github.com/CLS-Data/cohort-data-builder/issues/new?template=tag-suggestion.yml&…`
  in a new tab, with fields pre-filled from URL parameters. A new issue form,
  `.github/ISSUE_TEMPLATE/tag-suggestion.yml`, defines the fields (cohort, variable,
  file, label, current tags, suggested tags, why) and applies the `tag-suggestion` label.
  The URL is built by a new pure function in `site/js/core/feedback.js`, unit-tested
  under Node; the link is a plain `<a target="_blank" rel="noopener">`.
- **Rationale**: Issue forms apply their labels for any user; a `labels=` URL parameter is
  ignored for people without triage access, so FR-012 needs the form. Pre-filling form
  fields by id is supported by GitHub. No backend, so it stays a static site
  (Principle III). The repository URL is already public in the page's footer and beta bar.
- Long values: the URL is kept under 8,000 characters by truncating the label and the tag
  list (keeping cohort, variable and file whole).
- **Alternatives considered**: A `mailto:` link: no labels, harder to track. A form posting
  to a third-party service: a backend the project does not own, and data leaving GitHub.

## R6. Where the repository URL lives

- **Decision**: One exported constant, `REPOSITORY`, in `site/js/core/feedback.js`, used
  by the tag link. The footer and beta-bar links in `index.html` stay as they are.
- **Rationale**: Simplest change; a fork changes one constant (and is told so in its doc
  comment).
- **Alternatives considered**: A `repository` field in `datasets.json`: changes the data
  contract for one link.
