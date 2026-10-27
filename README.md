# Cohort Data Builder

Search the variables of UK longitudinal cohort studies, pick the ones you need, and download
a small R and/or Python project that merges them from your own copy of the data into one
file, one row per participant.

It starts with the 1970 British Cohort Study (BCS70, 32,452 variables) and Next Steps
(11,430). It is a static site on GitHub Pages: everything runs in your browser, with no
accounts and no server.

**The site and the download contain no study data.** They hold only the published data
dictionaries: names, labels, value labels, missing codes and topics. You get the data itself
from the [UK Data Service](https://ukdataservice.ac.uk/) and place it in the downloaded
project.

> Beta: check anything you rely on against the UK Data Service documentation, and
> [report problems](https://github.com/CLS-Data/cohort-data-builder/issues).

## Using it

1. Choose a cohort. Search by any part of a variable's name or label, and narrow by sweep,
   file, measurement level or topic. Open a variable with ▸ to see its value labels, missing
   codes, topics and the same question at other sweeps.
2. Click variables to select them (Shift-click for a range). The selection is kept in your
   browser, per cohort.
3. Open **Selection**: check or rename the output columns, choose R and/or Python, CSV, Stata
   or SPSS output, and whether missing codes become NA. Then download.
4. Unzip, put the data files listed in its README into `data/` (any of `.tab`, `.csv`,
   `.dta`, `.sav`, in any subfolder), and run `R/merge.R` or `python/merge.py`.

## Topic tagging

Cohorts often arrive without topics. The [Topic Tagger](tools/topic-tagger/README.md) in
`tools/topic-tagger/` assigns them with a language model run by the maintainer through
Ollama, with live progress and an HTML report. It is a self-contained tool, usable outside
this project. `scripts/topics.py` exports a cohort from `site/data` for it and merges the
tags back; [docs/data-format.md](docs/data-format.md#adding-topics) has the three commands.

## Repository layout

```text
site/                 the published site (static files only)
  index.html, styles.css
  js/core/            logic with no DOM: search, selection, topics, code generation, zip
  js/ui/              the views
  templates/          the R and Python project templates for the download
  data/               supplied cohort data (see docs/data-format.md)
tests/
  js/                 Node tests for site/js/core
  python/data/        supplied-data checks (rules D1–D8)
  python/generated/   runs the generated R and Python on fabricated data
  python/e2e/         browser tests (Playwright), accessibility, phone width, speed
  fixtures/data/      a tiny fictional cohort used by the tests
tools/topic-tagger/   the Topic Tagger, a standalone Python tool
scripts/              topics.py (export/merge for the tagger) and checks.py (data checks)
docs/data-format.md   the supplied-data format, for the data team
specs/                the specification, plan and task list
```

## Setup

You need [uv](https://docs.astral.sh/uv/) and Node.js 22 or later. R with the `haven` package
is optional; it is needed only for the tests that run the generated R.

```sh
uv sync                              # Python 3.12 and the dev tools
uv run playwright install chromium   # browser for the browser tests
npm ci                               # Biome
```

## Running locally

```sh
uv run python -m http.server -d site 8000
```

Then open <http://localhost:8000/>.

## Running every check

These are the checks CI runs:

```sh
uv run pytest tests/python/data                       # supplied data matches the format
uv run ruff check . && uv run ruff format --check .   # Python lint and format
npm run lint                                          # JavaScript lint and format (Biome)
npm test                                              # JavaScript core tests
uv run pytest                                         # all Python, generated-script and browser tests
```

Without R, the generated-R tests are skipped locally. CI sets `CDB_REQUIRE_R=1`, which makes
a missing R a failure. See `specs/001-cohort-data-builder/quickstart.md` for a full
walkthrough.

## Adding or updating cohort data

The data team supplies each cohort ready to use. Put its folder in `site/data/<key>/`, add it
to `site/data/datasets.json`, and run `uv run pytest tests/python/data`. No code changes are
needed. [docs/data-format.md](docs/data-format.md) has the format, the checks and the steps.

## Deploying

A push to `main` runs every check and then publishes `site/` to GitHub Pages
(`.github/workflows/pages.yml`). This needs a one-time setting: **Settings → Pages → Source →
GitHub Actions**. The site uses only relative URLs, so it works under
`https://<owner>.github.io/<repo>/`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md): a short branch per change, the failing test committed
before the code, Conventional Commits, and a pull request with a "How to review" section.
