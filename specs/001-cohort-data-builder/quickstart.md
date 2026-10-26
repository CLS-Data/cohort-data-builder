# Quickstart: validating Cohort Data Builder

How to prove the feature works end to end. Formats are in [contracts/](contracts/);
entities in [data-model.md](data-model.md).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 and all Python test tooling)
- Node.js 20 or later (JavaScript tests, Biome, download generation in tests)
- Optional, for the generated-R tests: R with the `haven` package

## Setup

```sh
uv sync                              # Python and dev tools
uv run playwright install chromium   # browser for end-to-end tests
npm ci                               # Biome only
```

## 1. Quality gates (what CI runs)

```sh
uv run pytest tests/python/data      # supplied data matches the format: all pass
uv run ruff check . && uv run ruff format --check .
npx biome ci site tests/js
node --test tests/js/
uv run pytest                        # everything: data, generated scripts, browser, axe
```

Expected: every command exits 0. Without R/haven locally, generated-R tests report as
skipped; in CI they must run.

## 2. Browse (User Stories 1, 2, 4)

```sh
uv run python -m http.server -d site 8000
```

Open <http://localhost:8000/#bcs70>, then:

1. The header shows "BCS70", 32,452 variables, 84 files; 14 sweeps in order.
2. Search `smok`: matches highlighted; click the `16y` sweep → only 16y rows.
3. Open a result's details: answers before missing codes; file and topics shown.
4. Click three results, Shift-click a fourth further down: the range is added and announced.
5. Reload: the selection is still there.
6. Open Topics, pick two topics, switch to "all": fewer results, each tagged with both.

## 3. Download and run (User Story 3)

1. Select one variable from a one-row-per-person file and one from a household grid file;
   choose R + Python, CSV, missing codes → NA; download.
2. Unzip; put fabricated or real data files in `data/`.
3. `Rscript R/merge.R` and `python python/merge.py`.

Expected: `output/merged.csv` with the identifier first, one row per person; the grid file in
`output/<file>_long.csv`; R and Python outputs identical. Removing a data file makes both
scripts stop and name it before reading anything.

Automated: `uv run pytest tests/python/generated`.

## 4. Sub-path deployment (Principle III)

```sh
mkdir -p "$TMPDIR/pages" && ln -s "$PWD/site" "$TMPDIR/pages/cohort-data-builder"
uv run python -m http.server -d "$TMPDIR/pages" 8001
```

<http://localhost:8001/cohort-data-builder/> loads and searches normally. Automated in the
browser tests.

## 5. Adding supplied data (User Story 5)

1. Copy a supplied cohort folder into `site/data/<key>/` and add its entry to
   `site/data/datasets.json`.
2. `uv run pytest tests/python/data` → all pass (or each problem listed with file and
   location).
3. Serve the site: the cohort appears in the picker.

## 6. Deployment

Push to `main`: the **Pages** workflow runs every gate above, then publishes `site/`.
Requires Settings → Pages → Source → **GitHub Actions**.
