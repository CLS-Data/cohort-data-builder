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

This folder is a self-contained project: copy it anywhere and it works on its own.

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
| 0 | Every variable tagged (or the dry run finished). |
| 1 | Finished, but some variables could not be tagged; they are listed. |
| 2 | Bad input, scheme or options; nothing was sent. |
| 3 | Ollama could not be reached or the model is not installed; nothing was sent. |
| 4 | Another run is using the output folder, or one left its lock (see `--force`). |
| 130 | Stopped with Ctrl-C; what was tagged is saved. |

**Privacy.** Only variable metadata (names, labels, value labels) is sent, never study
data. With a local model it never leaves your machine. A model on another machine, or an
Ollama `-cloud` model (which runs on Ollama's servers even through your local Ollama),
sends that metadata off your machine: the tool says so and asks first, unless you pass
`--yes`.
