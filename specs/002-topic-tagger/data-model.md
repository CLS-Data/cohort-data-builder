# Data Model: Topic Tagger

Entities from the spec (Key Entities). File layouts are in [contracts/formats.md](contracts/formats.md).

## Variable (input)

One variable to tag. One line of `variables.jsonl`.

| Field | Type | Rules |
|---|---|---|
| `file` | string | Required, not empty. |
| `variable` | string | Required, not empty. `file` + `variable` is unique, ignoring case. |
| `label` | string \| null | Optional. |
| `values` | list of `[value, label]` | Optional. Only the first 30 are sent to the model (edge case: huge value lists). |
| `sweep` | string \| null | Optional. Used only for statistics. |
| `identifier` | bool | Optional, default false. True marks the participant identifier, tagged by rule (FR-007). |

**Key**: `file/variable`, compared ignoring case. A duplicate key in the input is an error
that stops the run before tagging, listing the duplicates with their line numbers.

## Scheme

Loaded from `scheme.toml` (FR-016).

| Field | Type | Rules |
|---|---|---|
| `name` | string | Required. |
| `version` | int | Required; the maintainer's own label. |
| `guidance` | string | Required: the instructions given to the model. |
| `identifier_topic` | topic id | Required. Must be a topic in the scheme. |
| `fallback_topic` | topic id | Required. Must be a topic in the scheme ("other"). |
| `domains[]` | list of Domain | At least one. |
| `hash` | string | Derived, not written by hand: the first 12 hex characters of SHA-256 over the canonical JSON of everything above. |

**Domain**: `id`, `label` and `description` are required, and `topics[]` has at least one
entry. `closer` and `cessda` are optional and passed through.

**Topic**: `id`, `label` and `description` are required. `closer` and `added` are optional.

**Validation (FR-017)**: before tagging, the tool lists every problem it finds, each with
its location, for example `domains[3].topics[2].id`. The problems it checks for are:
- an id that does not match `^[a-z][a-z0-9_]*$`;
- an id used twice anywhere in the scheme, by a domain or a topic;
- a domain with no topics;
- a missing label or description;
- `identifier_topic` or `fallback_topic` not naming a topic in the scheme.

**Topic number**: each topic's position across the scheme, in order and counting from 0.
The processing script uses it for the site index.

## Tag

One topic on one variable: `[topic id, confidence]`, with the confidence a number from 0 to
1, rounded to 2 decimal places. A model reply goes through these rules (FR-006):
- the topic must be in the scheme;
- the confidence must be from 0 to 1;
- duplicate topics are merged, keeping the highest confidence;
- a reply with no tags for a variable counts as a missing variable;
- tags are stored strongest first, with ties broken by scheme order.

## Tag record

All the tags for one variable. One line of `tags.jsonl`.

| Field | Type | Rules |
|---|---|---|
| `file`, `variable` | string | The input key. |
| `topics` | list of Tag | At least one. |
| `scheme` | string | The scheme hash the tags were made with. |
| `model` | string | `provider:model`, e.g. `ollama:gpt-oss:20b`, or `rule` for the identifier. |
| `tagged` | string | ISO 8601 UTC time. |

**State** for each variable, worked out at the start of a run:

| State | Meaning |
|---|---|
| `missing` | No record. |
| `stale` | Has a record, but its `scheme` differs from the current scheme hash. |
| `current` | Has a record with the current scheme hash. |

A run tags the `missing` and `stale` variables, or every variable with `--retag`, limited by
`--files` and `--limit` (FR-013, FR-014). A variable that is still failing at the end of a
run gets no record, so it stays `missing` and the next run tries it again.

## Run

One time the tool is run. Saved as `run.json`.

| Field | Meaning |
|---|---|
| `started`, `ended` | ISO times. |
| `status` | `finished`, `stopped` (Ctrl-C) or `error`. |
| `settings` | The settings used: provider, base URL, model, batch size, workers, timeout, retries, files, limit, retag, scheme path and hash. |
| `counts` | `total`, `todo`, `tagged`, `skipped` (already current), `failed`, `requests`, `retries`, `singles` (variables retried one at a time). |
| `failed` | List of `file/variable` that could not be tagged (FR-022). |
| `timeline` | Variables done per 10-second interval, for the speed chart. |

## Run statistics

Worked out from the tag records that are current when the run ends, so every number agrees
with `tags.jsonl` (SC-004). Saved inside `run.json` as `stats`.

| Statistic | Definition |
|---|---|
| `per_topic` | `{topic id: number of variables}` for every topic, including zeros. |
| `per_domain` | `{domain id: number of variables}`. A variable counts once per domain, however many of that domain's topics it has. |
| `unused` | Topics with no variables. |
| `confidence_histogram` | Counts of tags in 10 bins: [0, 0.1), …, [0.9, 1.0]. |
| `below_default` | Share of variables whose strongest tag is under 0.5. |
| `mean_topics` | Average number of tags per variable. |
| `per_file` | `{file: {tagged, failed}}`. |
| `domain_by_sweep` | `{sweep: {domain id: variables}}`; left empty when no input record has a sweep. |
| `speed` | Mean variables per minute over the run; the timeline gives speed over time. |
