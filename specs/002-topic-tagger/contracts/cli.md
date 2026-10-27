# Contract: Commands

## `topic-tagger` (the tool, in `tools/topic-tagger/`)

```text
topic-tagger tag VARIABLES.jsonl --out DIR --scheme SCHEME.toml [options]
topic-tagger check-scheme SCHEME.toml
topic-tagger init-scheme PATH            copy the bundled example scheme, to edit
topic-tagger report DIR [--group-by F]   rebuild report.html from DIR's tags and run.json
```

`--scheme` is required: the tool never picks a scheme itself (FR-018). Every other `tag`
option has a default, and `--help` lists them all (FR-019):

| Option | Default | Meaning |
|---|---|---|
| `--scheme PATH` | required | Scheme and guidance file. |
| `--provider NAME` | `ollama` | The model host. `ollama` is the only one for now. |
| `--base-url URL` | `http://localhost:11434/v1` | Where the host is. Also read from `TOPIC_TAGGER_BASE_URL`. |
| `--model NAME` | `gpt-oss:20b` | Model name on the host. |
| `--group-by FIELD` | `sweep` | Input field the statistics and report group by. |
| `--batch-size N` | 20 | Variables per request. |
| `--workers N` | 2 | Requests in flight. |
| `--timeout S` | 120 | Seconds before a request is abandoned and retried. |
| `--retries N` | 2 | Retries per batch before trying its variables one at a time. |
| `--files A,B` | all | Tag only these files. |
| `--limit N` | all | Tag at most N variables. |
| `--retag` | off | Redo current tags too. |
| `--dry-run` | off | Print the instructions and first batch; send nothing. |
| `--yes` | off | Do not ask before sending to a remote model. |
| `--plain` | auto | Plain progress lines instead of the live display. |
| `--force` | off | Clear a stale lock left by a run that has ended. |

An API key, for hosts that need one, comes only from the environment
(`TOPIC_TAGGER_API_KEY`), never from an option, so it never shows up in shell history or
`run.json`.

**Exit codes**:

| Code | Meaning |
|---|---|
| 0 | Every variable tagged, or the dry run, check or report finished. |
| 1 | The run finished, but some variables failed. |
| 2 | Bad input, scheme or options; nothing was sent. |
| 3 | The host could not be reached or the model is missing; nothing was sent. |
| 4 | Locked: another run is in progress. |
| 130 | Stopped with Ctrl-C. The tags so far are saved, and a summary and report are written. |

**Output streams**: the live display and progress lines go to stderr. stdout carries only
the final summary, or with `--dry-run` the prompt, so it can be piped.

## `scripts/topics.py` (the processing script, at the repository root)

```text
uv run python scripts/topics.py export site/data/<key> --out variables.jsonl
uv run python scripts/topics.py merge  site/data/<key> --tags DIR
```

**`export`**:
- Writes every variable in every dictionary file of the cohort, in index order.
- Takes `sweep` from the file's `wave`.
- Leaves out the manifest's `identifier` variable (matched ignoring case), which the merge
  tags itself.
- Exits 0 when done, 2 on unreadable data.

**`merge`** (FR-026, FR-027):
1. Reads `DIR/scheme.json` and `DIR/tags.jsonl`, and keeps only the records whose `scheme`
   equals the scheme hash.
2. Writes the manifest's `topics`: `name`, `version`, `hash`, and the `domains` with their
   `id`, `label`, `description` and `topics` (`id`, `label`, `description`).
3. Tags the manifest's `identifier` variable, in every file that has it, with
   `[[IDENTIFIER_TOPIC, 1.0]]` (option `--identifier-topic`, default `identifiers`); stops
   with exit 2 if the scheme has no such topic.
4. Writes each tagged variable's dictionary `topics` as `[[id, confidence], …]`, strongest
   first.
5. Writes each index row's element 5 as `[number, round(confidence × 100), …]`, strongest
   first. Untagged rows keep exactly 5 elements.
6. Reports, without stopping:
   - records for variables not in the cohort;
   - variables with no record;
   - records left out because their scheme hash is stale.
7. Writes JSON in the same style as the existing files (no extra whitespace), each file to
   a temporary file first and then renamed.
8. Runs the site's data checks on the cohort and prints any problems.

Exit codes: 0 when merged and the checks pass; 1 when merged but the checks report
problems; 2 on bad input.
