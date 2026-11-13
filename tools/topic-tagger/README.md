# Topic Tagger

Tags the variables of a survey or cohort study by topic, using a language model that runs
on your own machine through [Ollama](https://ollama.com). You control the topics and the
instructions the model is given by editing one plain file. While it runs you see live
progress; when it finishes you get a summary and a report with charts.

It reads variable metadata only (names, labels, value labels), never study data.

Nothing in the tool is specific to any topic scheme or study: the topics, their
descriptions and the instructions all come from a scheme file you choose with `--scheme`.
An example scheme is bundled (based on the CLOSER Discovery topics for UK cohort studies)
for you to copy and adapt; the tool never uses it unless you pass it.

This folder is a self-contained project: copy it anywhere and it works on its own. The
file formats are in [docs/formats.md](docs/formats.md).

## Quick start (about 15 minutes)

1. Install [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com), and start
   Ollama.
2. Pull a model: `ollama pull gpt-oss:20b` (13 GB; on a machine without a large GPU, a
   smaller model or an Ollama `-cloud` model such as `gpt-oss:20b-cloud` is much faster).
3. From this folder: `uv sync`, then `uv run topic-tagger init-scheme my-scheme.toml`.
4. Try it on the 60 fictional variables that come with the tests:

   ```sh
   uv run topic-tagger tag tests/fixtures/variables.jsonl --out /tmp/tags --scheme my-scheme.toml
   ```

   You see the live view, then a summary. Open `/tmp/tags/report.html` in a browser.
5. Write your own `variables.jsonl` ([format](docs/formats.md)), edit `my-scheme.toml`
   to your topics, and tag for real.

## Install

Needs [uv](https://docs.astral.sh/uv/). From this folder:

```sh
uv sync                      # then run it as: uv run topic-tagger --help
uv tool install .            # or install the topic-tagger command for your user
```

## Tag a cohort

You need [Ollama](https://ollama.com) running and a model pulled, for example:

```sh
ollama pull gpt-oss:20b
```

Then, from this folder, start a scheme from the example and tag with it:

```sh
uv run topic-tagger init-scheme my-scheme.toml
uv run topic-tagger tag variables.jsonl --out tags/ --scheme my-scheme.toml
```

`variables.jsonl` has one variable per line: `file`, `variable`, and optionally `label` and
`values` (`[value, label]` pairs), which are what the model sees. Every variable is sent to
the model; leave out any you do not want tagged. A line may carry any other fields, such
as `"sweep": "5y"` or `"questionnaire": "parent"`: they are kept, never sent, and the
statistics group by the one named with `--group-by` (default `sweep`). The output folder gets
`tags.jsonl` (each variable's topics with a confidence from 0 to 1) and `scheme.json` (the
topics used). Every reply is checked, so only topics from the scheme and confidences from
0 to 1 are ever stored; a batch that fails is retried, then its variables are sent one at
a time.

Check what will be sent first, without sending anything (works with Ollama stopped):

```sh
uv run topic-tagger tag variables.jsonl --out tags/ --scheme my-scheme.toml --dry-run
```

`uv run topic-tagger tag --help` lists every option with its default. The ones you are
most likely to change are `--model`, `--batch-size` (variables per request, default 20)
and `--workers` (requests at once, default 2).

**Speed** depends on the model and your machine. A model that does not fit in your GPU's
memory runs partly on the CPU and can take minutes per request; a smaller model, or a
smaller `--batch-size`, helps.

## Watching a run

In a terminal, a live view redraws four times a second:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  100%  60/60  elapsed 00:00:34  remaining 00:00:00  105/min
Leading topic areas                          Leading topics
 Physical health                  18          Anthropometry                 12
 Demographics                     12          Age                            6
 ...                                          ...
Failed 0   Retried 1
```

It shows progress, elapsed and remaining time, speed over the last minute, the five leading
topic areas and ten leading topics so far, and how many variables failed and how many
requests were retried. When the output is not a terminal (a log file, a pipe, a CI job), or
with `--plain`, it writes one line every 10 seconds instead, and one at the end:

```text
[00:01:40] 120/600 (20%) 72/min eta 00:06:40 failed 0 retries 1
```

Progress goes to stderr; stdout gets only the final summary.

## Reading the report

When a run ends, even one you stopped, the tool prints a summary and saves the same figures
in the output folder: `run.json` (under `stats`) and `report.html`, a single file that opens
in any browser with no network connection and follows your light or dark setting. It has:

1. **Run**: when, which model, which scheme (name, version, hash) and the settings, so
   reports from different runs can be compared side by side.
2. **Summary**: variables tagged, failed, run time, speed, mean topics per variable, and the
   share of variables with no tag at 50% or above (the site hides those by default).
3. **Topic areas**: how many variables have a topic in each area.
4. **Topics**: the used topics in each area, then every topic never used. Many unused
   topics, or one topic taking most variables, suggests the scheme or guidance needs work.
5. **Confidence**: every tag's confidence, in tenths.
6. **Topic areas by group**: a grid of areas against the values of the `--group-by` field
   (default `sweep`); left out when no variable has the field.
7. **Speed**: variables per minute over the run.
8. **Data files**: tagged and failed per file, and the variables that could not be tagged.

Hover over a bar or cell for its exact figure; each chart can also be shown as a table.
To rebuild the report, for example grouped by another field, without tagging again:

```sh
uv run topic-tagger report tags/ --group-by questionnaire
```

## Stopping and carrying on

Tags are saved after every batch, so you can stop a run at any point with **Ctrl-C**. The
batches already sent finish and are saved; press Ctrl-C again to quit at once. Then run the
same command again: it reports how many variables are already tagged and does only the rest.

- **Changing the scheme or the guidance** makes every existing tag out of date (each tag
  records the scheme it was made with), so the next run redoes them all.
- `--retag` redoes every variable, even ones with current tags.
- `--files alpha,beta` tags only those data files; `--limit 100` at most 100 variables.
  Both are handy for trying a model or a scheme change on a sample first.
- Variables that could not be tagged get no tags, so the next run tries them again.
- Only one run can use an output folder at a time. If a run was killed without cleaning
  up (for example the machine shut down), the next one says so: check nothing else is
  running and add `--force`.

The output folder also gets `run.json`, recording each run's settings and counts.

## Editing the topics and instructions

Everything the model is told lives in one file: the topic areas (domains), the topics in
each with a description, and the general guidance. The bundled example is based on the
CLOSER Discovery topics (15 areas, 107 topics). Copy it and edit the copy:

```sh
uv run topic-tagger init-scheme my-scheme.toml      # never overwrites an existing file
uv run topic-tagger check-scheme my-scheme.toml     # lists every mistake, with where it is
uv run topic-tagger tag variables.jsonl --out tags/ --scheme my-scheme.toml --dry-run
```

The file looks like this:

```toml
name = "CLOSER topics"
version = 1
fallback_topic = "other"           # what the model should use when nothing fits
guidance = '''
You are classifying variables from a UK longitudinal cohort study by topic...
'''

[[domains]]
id = "health_behaviour"
label = "Health behaviour"
description = "..."

  [[domains.topics]]
  id = "smoking"
  label = "Smoking"
  description = "Tobacco and e-cigarette use."   # the model reads this
```

- Ids are lower-case letters, digits and `_`, start with a letter, and are unique across
  the whole file. Every domain needs at least one topic, and every domain and topic a label
  and description. `check-scheme` (and `tag`, before it sends anything) lists every
  mistake, for example `domains[1].topics[0].id: 'smoking' is also used at
  domains[1].topics[1].id` (positions count from 0).
- **Any** edit, even to a description or the guidance, makes existing tags out of date,
  so the next run redoes them. Comments and layout do not count.
- Ids are what gets stored: rename one only if you mean to retag.
- Keep as many scheme files as you like and choose one per run with `--scheme`.

**Exit codes**

| Code | Meaning |
|---|---|
| 0 | Every variable tagged, or the dry run, check or report finished. |
| 1 | Finished, but some variables could not be tagged; they are listed. |
| 2 | Bad input, scheme or options; nothing was sent. |
| 3 | The host could not be reached or the model is not installed; nothing was sent. |
| 4 | Another run is using the output folder, or one left its lock (see `--force`). |
| 130 | Stopped with Ctrl-C; what was tagged is saved. |

**Privacy.** Only variable metadata (names, labels, value labels) is sent, never study
data. With a local model it never leaves your machine. A model on another machine, or an
Ollama `-cloud` model (which runs on Ollama's servers even through your local Ollama),
sends that metadata off your machine: the tool says so and asks first, unless you pass
`--yes`.

## Tiered tagging

By default each request lists every topic in the scheme (`--method flat`). With
`--method tiered` the tool works down the taxonomy instead:

1. **Areas first.** One request per batch asks which areas (the scheme's domains) each
   variable belongs to. Each area is shown with its topics' labels, so the model can see
   where, say, "Pregnancy" lives.
2. **Then topics within each area.** For each area followed, one request asks the
   variables routed there which of that area's topics apply. Only that area's topics are
   listed.

An area is followed when its confidence is at least `--descend-at` (0.5), at most
`--max-areas` of them (3; 0 for no cap). The strongest area is always followed, so no
variable stops at the first tier. A stored tag keeps its topic-level confidence, so it
means the same as a flat tag.

A batch takes 1 + (the number of different areas followed) requests instead of 1, but each
request is short. Failed requests are retried as in flat runs, per area. A variable keeps
the tags from the areas that answered, and fails only if it ends with none.
`--dry-run --method tiered` prints the first tier's request and one area's.

### With a decision model (Clef)

[Clef](https://ollama.com/library/clef) is a decision model: it does not write replies but
answers typed questions about one thing with probabilities. To use it:

```sh
ollama --version          # 0.40.6 or later
ollama signin             # clef:cloud runs in Ollama's cloud: a plan or credits
ollama pull clef:cloud    # or `ollama pull clef` for the 18–20 GB local model
uv run topic-tagger tag variables.jsonl --out tags/ --scheme my-scheme.toml \
  --provider ollama-decision --model clef:cloud
```

For each variable and tier, Clef is asked one choice question: "Which area of a survey is
this variable about?", then "Which topic…" within each area followed. Each option is
described by its label and description, and an area also by its topics. Clef gives every
option a probability, and these sum to about 1. The probability is the confidence.

Areas are followed as above. Topics are kept at `--keep-at` (0.3) or above, and the
strongest is always kept. Because the probabilities are shared out between the options,
a variable rarely has two areas or topics above 0.5. Lower `--descend-at` and `--keep-at`
to keep more than one.

Clef tags tiered only: a choice question takes at most 26 options, too few for every
topic at once, so `--method flat` is refused. For the same reason the tool refuses a scheme
with more than 26 areas, or an area with more than 26 topics, before sending anything. The
bundled scheme has 15 areas and at most 23 topics in one.

Clef is asked one variable at a time: 1 request, plus 1 per area followed. A cohort of
30,000 variables is therefore 60,000 requests or more. Clef's cloud tag is
billed per input token, so try `--limit` first. A model ending `:cloud` (or `-cloud`) runs
off this machine, so the tool asks before sending unless you pass `--yes`.
`--dry-run` prints the first variable's request bodies.

## Every option

`uv run topic-tagger --help` lists the commands and `uv run topic-tagger tag --help` the
options, with their defaults.

| Command | Does |
|---|---|
| `tag VARIABLES --out DIR --scheme FILE` | Tag the variables, carrying on from what `DIR` already has. |
| `init-scheme PATH` | Copy the bundled example scheme to `PATH`, to edit. Never overwrites. |
| `check-scheme FILE` | List every mistake in a scheme, or summarise it. |
| `report DIR [--group-by FIELD]` | Rebuild `report.html` (and the statistics in `run.json`). |

| `tag` option | Default | Meaning |
|---|---|---|
| `--scheme FILE` | required | The topics and instructions. |
| `--group-by FIELD` | `sweep` | Input field the statistics are grouped by. |
| `--provider NAME` | `ollama` | The model host: `ollama` for chat models, `ollama-decision` for decision models such as Clef. |
| `--base-url URL` | `http://localhost:11434/v1` | Where the host's API is; also `TOPIC_TAGGER_BASE_URL`. |
| `--model NAME` | `gpt-oss:20b` | Model name on the host. |
| `--method flat\|tiered` | `flat` | `flat`: every topic in one request. `tiered`: areas first, then topics within them. See [Tiered tagging](#tiered-tagging). Always `tiered` with `ollama-decision`. |
| `--descend-at X` | 0.5 | Tiered: follow an area at this confidence or above. |
| `--max-areas N` | 3 | Tiered: follow at most N areas per variable; 0 for no cap. |
| `--keep-at X` | 0.3 | Decision models: keep a topic at this probability or above; 0 keeps every topic. The strongest is always kept. |
| `--batch-size N` | 20 | Variables per request. |
| `--workers N` | 2 | Requests in flight at once. |
| `--timeout S` | 120 | Seconds before a request is abandoned and retried. |
| `--retries N` | 2 | Retries per batch before its variables are sent one at a time. |
| `--files A,B` | all | Tag only these data files. |
| `--limit N` | all | Tag at most N variables. |
| `--retag` | off | Redo variables that already have current tags. |
| `--dry-run` | off | Print the instructions and the first batch; send nothing. |
| `--yes` | off | Do not ask before sending to a remote model. |
| `--plain` | off | Plain progress lines instead of the live view (automatic without a terminal). |
| `--force` | off | Clear a lock left by a run that ended without cleaning up. |

A host that needs an API key reads it from `TOPIC_TAGGER_API_KEY`, never from an option,
so it is not in your shell history or in `run.json`.

## Adding a model host

The tool talks to Ollama through its OpenAI-compatible API, so a host with the same API
(vLLM, LM Studio, llama.cpp's server) already works with `--base-url` and, if it needs
one, `TOPIC_TAGGER_API_KEY`; its error messages will still name Ollama until the host is
registered as below.

To give a host its own name, wording or rules, register it in `get_provider` in
`src/topic_tagger/providers/__init__.py`: either the existing `OpenAICompatProvider` with
the host's name, the command that installs a missing model and the suffix of models it
runs remotely, or a new class with the three methods of the `Provider` protocol:
`check()` (raise `ProviderError` unless the host and model are there), `is_remote()`, and
`complete(messages, schema)` (return the reply's text). Replies are checked by the tool,
not the host, so a new host needs no parsing of its own.

## Using this outside Cohort Data Builder

Nothing here depends on the rest of the repository: copy this folder anywhere, run
`uv sync`, and `uv run pytest` passes. Prepare a `variables.jsonl` from your own metadata
([format](docs/formats.md)), write a scheme for your own topics (starting from
`init-scheme` or from scratch), and read the tags from `tags.jsonl`. Cohort Data Builder
does this with its own script (`scripts/topics.py` in that repository), which converts
its site data to and from these formats; do the same for yours.

## Licence

MIT, as for the rest of Cohort Data Builder. The licence text is in `LICENSE` in this
folder, so a copy of the folder carries it.
