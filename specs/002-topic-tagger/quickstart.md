# Quickstart: Topic Tagger

These are the runs that prove the feature works. The commands are in
[contracts/cli.md](contracts/cli.md) and the files in
[contracts/formats.md](contracts/formats.md).

## Prerequisites

- uv, and Python 3.12 (uv installs it if needed).
- For real runs only: [Ollama](https://ollama.com) running, with a model pulled
  (`ollama pull gpt-oss:20b`). The tests do not need Ollama.

## 1. The tool on its own (SC-006)

```sh
cp -r tools/topic-tagger "$TMPDIR/tt" && cd "$TMPDIR/tt"
uv sync && uv run pytest && uv run ruff check .
```

Expect every test to pass outside the repository, with no network access.

## 2. Check and edit the scheme (US3)

```sh
cd tools/topic-tagger
uv run topic-tagger init-scheme my-scheme.toml
uv run topic-tagger check-scheme my-scheme.toml        # exit 0, "15 domains, 1xx topics"
```

Duplicate a topic id in `my-scheme.toml` and run `check-scheme` again. Expect exit 2, with
the duplicate named and both of its locations shown.

## 3. Dry run (US1, scenario 6)

```sh
uv run topic-tagger tag tests/fixtures/variables.jsonl --out "$TMPDIR/out" \
  --scheme my-scheme.toml --dry-run
```

Expect the guidance, the topic list and the first 20 variables on stdout. No request is
sent, so this also works with Ollama stopped.

## 4. A real run, stopped and resumed (US1, US2, US4, US5)

```sh
uv run topic-tagger tag tests/fixtures/variables.jsonl --out "$TMPDIR/out" --model gpt-oss:20b
```

Expect a live display showing:
- progress bar, percentage, elapsed and remaining time, variables per minute;
- failures and retries;
- a table of the leading topic areas and topics.

Press Ctrl-C part way through. Expect exit code 130, a summary, and a `report.html`.

Run the same command again. Expect "N already tagged, M to do", where M is only the
remainder. When it finishes, open `$TMPDIR/out/report.html` with networking off: every chart
shows, and the counts match the terminal summary.

With Ollama stopped, the same command exits with code 3 and the message "Ollama is not
reachable at http://localhost:11434". It makes no requests.

## 5. Publish to the site (US6, SC-008)

From the repository root, with a cohort folder whose topics have been removed:

```sh
uv run python scripts/topics.py export site/data/<key> --out "$TMPDIR/vars.jsonl"
(cd tools/topic-tagger && uv run topic-tagger tag "$TMPDIR/vars.jsonl" --out "$TMPDIR/tags")
uv run python scripts/topics.py merge site/data/<key> --tags "$TMPDIR/tags"
uv run pytest tests/python/data
```

Expect the merge to report the counts and "data checks: no problems". Then serve the site
(`uv run python -m http.server -d site 8000`) and check that the cohort shows the topic grid,
the topic chips and the topic filter.

## 6. CI

- The site's `ci` workflow runs `tests/python/topics/`, the processing script's tests.
- The `topic-tagger` workflow runs on every pull request. It runs the tool's lint and tests
  when `tools/topic-tagger/` changed, and otherwise passes at once, so it can be a required
  check.
