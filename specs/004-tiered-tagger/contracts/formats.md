# Contract: output additions (for `tools/topic-tagger/docs/formats.md`)

## `tags.jsonl`

Flat record, with the one addition `method`:

```json
{"file": "f", "variable": "smoke5", "topics": [["smoking", 0.9]], "scheme": "a1b2c3d4e5f6",
 "model": "ollama:gpt-oss:20b-cloud", "tagged": "2026-11-13T12:00:00Z", "method": "flat"}
```

Tiered record:

```json
{"file": "f", "variable": "smoke5", "topics": [["smoking", 0.9], ["pregnancy_history", 0.7]],
 "scheme": "a1b2c3d4e5f6", "model": "ollama:gpt-oss:20b-cloud",
 "tagged": "2026-11-13T12:00:00Z", "method": "tiered",
 "path": [["health_behaviour", 0.9], ["family", 0.6]]}
```

- `method`: how the tags were made. A record without it was made by the flat method.
  Records made with another method count as stale.
- `path`: the areas followed, in order, with their confidence. Tiered records only.
- `topics` means the same for both methods: leaf topic and its own confidence.

## `run.json`

Added:

```json
{"method": "tiered", "descend_at": 0.5, "max_areas": 3, "keep_at": 0.3, "requests_by_tier": [12, 41]}
```

`keep_at` appears only for the decision provider.

A flat run has `"method": "flat"` and `"requests_by_tier": [<requests>]`.

## Consumers

`scripts/topics.py` and the site read only `topics`, `scheme`, `file` and `variable`, so no
change is needed there.
