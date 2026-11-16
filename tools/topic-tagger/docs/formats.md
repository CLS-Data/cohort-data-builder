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
| `fallback_topic` | Required; must be a topic (a leaf) in the scheme. |
| `domains` | At least one. Each has `id`, `label`, `description` and at least one topic. |
| `domains.topics` | Each has `id`, `label` and `description`. |

### Nested form: one to three tiers

Instead of `domains`, a file may list `categories`, nested up to three deep:

```toml
[[categories]]
id = "health"
label = "Health"
description = "Physical and mental health."

  [[categories.categories]]
  id = "physical_health"
  label = "Physical health"

    [[categories.categories.categories]]
    id = "respiratory"
    label = "Respiratory conditions"
    description = "Asthma, bronchitis, wheeze."

[[categories]]
id = "other"
label = "Other"
```

| Field | Rules |
|---|---|
| `categories` | At least one, at every level where it appears. A file has `categories` or `domains`, not both. |
| `id` | As below. |
| `label` | Required text. |
| `description` | Optional text (empty when missing). |
| `categories` (inside a category) | Makes it a **group**: at least one category. Without it, the category is a **leaf**. |

At most three tiers (a category inside a tier-3 category is refused); at least two leaves;
`fallback_topic` must be a leaf. Depth may be uneven: a leaf can sit beside a group. Leaves
are what variables are tagged with; the `domains` form is the same as two tiers.

Ids are lower-case letters, digits and `_`, start with a letter, and are unique across the
whole file, at every tier (domains and topics together, in the `domains` form). Other keys (for example a code from another
vocabulary) are allowed but not used.

### `[run]`: how to classify (optional)

```toml
[run]
provider   = "ollama-decision"   # or "ollama" (chat models)
model      = "clef:cloud"
method     = "tiered"            # or "flat"
descend_at = 0.3                 # tiered: follow a group at this confidence or above
max_follow = 3                   # tiered: most groups followed per question; 0 for no cap
keep_at    = 0.3                 # decision models: keep a leaf at this probability or above
```

Every key is optional. Each setting comes from the command line if given, then from
`[run]`, then from its default (`ollama`, `gpt-oss:20b`, flat for a chat model and tiered
for a decision model, 0.5, 3, 0.3). An unknown key, or a value out of range, is refused
when the file is loaded, as `run.<key>`. A `keep_at` here is ignored, with a note, when the
run uses a chat model. The host's address, keys, workers, batch size, retries, timeout and
output folder are not in `[run]`: they belong to one machine, or are secret.

The scheme's **hash** is the first 12 hex characters of SHA-256 over its parsed content,
leaving out `[run]`, so any change to content (not comments, layout or `[run]`) changes it
and makes existing tags out of date. Changing a model or a threshold in `[run]` does not:
it is how a run is made, not what the tags mean. Each topic's **number** is its position across the whole scheme, counting from 0.

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
{"file": "wave1", "variable": "SMOKE", "topics": [["smoking", 0.9], ["health_general", 0.4]], "scheme": "c87a35ec8bc2", "model": "ollama:gpt-oss:20b", "tagged": "2027-01-15T08:00:00Z", "method": "flat"}
{"file": "wave1", "variable": "SMOKE", "topics": [["smoking", 0.9]], "scheme": "c87a35ec8bc2", "model": "ollama-decision:clef:cloud", "tagged": "2027-01-15T08:00:00Z", "method": "tiered", "path": [["health", 0.95]]}
```

| Field | Rules |
|---|---|
| `file`, `variable` | The input key. |
| `topics` | At least one `[topic id, confidence]`: the topic is in the scheme, the confidence is 0 to 1, rounded to 2 places; strongest first, ties in scheme order. |
| `scheme` | The hash of the scheme the tags were made with. |
| `model` | `provider:model`. |
| `tagged` | ISO 8601 UTC time. |
| `method` | `flat` or `tiered`: how the tags were made. A line without it was made by the flat method. |
| `path` | Tiered only: the groups followed, top down, as `[group id, confidence]` (two entries per branch in a three-tier taxonomy). A flat record, from a chat or a decision model, has none. |

`topics` means the same for both methods: each topic with its own confidence. In a tiered
line it is the topic-level confidence, merged across areas (highest per topic).

During a run lines are only appended, so a variable may appear more than once: the last
line wins, and a cut-off last line is ignored. When a run ends the file is rewritten with
one line per variable, sorted by `file` then `variable`. A variable that could not be
tagged has no line, so the next run tries it again. A line whose `scheme` differs from the
current scheme's hash, or whose `method` differs from the run's, is out of date and is redone.

### `scheme.json`

The scheme as used, with its hash:

```json
{"name": "My topics", "version": 1, "hash": "c87a35ec8bc2", "guidance": "...",
 "fallback_topic": "other", "tiers": 2,
 "categories": [{"id": "health", "label": "Health", "description": "...",
                 "categories": [{"id": "smoking", "label": "Smoking", "description": "..."}]}],
 "domains": [{"id": "health", "label": "Health", "description": "...",
              "topics": [{"id": "smoking", "label": "Smoking", "description": "..."}]}]}
```

`categories` is the taxonomy, nested as in the scheme file (a leaf has no `categories`);
`tiers` is its depth. `domains` is a two-level view kept for older readers: one entry per
tier-1 category, with every leaf beneath it (a tier-1 leaf is a domain of itself). Folders
written before `categories` existed are read from `domains`.

### `run.json`

```json
{"started": "...", "ended": "...", "status": "finished", "settings": {...},
 "counts": {...}, "failed": [...], "timeline": [[0, 37], [10, 41]], "stats": {...}}
```

| Field | Meaning |
|---|---|
| `status` | `finished` or `stopped` (Ctrl-C, or a refusal). |
| `stop_reason` | Only when a model refused a question for its number of options (exit 5): the message shown, naming the question. |
| `settings` | Provider, base URL, model, `method` (`flat` or `tiered`), for tiered runs `descend_at` and `max_follow` (also written as `max_areas`, its 004 name), for decision models (`ollama-decision`) `keep_at`, batch size, workers, timeout, retries, files, limit, retag, grouping field, variables path, scheme path and hash. Never an API key. |
| `settings_source` | Where each of `provider`, `model`, `method`, `descend_at`, `max_follow` and `keep_at` came from: `cli`, `file` (the scheme's `[run]`) or `default`. Only the settings that apply to the run are listed. |
| `tiers` | How many tiers the taxonomy has. |
| `counts` | `total`, `todo`, `tagged`, `skipped` (already current), `failed`, `requests`, `requests_by_tier` (index 0 is tier 1; a flat run has one entry), `retries`, `singles` (variables retried one at a time). |
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
