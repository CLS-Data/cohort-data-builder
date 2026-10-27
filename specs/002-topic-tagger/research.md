# Research: Topic Tagger

Decisions for the plan. The reference implementation is the PoC tagger (`PoC/enrich/`), which
used LangChain with `ChatOllama`, Pydantic, `rich` and a YAML scheme.

## R1. Calling the model

**Decision**: The official `openai` Python SDK, pointed at Ollama's OpenAI-compatible
endpoint (`http://localhost:11434/v1`), behind a small `Provider` interface of the tool's own
(one method: send messages plus a JSON schema, get text back). The first provider is
`ollama`. A later host (OpenAI, OpenRouter, vLLM, LM Studio, a llama.cpp server, or a
hosted service with an OpenAI-compatible API) needs only a base URL and an API key from the
environment. A host without an OpenAI-compatible API gets its own `Provider` class.

**Rationale**:
- The user asked for the most popular lightweight wrapper, Ollama now, and other hosts
  later. The OpenAI chat-completions protocol is the de facto common interface: Ollama
  serves it, as do most local and hosted servers. Its official SDK is the most widely used
  LLM client in Python.
- It is light: its main dependencies are `httpx` and `pydantic`, which the tool needs
  anyway for validation.
- Ollama's compatibility layer supports `response_format` (structured outputs) and
  `/v1/models`, which the pre-flight check uses. It ignores the API key for a local server.
- The `Provider` interface is one method. That keeps the stand-in model for tests trivial
  (FR-025) and is the only place a new host plugs in.

**Alternatives considered**:
- **LiteLLM**: the most popular multi-provider wrapper (100+ providers, Ollama included). It
  was rejected for now on two counts:
  - It is not lightweight: a large dependency tree for what is one call here.
  - It had two supply-chain compromises on PyPI in 2026: credential-stealing releases
    1.82.7/1.82.8 in March, and 1.107.0 from a hijacked release pipeline on 21 October 2026.

  A tool that maintainers run on their own machines, possibly with API keys in their
  environment, should keep its dependency surface small. Because providers sit behind
  `Provider`, a LiteLLM provider can be added later if a host needs it.
- **LangChain (`langchain-ollama`)**: used by the PoC. It is heavy for one call, and its
  abstractions (output parsers, message classes) add nothing that Pydantic and a prompt
  string do not already give.
- **`ollama` Python client**: light, but Ollama-only, so a second host would need a second
  client anyway.
- **Instructor**: retries and validation around many clients. The tool's retry rules (whole
  batch, then one variable at a time, then mark as failed) are specific enough to write
  directly, and that avoids another dependency.

**Note**: Structured-output enforcement differs between models and hosts. The tool always
validates every reply itself (R3), so a host that ignores the schema only costs retries,
never bad tags.

## R2. Scheme file format

**Decision**: TOML (`scheme.toml`), read with the standard library's `tomllib`. The shipped
default is the PoC's `topics.yaml` converted once: 15 domains, about 100 topics, the
guidance text and CLOSER/CESSDA cross-references.

**Rationale**:
- TOML is plain, supports comments and multi-line strings (for the guidance), and is
  unambiguous.
- Python reads it with no extra dependency (Simplicity).
- `[[domains]]` and `[[domains.topics]]` tables map directly onto the two-level scheme.

**Alternatives considered**: YAML, as in the PoC: friendlier for long text, but it needs
PyYAML and has ambiguous types ("no" read as false). JSON: no comments.

## R3. Validating replies

**Decision**: Pydantic models built from the loaded scheme. A reply is a list of
`{id, topics: [{topic, confidence}]}`. `topic` is constrained to the scheme's ids, and
`confidence` to 0–1. The same model's JSON schema is sent as the structured-output format.

**Rationale**: One definition gives both the schema the model is held to and the check
applied to what comes back (FR-006). Pydantic is already a dependency of `openai`.

## R4. Live display

**Decision**: `rich` (`Live`, `Progress`, `Table`). With no live terminal (`not
sys.stdout.isatty()`, or `--plain`), plain progress lines go to stderr every 10 seconds.

**Rationale**:
- `rich` is the standard for terminal dashboards in Python, and the PoC already used it.
- It gives progress, rates, time remaining and tables in a few lines.
- It degrades in CI and when output is redirected.

**Alternatives considered**: `tqdm` (progress bars only, no tables); `textual` (a full TUI
framework, more than needed).

## R5. Final report

