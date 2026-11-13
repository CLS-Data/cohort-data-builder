# Data model: Tiered tagging

## Node (in memory, `tiered.py`)

The taxonomy as a tree, built from a `Scheme`.

| Field | Meaning |
|---|---|
| `id` | Area or topic id; `""` for the root |
| `label`, `description` | From the scheme |
| `children` | Child nodes, in scheme order; empty for a topic (leaf) |

- Root → one node per area → one leaf per topic.
- `is_leaf` means no children. Only leaf ids are ever stored as tags.
- Validation is unchanged: the scheme loader already guarantees unique ids, and that the
  fallback topic exists.

## Group (in memory, during one batch)

A node and the batch's variables routed to it, each with its path so far.

- Created at the root with the whole batch.
- At a node with more than one child: one request over its children. Chosen children that
  are areas spawn groups (R3). Chosen leaves become tags.
- At a node with one child: routed without a request, keeping the parent's confidence.

## Decision path

For each variable, the areas chosen on the way, in order: `[[area_id, confidence], …]`.
With two tiers, it is the tier-1 choices that were followed.

## Records (`tags.jsonl`), changed

| Field | Flat | Tiered |
|---|---|---|
| `topics` | `[[topic, conf], …]` as now | Leaf confidences from tier 2, merged across areas: highest per topic, strongest first, ties in scheme order |
| `method` | `"flat"` (new) | `"tiered"` |
| `path` | absent | `[[area, conf], …]` |

State is:
- `current` when the scheme hash and `method` both match;
- `stale` otherwise;
- `missing` when there is no record.

A record with no `method` counts as `"flat"`.

## Run record (`run.json`), added

- `method`
- `descend_at` and `max_areas` (tiered only; `max_areas` 0 means no cap)
- `keep_at` (decision provider only)
- `requests_by_tier`: a list, index 0 being tier 1

The existing `requests` field stays the total.
