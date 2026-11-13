# Quickstart: Tiered tagging

## 1. Tests (no model needed)

From `tools/topic-tagger/`:

```sh
uv sync
uv run pytest            # all pass, including tests/test_tiered.py
uv run ruff check . && uv run ruff format --check .
```

## 2. See the requests without sending anything

```sh
uv run topic-tagger tag tests/fixtures/variables.jsonl --out "$TMPDIR/t" \
  --method tiered --dry-run
```

Expected output:
- a tier-1 request listing only areas, each with its topic labels;
- `--- tier 2 example (…) ---`;
- a request listing only that area's topics.

## 3. Add Clef to Ollama (once)

```sh
ollama --version          # 0.40.6 or later for cloud models
ollama signin             # if not signed in; clef:cloud needs a plan or credits
ollama pull clef:cloud    # registers the cloud model; nothing large is downloaded
```

(`ollama pull clef` downloads the 18–20 GB local model instead.)

## 4. Tag the fixture with Clef

```sh
uv run topic-tagger tag tests/fixtures/variables.jsonl --out "$TMPDIR/clef" \
  --provider ollama-decision --model clef:cloud --method tiered --yes
```

Expected:
- all 60 variables are tagged, and none fail (SC-005);
- the summary shows the requests by tier.

## 5. Tag the fixture with a chat model, tiered

```sh
uv run topic-tagger tag tests/fixtures/variables.jsonl --out "$TMPDIR/tiered" \
  --method tiered --model gpt-oss:20b-cloud --yes
```

Expected:
- every variable is tagged, and none fail;
- the summary shows `Requests by tier: 1: …, 2: …`;
- each line of `$TMPDIR/tiered/tags.jsonl` has `"method": "tiered"` and a `path`.

## 6. Compare the methods (ad hoc)

From the repository root, with Ollama running and signed in for cloud models:

```sh
uv run --project tools/topic-tagger python adhoc/tiered/compare.py
```

Expected: a table, one row per run (flat/gpt-oss, tiered/gpt-oss, tiered/clef), with:
- top-1 hits, recall, precision, requests and seconds;
- then the variables where the two methods disagree, with the expected topics.

It finishes in under 10 minutes. Results are kept in `adhoc/tiered/runs/`.

To try real variables instead, a choice for the maintainer since it sends study metadata to
a cloud model: export a cohort with `scripts/topics.py export` and pass `--variables` with
a sample. That run has no expected topics, so the script reports only the disagreements.

## 7. Decide

If tiered recall ≥ flat recall (SC-001), consider making it the default in a follow-up.
Otherwise keep flat, and note the result in `research.md`.
