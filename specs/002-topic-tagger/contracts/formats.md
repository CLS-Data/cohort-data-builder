# Contract: Topic Tagger file formats

These are the tool's public formats. The processing script (`scripts/topics.py`) relies on
them and on nothing else (FR-028). All files are UTF-8. Entity rules are in
[../data-model.md](../data-model.md).

## Input: `variables.jsonl`

One JSON object per line. Blank lines are ignored.

```json
{"file": "bcs1derived", "variable": "BCSID", "label": "Cohort member ID", "identifier": true}
{"file": "bcs1derived", "variable": "BD1SMOKE", "label": "Mother smoked in pregnancy", "values": [["1", "Yes"], ["2", "No"]], "sweep": "0y"}
```

## Scheme: `scheme.toml`

```toml
name = "CLOSER topics"
version = 1
identifier_topic = "identifiers"
fallback_topic = "other"
guidance = """
You are classifying variables from a UK longitudinal cohort study by topic...
"""

[[domains]]
id = "health_behaviour"
label = "Health behaviour"
description = "..."
cessda = "Health"

  [[domains.topics]]
  id = "smoking"
  label = "Smoking"
  description = "Tobacco and e-cigarette use, exposure to smoke."
  closer = "10603"
```

The tool ships `topic_tagger/schemes/closer.toml`, converted from the PoC scheme. `topic-tagger
init-scheme` copies it out so it can be edited.

## Output folder

```text
<out>/
├── tags.jsonl     one tag record per variable
├── scheme.json    the scheme used (shape below)
├── run.json       the last run's settings, counts and statistics
├── report.html    the report, self-contained
└── .lock          present only while a run is in progress
```

### `tags.jsonl`

```json
{"file": "bcs1derived", "variable": "BD1SMOKE", "topics": [["smoking", 0.9], ["pregnancy_history", 0.85]], "scheme": "c87a35ec8bc2", "model": "ollama:gpt-oss:20b", "tagged": "2026-10-27T14:03:11Z"}
```

During a run, lines are only ever appended. A variable may appear more than once, and the
last line for it wins; a cut-off last line is ignored. When a run ends, the file is rewritten
with one line per variable, sorted by `file` then `variable`.

### `scheme.json`

This has the same shape as the site's manifest `topics` object, plus `guidance`,
`identifier_topic` and `fallback_topic`:

```json
{"name": "CLOSER topics", "version": 1, "hash": "c87a35ec8bc2", "guidance": "...",
 "identifier_topic": "identifiers", "fallback_topic": "other",
 "domains": [{"id": "health_behaviour", "label": "Health behaviour", "description": "...",
              "topics": [{"id": "smoking", "label": "Smoking", "description": "..."}]}]}
```

### `run.json`

The fields are as in the data model's *Run* and *Run statistics*:

```json
{"started": "...", "ended": "...", "status": "finished", "settings": {...},
 "counts": {...}, "failed": [...], "timeline": [[0, 0], [10, 37]], "stats": {...}}
```

### `report.html`

A single file with no external requests and no scripts. Sections:
1. run header: date, model, scheme name, version and hash, settings;
2. summary tiles: tagged, failed, run time, speed, mean topics, share below 50%;
3. variables per topic area: bars;
4. variables per topic within each area: bars, with unused topics listed;
5. confidence histogram;
6. topic areas by sweep: heat grid, left out when there are no sweeps;
7. speed over time: line;
8. per-file table, and the list of failed variables.

It follows the reader's light or dark preference.
