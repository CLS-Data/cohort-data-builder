# Quickstart: validating feature 005

Run everything from `tools/topic-tagger/`. Steps 1–7 need no model.

```sh
uv sync
uv run pytest          # all pass, including the new tests below
uv run ruff check . && uv run ruff format --check .
```

## 1. Old schemes still work (FR-004, SC-003)

```sh
uv run topic-tagger check-scheme src/topic_tagger/schemes/closer.toml
```

Expected: `2 tiers`, 15 categories at tier 1, 107 leaves, and **the same hash as on
`main`**. A finished 004 output folder, re-run with the same settings, has nothing to do.

## 2. One and three tiers (story 1)

```sh
uv run topic-tagger check-scheme src/topic_tagger/schemes/example-1-tier.toml
uv run topic-tagger check-scheme src/topic_tagger/schemes/example-3-tier.toml
```

Expected: `1 tier` and `3 tiers`, with categories per tier and the largest question at each
tier (contract `cli.md`).

A copy with a fourth tier, a repeated id, or an empty group exits 2, listing each problem
with its location.

## 3. Every tier in a dry run (stories 4 and 5)

```sh
S=src/topic_tagger/schemes/example-3-tier.toml
uv run topic-tagger tag tests/fixtures/variables.jsonl --out /tmp/t --scheme $S --dry-run
uv run topic-tagger tag tests/fixtures/variables.jsonl --out /tmp/t --scheme $S --dry-run --provider ollama
```

- **The first command** (the file's `[run]` names `ollama-decision`, tiered) prints three
  `/v1/systemone` bodies, one per tier. Each body's `instructions` is the guidance, then the
  file's question for that tier, with `{group}` filled in.
- **The second** prints three chat requests, each with a `Question:` line.

## 4. All four combinations (story 2)

The tests in `test_runner.py` tag the two-tier fixture with fake models in each of these
four ways:
- chat flat;
- chat tiered;
- decision flat;
- decision tiered.

Expected:
- stored leaf tags in every case;
- `method` right in each record;
- decision flat: one request per variable, offering every leaf;
- three-tier tiered: records whose `path` has two entries.

## 5. A refusal stops the run (FR-009, SC-002)

In `test_runner.py` and `test_cli.py`, a fake decision host answers HTTP 400 with an
options error when a question has more than 5 options.

Expected:
- **Flat** with the 8-leaf fixture: exit 5. The message names "every topic, asked flat",
  gives 8 options and the host's text, and suggests tiered. `run.json` has `stop_reason`.
  No variable is listed as failed, and no request is retried.
- **Tiered** with a fixture where one group has 6 children: earlier batches are stored, the
  message names that group, and a second run after the group is split carries on.
- **Other errors still retry**: a 400 with any other text (for example a context error)
  still goes through retries and single requests, as today.

## 6. The file controls the run (story 3)

A fixture with `[run]` (decision, tiered, `descend_at = 0.3`), tagged with a fake:
- With no options, `run.json` shows those values, each with source `file`.
- With `--method flat`, `run.json` shows `flat` with source `cli`.
- With `run.descend_at = 1.5`, the run exits 2, naming `run.descend_at`.
- Changing only `[run]` keeps the hash, so a re-run has nothing to do. Changing a
  `[questions]` entry changes the hash, so the next run redoes everything.

## 7. Prompts unchanged where nothing changed

`tests/fixtures/flat_prompt.txt` still matches the flat chat prompt for the 004 fixture.
Tier prompts with no `[questions]` are byte-for-byte as in 004.

## 8. With real models (maintainer, outside the sandbox)

```sh
uv run topic-tagger tag tests/fixtures/variables.jsonl --out /tmp/clef-flat \
  --scheme tests/fixtures/scheme_small.toml --provider ollama-decision --model clef:cloud \
  --method flat --yes
```

Expected: every variable tagged, `method: "flat"`, one request each.

Then try a question with 27 options or more against Clef (for example the bundled `closer.toml`
flat, with 107 leaves):

```sh
uv run topic-tagger tag tests/fixtures/variables.jsonl --out /tmp/clef-big \
  --scheme src/topic_tagger/schemes/closer.toml --provider ollama-decision \
  --model clef:cloud --method flat --yes
```

Expected: either exit 5 after the first request, with the model's own message (record its
status and text in `research.md` R1 and make the fake host's refusal match it), or, for a
model with no limit that low, a normal finish. `clef:cloud` finished normally when tested in
November 2026 (see R1).
