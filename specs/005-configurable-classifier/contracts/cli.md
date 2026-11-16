# Contract: `topic-tagger` command line (changes from 004)

## `tag`: where settings come from

Each of these settings comes from the command line if given, then from the scheme's `[run]`
table, then from the default.

| Option | `[run]` key | Default |
|---|---|---|
| `--provider ollama\|ollama-decision` | `provider` | `ollama` |
| `--model NAME` | `model` | `gpt-oss:20b` |
| `--method flat\|tiered` | `method` | `tiered` for `ollama-decision`, else `flat` |
| `--descend-at X` | `descend_at` | `0.5` |
| `--max-follow N` (alias `--max-areas`) | `max_follow` | `3` (0 = no cap) |
| `--keep-at X` | `keep_at` | `0.3` |

The other options stay command-line only:
- `--base-url`;
- `--workers`;
- `--batch-size`;
- `--retries`;
- `--timeout`;
- `--out`;
- `--yes`.

**What changes from 004:**
- `--provider ollama-decision --method flat` is allowed. It asks one `choice` question per
  variable, offering every leaf.
- There is no check of the number of options before tagging. The scheme-size error, exit 2
  ("does not fit a decision model"), is removed.
- `tiered` with a one-tier taxonomy tags flat, and prints:
  `This taxonomy has one tier: tagging flat.`
- A `keep_at` set in `[run]` with a chat provider is ignored, and prints:
  `keep_at in the scheme applies to decision models only; ignored.`
- `--keep-at` on the command line with a chat provider is still exit 2.

**Bad values** exit 2, before anything is sent. Each message names its source:
- `--descend-at must be between 0 and 1`;
- `run.descend_at in my-scheme.toml must be between 0 and 1`.

## `tag`: a model refuses a question (new exit status 5)

When the decision host refuses a question because it has too many options, the run stops.
Batches already in flight are stored. Then stderr shows:

```text
The model clef:cloud refused a question with 107 options (every topic, asked flat):
  HTTP 400: <the host's error text>
Tag tiered (--method tiered) so each question offers fewer options. Tags made so far are
kept; run again to carry on.
```

For a group, the first line names it, and the advice changes:

```text
The model clef:cloud refused a question with 31 options (the topics in group
physical_health, "Physical health", tier 2):
  HTTP 400: <the host's error text>
Split physical_health into smaller groups, or use a model that takes more options. Tags
made so far are kept; run again to carry on.
```

At tier 1, the question is described as `(the tier-1 categories and the fallback exit)`.

When the run stops this way:
- exit status 5;
- `run.json` has `stop_reason` set to the message;
- the summary is printed, as for any stopped run.

**Exit statuses**: 0, 1, 2, 3, 4 and 130 are as in 004. The new one:

| Code | Meaning |
|---|---|
| 5 | A model refused a question because it has too many options. What was tagged is saved. |

## `tag --dry-run`

Prints one example request for each tier the method would ask, following the first group
down. Each tier is introduced by a line:

```text
--- tier 1 ---
--- tier 2 example (<group label>) ---
--- tier 3 example (<group label>) ---
```

- Decision models: each request is printed as a `/v1/systemone` JSON body for the first
  variable.
- Chat models: each request is printed as system text, then user text, for the first batch.
- Flat: one request.

Nothing is sent.

## `check-scheme FILE`

Exit 0 when the file is valid. It prints:

```text
Life course topics (version 1): 3 tiers, hash 1a2b3c4d5e6f
  tier 1: 6 categories (5 groups, 1 leaf)
  tier 2: 24 categories (9 groups, 15 leaves)
  tier 3: 41 categories (41 leaves)
  57 leaves; fallback: other
  largest question, flat: 57 options (every leaf)
  largest question, tier 1: 6 options (5 groups and the fallback exit)
  largest question, tier 2: 9 options (in health, "Health")
  largest question, tier 3: 12 options (in physical_health, "Physical health")
  run settings: provider ollama-decision, model clef:cloud, method tiered (from the file)
```

- A two-tier 004 file prints the same layout, with two tiers.
- An invalid file exits 2, listing every problem with its location, as in 004.
