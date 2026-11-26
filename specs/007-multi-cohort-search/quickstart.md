# Quickstart: validating multi-cohort search

## Setup

```sh
uv sync && uv run playwright install chromium && npm ci
uv run python -m http.server -d site 8000      # open http://localhost:8000/
```

## 0. Sweep ages of the real cohorts (first task, run by a person)

The planning session could not read `site/data/`. Run this and paste the output into the
task: it prints each cohort's sweep keys and any `age` already given.

```sh
uv run python -c "import json,pathlib; [print(p.parent.name, [(w['key'], w.get('age')) for w in json.loads(p.read_text())['wave']['list']]) for p in sorted(pathlib.Path('site/data').glob('*/manifest.json'))]"
```

Keys of the form `14y` or `9m` need nothing; any other key needs `age` added
([contracts/sweep-ages.md](contracts/sweep-ages.md)). The real cohorts' keys are not
age-shaped (research R1), but their labels carry the CLS metadata's age text, so:

```sh
uv run python scripts/sweep_ages.py site/data/bcs70 site/data/mcs site/data/ncds site/data/next_steps
# check the ages it lists, then the same again with --write
```

It lists the sweeps whose label gives no age; add `age` to those by hand.

## 1. Automated checks

```sh
npm test                                     # core: ages, cohorts, search, selection, codegen
uv run pytest tests/python/data              # supplied data, incl. new age checks
uv run pytest tests/python/e2e -k "multi or cohort or tutorial"
uv run pytest tests/python/generated         # bundle folders == single-cohort downloads
npm run lint && uv run ruff check . && uv run ruff format --check .
```

All pass. Single-cohort e2e tests (`test_us1_search.py` … `test_us4_topics.py`) pass
unchanged apart from the cohort selector.

## 2. By hand

| # | Do | Expect |
|---|---|---|
| 1 | Open `/` in a fresh profile | One cohort chosen, page as before (Q3, FR-005) |
| 2 | Press a second cohort in the header | It loads in under 3 s; one row of bars on an age axis, each bar stacked in both colours; results grouped under two headings, count split by cohort; hovering a toggle says what the cohort is; the title does not change |
| 3 | Search `smok` | Both groups narrow; a cohort with none shows "no matches" |
| 4 | Click a sweep bar of the second cohort | Only that cohort's sweep; chip names cohort and sweep |
| 5 | Open Topics → a domain | Each topic is one row of cells stacked by cohort; an untagged cohort is named above the rows |
| 6 | Select variables from both; open Selection | Grouped by cohort; button "Download N variables from 2 cohorts" |
| 7 | Give two cohorts' variables the same column name | No clash reported |
| 8 | Download, unzip | `cohorts-merge-<date>/README.md` and one complete project folder per cohort |
| 9 | Remove a cohort in the header | Its selection stays, marked "not being searched" |
| 10 | Reload; copy the address to a new tab | Same cohorts chosen |
| 11 | Try to un-press the last cohort | Nothing happens; title explains why |
| 12 | Choose all cohorts at 390px wide, dark theme, largest text | No page-level sideways scroll; chart scrolls in its box; colours and names readable |
| 13 | Open the tutorial | Intro lists cohorts in their colours; demo panels show two cohorts; download step shows the folder-per-cohort zip |
