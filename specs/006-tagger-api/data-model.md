# Data Model: The Topic Tagger as a Python API

All of these are in memory; the API writes no files. For the exact signatures see
[contracts/api.md](contracts/api.md).

## Input

One of the following:

| Form | Becomes | Sent to the model |
|---|---|---|
| `str` | `Variable(file=<position>, variable="", label=text)` | `name: ""`, `label: text`, `values: []` |
| `Variable` | a copy with `file=<position>` | its name, label and value labels (at most 30) |
| `dict` (a `variables.jsonl` line) | parsed as the file's lines are, then as `Variable` | as `Variable` |

Validation:
- **dict**: the same rules as a `variables.jsonl` line (`file` and `variable` non-empty,
  `values` as `[value, label]` pairs). A bad dict raises `ValueError` naming its position.
- **Anything else**: raises `TypeError` naming its position.

## Tag

| Field | Type | Meaning |
|---|---|---|
| `topic` | `str` | Leaf id in the scheme. |
| `label` | `str` | The leaf's label. |
| `confidence` | `float` | 0–1, as stored in `tags.jsonl`. |

## Result

One per input, in input order.

| Field | Type | Meaning |
|---|---|---|
| `input` | `str \| Variable \| dict` | What the caller passed, unchanged. |
| `tags` | `list[Tag]` | Strongest first; empty if failed. |
| `path` | `list[tuple[str, float]] \| None` | Tiered: the groups followed, with confidence; `None` for flat. |
| `failed` | `bool` | True when no tags were obtained after the retries. |
| `error` | `str` | The call's last error, for a failed input; empty otherwise. |
| `topics` (property) | `list[str]` | `[t.topic for t in tags]`. |
| `to_dict()` | `dict` | Same keys as a `tags.jsonl` record, plus `failed` and `error`, minus `file`/`variable`/`tagged`. |

## Results

A sequence of `Result` (indexable, iterable, `len`), plus:

| Field | Type | Meaning |
|---|---|---|
| `settings` | `dict` | Resolved `provider`, `model`, `method`, `descend_at`, `max_follow`, `keep_at`. |
| `sources` | `dict[str, str]` | Each setting's source: `call`, `file` or `default`. |
| `notes` | `list[str]` | As the CLI prints, e.g. "This taxonomy has one tier: tagging flat." |
| `requests_by_tier` | `list[int]` | Requests sent at each tier. |
| `retries` | `int` | Requests retried. |
| `scheme_name`, `scheme_hash` | `str` | Which scheme tagged them. |
| `failed` (property) | `list[Result]` | The failed results. |

The source for a setting from the API is named `call`. The command line keeps `cli` in
`run.json`. `settle` takes the label as an argument.

## Tagger

| Field | Meaning |
|---|---|
| `scheme` | The loaded `Scheme`. |
| `settings`, `sources`, `notes` | As in `Results`, resolved once, at construction. |
| state: `checked` | False until the first non-empty call checks the host; then True. |

Lifecycle: constructed (scheme loaded, settings resolved and checked, provider made; no
network) → first non-empty call (host checked, unless `check=False`; remote consent
checked) → calls (each a fresh `Runner` over an in-memory sink).

## Internal changes (not public)

| Where | Change |
|---|---|
| `scheme.py` | `parse_scheme(text, source)` split out of `load_scheme`; same checks and hash. |
| `run_settings.py` | `settle(given, scheme, label="cli") -> Resolved`, holding the checks now in `cli._settle`; raises `ValueError`. |
| `variables.py` | `variable_from_dict(data)`, the public name for the line parser. |
| `runner.py` | `store` typed as `RecordSink` (a protocol with `append`). |
| `cli.py` | `_settle` calls `settle`; output unchanged. |
