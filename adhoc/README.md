# Ad hoc: CLS metadata to site data

A one-off pipeline that turns the CLS studies metadata CSV into the site's data format
(`docs/data-format.md`), with topics from the Topic Tagger. It is not part of the site
or the tool. Data files never leave `data/` and are never committed.

```text
data/raw/          CLS_studies_metadata.csv, as supplied
data/staging/      one folder per cohort: everything the CSV says, worked out, plus tags
data/processed/    the finished cohorts, laid out like site/data
cohorts.json       names, descriptions, identifier and UKDS link for each study
```

## 1. Stage

```sh
uv run python adhoc/stage.py
```

Writes `data/staging/<key>/` for `ncds`, `bcs70`, `next_steps` and `mcs`, and
`data/staging/report.md` (read it). Each variable keeps its whole CSV row, including the
human-assigned research topic and subtopic. What is worked out:

- **Sweeps:** keys `s0`, `s6_1`, …, cross-sweep `xwave` last; labels like
  "Sweep 6.1: age 44/45, 2002/04".
- **Value labels:** split from `value_labels_to_2000_chars`. A list the CSV cut off
  ("… AND MORE") loses its last label and is marked `valuesCut`.
- **Missing codes:** negative codes whose label reads as missing ("Not applicable",
  "Refusal", …) become `na.values`. Other negative codes are `kept`: they are never
  converted. The report lists the commonest kept labels.
- **From the live site:** where `site/data` already has a variable (BCS70 and Next
  Steps), its type, measurement level, value labels and missing codes come from there,
  since they were read from the data files.
- **Identifier:** the CSV lists none. Files on the live site say whether they hold it;
  every other file is assumed to.
- **Files spelled two ways** (differing only in case) are one file.

## 2. Tag (by hand)

For each cohort, from `tools/topic-tagger/`:

```sh
uv run topic-tagger init-scheme ../../adhoc/scheme.toml     # once; edit it if you like
uv run topic-tagger tag ../../adhoc/data/staging/<key>/tagger/variables.jsonl \
  --out ../../adhoc/data/staging/<key>/tags --scheme ../../adhoc/scheme.toml \
  --model gpt-oss:20b-cloud
```

Stop it at any time; the same command carries on. Check each `tags/report.html`.
At about 100–140 variables a minute, all four cohorts take 14–19 hours.

## 3. Build

```sh
uv run python adhoc/build.py
```

Rebuilds `data/processed/` from staging, merges each cohort's tags if it has any (a
cohort without them is built without topics), and runs the site's data checks. Exits 1
if they find problems. Besides the documented fields, each variable keeps `question`,
`human` (the CSV's topics) and `clsId`, and each file its `licence`, `category` and
`ukdsDeposit`.

To publish, copy `data/processed/` over `site/data/` and continue from step 4 of
"Adding or updating a cohort" in `docs/data-format.md`.

## Tests

```sh
uv run pytest adhoc/tests
```
