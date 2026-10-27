# Topic Tagger file formats

The files the tool reads and writes. Anything that prepares its input or uses its output
should rely on these and nothing else. All files are UTF-8.

## Input: `variables.jsonl`

One JSON object per line; blank lines are ignored.

```json
{"file": "wave1", "variable": "SMOKE", "label": "Do you smoke?", "values": [["1", "Yes"], ["2", "No"]], "sweep": "1"}
```

| Field | Type | Rules |
|---|---|---|
| `file` | string | Required, not empty. The data file the variable is in. |
| `variable` | string | Required, not empty. `file` + `variable` is unique, ignoring case. |
| `label` | string or null | Optional. |
| `values` | list of `[value, label]` | Optional. Only the first 30 are sent to the model. |
| any other field | any JSON value | Optional. Kept as given and never sent to the model; `--group-by FIELD` (default `sweep`) picks the one the statistics group by. |

Only `label` and `values`, with the variable's name, are sent to the model. Every line is
tagged: leave out variables you do not want tagged (such as identifiers). A bad line or a
duplicate key stops the run before anything is sent, listing every problem with its line
number.

## Scheme: a TOML file you choose with `--scheme`

```toml
name = "My topics"
version = 1
fallback_topic = "other"          # what the model should use when nothing fits
guidance = '''
You are classifying variables from a household survey by topic...
'''

[[domains]]
id = "health"
label = "Health"
description = "Physical and mental health."

  [[domains.topics]]
  id = "smoking"
  label = "Smoking"
  description = "Tobacco and e-cigarette use."
```

| Field | Rules |
|---|---|
| `name`, `guidance` | Required text. The guidance is the model's instructions, before the topics. |
| `version` | Required whole number; your own label. |
| `fallback_topic` | Required; must be a topic in the scheme. |
| `domains` | At least one. Each has `id`, `label`, `description` and at least one topic. |
| `domains.topics` | Each has `id`, `label` and `description`. |

Ids are lower-case letters, digits and `_`, start with a letter, and are unique across the
whole file, domains and topics together. Other keys (for example a code from another
vocabulary) are allowed but not used.

The scheme's **hash** is the first 12 hex characters of SHA-256 over its parsed content, so
any change to content (not comments or layout) changes it and makes existing tags out of
date. Each topic's **number** is its position across the whole scheme, counting from 0.

`topic-tagger init-scheme PATH` copies the bundled example to start from;
`topic-tagger check-scheme PATH` lists every mistake with its location.

## Output folder

```text
<out>/
├── tags.jsonl     one tag record per variable
├── scheme.json    the scheme used
├── run.json       the last run's settings, counts and statistics
├── report.html    the report, self-contained
└── .lock          present only while a run is in progress
```

### `tags.jsonl`

```json
{"file": "wave1", "variable": "SMOKE", "topics": [["smoking", 0.9], ["health_general", 0.4]], "scheme": "c87a35ec8bc2", "model": "ollama:gpt-oss:20b", "tagged": "2027-01-15T08:00:00Z"}
```

| Field | Rules |
|---|---|
| `file`, `variable` | The input key. |
| `topics` | At least one `[topic id, confidence]`: the topic is in the scheme, the confidence is 0 to 1, rounded to 2 places; strongest first, ties in scheme order. |
| `scheme` | The hash of the scheme the tags were made with. |
| `model` | `provider:model`. |
| `tagged` | ISO 8601 UTC time. |

During a run lines are only appended, so a variable may appear more than once: the last
line wins, and a cut-off last line is ignored. When a run ends the file is rewritten with
one line per variable, sorted by `file` then `variable`. A variable that could not be
tagged has no line, so the next run tries it again. A line whose `scheme` differs from the
current scheme's hash is out of date and is redone.

### `scheme.json`

The scheme as used, with its hash:

```json
{"name": "My topics", "version": 1, "hash": "c87a35ec8bc2", "guidance": "...",
 "fallback_topic": "other",
 "domains": [{"id": "health", "label": "Health", "description": "...",
              "topics": [{"id": "smoking", "label": "Smoking", "description": "..."}]}]}
```

### `run.json`

```json
{"started": "...", "ended": "...", "status": "finished", "settings": {...},
 "counts": {...}, "failed": [...], "timeline": [[0, 37], [10, 41]], "stats": {...}}
```

| Field | Meaning |
|---|---|
| `status` | `finished` or `stopped` (Ctrl-C). |
| `settings` | Provider, base URL, model, batch size, workers, timeout, retries, files, limit, retag, grouping field, variables path, scheme path and hash. Never an API key. |
| `counts` | `total`, `todo`, `tagged`, `skipped` (already current), `failed`, `requests`, `retries`, `singles` (variables retried one at a time). |
| `failed` | `file/variable` of each variable that could not be tagged. |
| `timeline` | `[seconds, variables]`: variables tagged in each 10-second step. |
| `stats` | The statistics below, from the records current when the run ended. |

| Statistic | Definition |
|---|---|
| `per_topic` | `{topic id: variables}` for every topic, including zeros. |
| `per_domain` | `{domain id: variables}`; a variable counts once per domain. |
| `unused` | Topics with no variables. |
| `confidence_histogram` | Tags in 10 bins, [0, 0.1) to [0.9, 1.0]. |
| `below_default` | Share of variables whose strongest tag is under 0.5. |
| `mean_topics` | Tags per variable. |
| `per_file` | `{file: {tagged, failed}}`. |
| `group_by`, `per_group`, `domain_by_group` | The grouping field, `{value: variables}` and `{value: {domain id: variables}}`; empty when no variable has the field. |
| `speed` | Variables tagged per minute in this run. |

### `report.html`

One file with no scripts and no external requests, following the reader's light or dark
setting. Sections: the run; summary tiles; variables per topic area; variables per topic
within each area, with unused topics listed; confidence; topic areas by the grouping field
(left out when no variable has it); speed over the run; per-file counts and the failed
variables. `topic-tagger report DIR [--group-by FIELD]` rebuilds it.
