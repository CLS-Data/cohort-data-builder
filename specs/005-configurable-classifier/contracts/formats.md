# Contract: file formats (changes from 004)

## The scheme file

Two forms. A file uses one or the other, never both.

### Nested form (new): one to three tiers

```toml
name = "Life course topics"
version = 1
fallback_topic = "other"
guidance = '''
You are classifying variables from a UK cohort study by what they measure.
'''

[questions]                     # optional; {group} is the label of the group asked about
flat  = "Which topic is this variable about?"
tier1 = "Which domain of a survey is this variable about?"
tier2 = "Which topic within {group} is this variable about?"
tier3 = "Which subtopic within {group} is this variable about?"

[run]                           # optional; command-line options override it
provider   = "ollama-decision"
model      = "clef:cloud"
method     = "tiered"
descend_at = 0.3
max_follow = 3
keep_at    = 0.3

[[categories]]                  # tier 1
id = "health"
label = "Health"
description = "Physical and mental health, and health behaviour."

  [[categories.categories]]     # tier 2
  id = "physical_health"
  label = "Physical health"

    [[categories.categories.categories]]   # tier 3
    id = "respiratory"
    label = "Respiratory conditions"
    description = "Asthma, bronchitis, wheeze."

  [[categories.categories]]     # a tier-2 leaf beside a tier-2 group (uneven is allowed)
  id = "smoking"
  label = "Smoking"

[[categories]]
id = "other"
label = "Other"
description = "Nothing above fits."
```

- **One tier** is a flat list of `[[categories]]` with no children.
- **Rules**:
  - Ids are unique across all tiers.
  - Labels are required; descriptions are optional.
  - A group needs at least one child.
  - Depth is at most 3.
  - There must be at least two leaves.
  - `fallback_topic` must name a leaf.
  - `[questions]` keys are limited to `flat` and `tier1` up to the depth.
  - `[run]` keys and values are as in `cli.md`.
- Unknown keys on categories (for example a code from another vocabulary) are allowed and
  kept, as in 004.

### 004 form (unchanged)

`[[domains]]` with `[[domains.topics]]`. It loads as a two-tier taxonomy, and keeps its
rules and its hash. It may also have `[questions]` and `[run]`.

### Hash

SHA-256 of the parsed file without the `[run]` table, as canonical JSON, first 12 hex
characters.
- Editing `[run]` does not make tags out of date.
- Editing anything else does, as in 004.

## `scheme.json` (written beside the tags)

The 004 fields remain, including `domains` (derived: one per tier-1 category, with every
leaf beneath it), so `scripts/topics.py` works unchanged. Three fields are added:

```json
{"tiers": 3,
 "questions": {"tier2": "Which topic within {group} is this variable about?"},
 "categories": [{"id": "health", "label": "Health", "description": "…",
                 "categories": [{"id": "physical_health", "label": "Physical health", "description": "",
                                 "categories": [{"id": "respiratory", "label": "…", "description": "…"}]},
                                {"id": "smoking", "label": "Smoking", "description": ""}]},
                {"id": "other", "label": "Other", "description": "Nothing above fits."}]}
```

`report` rebuilds the taxonomy from `categories` when present, and from `domains`
otherwise (folders written by 004).

## `tags.jsonl`

No new fields.
- `topics` holds leaf ids.
- `path`, in tiered runs, lists every group followed, top down. A three-tier example:

```json
{"file": "w1", "variable": "ASTHMA", "topics": [["respiratory", 0.91]], "scheme": "1a2b3c4d5e6f",
 "model": "ollama-decision:clef:cloud", "tagged": "2026-11-16T10:00:00Z", "method": "tiered",
 "path": [["health", 0.97], ["physical_health", 0.88]]}
```

A flat record from a decision model has `"method": "flat"` and no `path`.

## `run.json`

The 004 fields remain. These are added:

```json
{"settings": {"provider": "ollama-decision", "model": "clef:cloud", "method": "tiered",
              "descend_at": 0.3, "max_follow": 3, "max_areas": 3, "keep_at": 0.3, "…": "…"},
 "settings_source": {"provider": "file", "model": "file", "method": "cli",
                     "descend_at": "file", "max_follow": "default", "keep_at": "file"},
 "tiers": 3,
 "stop_reason": "The model clef:cloud refused a question with 31 options (…)"}
```

`stop_reason` is present only when a run was stopped by a refusal (exit 5).