**Decision**: A single self-contained `report.html` written beside the tags. It uses inline
SVG charts made by a small module of the tool (horizontal bars, histogram, heat grid, line),
with inline CSS and light/dark styling. It has no JavaScript and no external requests, so it
opens offline (FR-021).

**Rationale**: The charts needed are simple:
- bars for variables per topic area and per topic;
- a histogram of confidences;
- a grid of topic areas by sweep;
- a line of speed over time.

Generating SVG directly is about 150 lines, adds no dependency, and keeps the file small.
The charts are testable as text.

**Alternatives considered**:
- **matplotlib**: a heavy install, and its PNG output is not crisp or theme-aware.
- **plotly** or **Vega embedded inline**: several MB of JavaScript in every report.

## R6. Storage and resuming

**Decision**: An output folder per cohort, holding:
- `tags.jsonl`: one line per variable, appended after each batch and flushed. It is
  compacted (sorted, one line per variable, written to a temporary file and renamed) at the
  end of a run.
- `scheme.json`: the scheme used, with its version hash.
- `run.json`: the last run's settings and statistics.
- `report.html`: the report.
- `.lock`: written at start; holds the process id.

A record is current when its `scheme` hash equals the hash of the loaded scheme. The hash
is the first 12 hex characters of SHA-256 over the canonical JSON of the scheme and guidance
(FR-013).

**Rationale**:
- Append-and-flush loses at most the batches in flight (FR-012).
- A cut-off last line is ignored on load.
- Rename-on-compact never leaves a half-written file.
- The lock refuses a second run (FR-015). A stale lock, whose process is gone, is reported
  and can be cleared with `--force`.

This is the PoC's `TagStore` behaviour, kept.

## R7. Concurrency

**Decision**: A thread pool (`concurrent.futures`) with `--workers` requests in flight (default
2), and `--batch-size` variables per request (default 20). Requests time out after
`--timeout` seconds (default 120). Each batch is retried `--retries` times (default 2), then
its variables are tried one at a time, then any still failing are recorded as failed.

**Rationale**: Requests are I/O-bound, and the `openai` SDK's synchronous client is
thread-safe. Threads are simpler to test and stop with Ctrl-C than asyncio. The defaults
suit a local model on a laptop; the PoC's 4 workers assumed a cloud model.

## R8. Local or remote model (FR-011)

**Decision**: Before any request, the tool decides whether the host is the maintainer's own
machine. It treats a request as remote if either of these holds:
- the base URL's host is not `localhost`, `127.0.0.1` or `::1`;
- the model name ends in `-cloud`. Ollama runs these models on its own servers even through
  a local Ollama.

For a remote request it prints what will leave the machine (variable names, labels, value
labels) and asks for confirmation unless `--yes` is given. With no terminal to ask in, it
refuses unless `--yes` is given.

## R9. Packaging and independence

**Decision**: The tool is in `tools/topic-tagger/` with:
- its own `pyproject.toml`, `uv.lock`, `README.md`, `tests/` and ruff settings;
- the package name `topic-tagger` and the command `topic-tagger`;
- Python 3.12.

The root `pyproject.toml` excludes `tools/` from ruff and pytest. A separate workflow,
`.github/workflows/topic-tagger.yml`, runs the tool's lint and tests on changes under
`tools/topic-tagger/`.

**Rationale**:
- FR-023 and FR-024 require independence, and SC-006 requires that the folder can be copied
  out and still work.
- Its own lockfile and workflow mean it shares nothing with the site at install, test or
  run time.

## R10. The processing script (site side)

**Decision**: `scripts/topics.py` in this repository, standard library only, with two
commands:
- `export <cohort>`: reads `site/data/<key>/`, writes `variables.jsonl`;
- `merge <cohort> <tags-dir>`: writes the scheme into the manifest and tags into the
  dictionaries and index, then runs the site's data checks (001 D1–D8) and reports.

It reads only the tool's documented file formats (contracts/), never its code (FR-028).
Tests go in `tests/python/topics/`, run by the site's CI.

**Rationale**: It belongs to the site, which owns `site/data`. Using the standard library
only matches `tests/python/data/checks.py`.

**Merge details**:
- **Topic numbers:** the index uses scheme-wide topic numbers in scheme order (001
  contract).
- **Percents:** confidences become `round(confidence * 100)`.
- **Order:** both the dictionaries and the index list tags strongest first.
- **Ties:** equal confidences are broken by scheme order.
