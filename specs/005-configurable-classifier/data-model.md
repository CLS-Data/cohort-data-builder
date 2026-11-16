# Data model: A configurable classification pipeline

## Category

One entry in the taxonomy.

| Field | Rule |
|---|---|
| `id` | Lower-case letters, digits and `_`, starting with a letter. Unique across the whole taxonomy, at every tier. |
| `label` | Required, not blank. |
| `description` | Optional in the nested form (empty when missing). Required in the 004 form, as today. |
| `children` | Categories one tier down, in file order. Empty for a **leaf**; at least one for a **group**. |

- **Depth**: a category's tier is 1 at the top. No category may sit at tier 4.
- A group with exactly one child is valid. The walk passes through it without a question.

## Taxonomy (`Scheme`)

| Field | Rule |
|---|---|
| `name`, `version`, `guidance` | As in 004 (required text, an integer and required text). |
| `fallback_topic` | Must name a **leaf**. |
| `root` | The tree: a nameless root whose children are the tier-1 categories. |
| `questions` | Optional: `flat`, `tier1`, `tier2`, `tier3` → text; `{group}` allowed. A `tierN` beyond the depth is refused. |
| `run` | Optional `RunSettings` from the file (below). |
| `hash` | 12 hex characters of SHA-256 over the parsed file **without `run`**. |

Rules:
- There must be at least two leaves.
- A file uses `categories` (nested) or `domains` (004), never both.

Views derived from `root` (kept for prompts, statistics and reports):
- `tiers`: the height of the tree, 1 to 3.
- `topics` and `topic_ids`: the leaves, in file order. `topic_number(id)` gives a leaf's
  position.
- `domains`: one per tier-1 category, with every leaf beneath it. A tier-1 leaf forms a
  domain of itself.
- `domain_of(leaf)`: the leaf's tier-1 ancestor, as a domain.
- `path_of(leaf)`: the groups from tier 1 down to the leaf's parent.

## Question trees (built per run, not stored)

- **Tiered tree** (`build_tree`):
  - the taxonomy, with the fallback leaf moved to tier 1 as an exit;
  - any group that the move leaves empty is removed, repeatedly up the tree.
- **Flat tree** (`flat_tree`): a root whose children are every leaf, including the fallback.
  It is used only for flat tagging with a decision model.

## RunSettings

| Setting | Values | Default | Source |
|---|---|---|---|
| `provider` | `ollama`, `ollama-decision` | `ollama` | CLI `--provider`, file `run.provider` |
| `model` | text | `gpt-oss:20b` | `--model`, `run.model` |
| `method` | `flat`, `tiered` | `tiered` for `ollama-decision`, else `flat` | `--method`, `run.method` |
| `descend_at` | 0–1 | 0.5 | `--descend-at`, `run.descend_at` |
| `max_follow` | integer ≥ 0 (0 = no cap) | 3 | `--max-follow` (alias `--max-areas`), `run.max_follow` |
| `keep_at` | 0–1 | 0.3 | `--keep-at`, `run.keep_at` (decision models only) |

- **Resolution**: the CLI value if given, otherwise the file's, otherwise the default. Each
  setting's source (`cli`, `file` or `default`) is kept.
- **After resolution**:
  - a one-tier taxonomy turns `tiered` into `flat`, with a notice (research R7);
  - `descend_at` and `max_follow` are recorded only for tiered runs;
  - `keep_at` is recorded only for decision models.

## Tag record (`tags.jsonl`)

Unchanged fields: `file`, `variable`, `topics`, `scheme`, `model`, `tagged` and `method`.
- `topics` are leaf ids.
- `path`, for tiered runs, lists the groups followed, one entry per group and in walk order.
  With three tiers, a variable that reaches one leaf has two entries. A variable that
  followed several branches has one entry for each group in each branch.

**Staleness**, as in 004: a record is current when its `scheme` equals the scheme's hash
(which leaves out `[run]`) and its `method` equals the run's method.

## Run record (`run.json`) additions

| Field | Meaning |
|---|---|
| `settings.provider`, `settings.model`, `settings.method`, `settings.descend_at`, `settings.max_follow`, `settings.keep_at` | The resolved settings. `max_areas` is still written, with the same value, for older readers. |
| `settings_source` | `{setting: "cli" \| "file" \| "default"}` |
| `tiers` | The taxonomy's height. |
| `counts.requests_by_tier` | As in 004, one entry per tier asked. |
| `stop_reason` | Only when a model refused a question: the message shown to the user. |

## OptionLimitError

A `ProviderError` raised by a decision provider when the host refuses a question for its
number of options (research R1).

| Field | Meaning |
|---|---|
| `status` | The HTTP status (400 or 413). |
| `host_message` | The host's `error` text. |
| `options` | How many options were sent. |

The walk adds the question it came from (flat list, top tier, or group id and label) before
the runner stops.

## States of a run

```text
running ──(all batches done)──────────────────────────────▶ finished (exit 0, or 1 if any failed)
   │──(Ctrl-C)────────────────────────────────────────────▶ stopped  (exit 130)
   └──(OptionLimitError)──▶ stop flag; in-flight batches stored ──▶ refused (exit 5, stop_reason)
```
