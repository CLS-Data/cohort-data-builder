# Topic Tagger

Tags the variables of a survey or cohort study by topic, using a language model that runs
on your own machine through [Ollama](https://ollama.com). You control the topics and the
instructions the model is given by editing one plain file. While it runs you see live
progress; when it finishes you get a summary and a report with charts.

It reads variable metadata only (names, labels, value labels), never study data.

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

Then, from this folder:

```sh
uv run topic-tagger tag variables.jsonl --out tags/
```

`variables.jsonl` has one variable per line: `file`, `variable`, and optionally `label`,
`values` (`[value, label]` pairs), `sweep` and `identifier` (true for the participant
identifier, which is tagged by rule without the model). The output folder gets
`tags.jsonl` (each variable's topics with a confidence from 0 to 1) and `scheme.json` (the
topics used). Every reply is checked, so only topics from the scheme and confidences from
0 to 1 are ever stored; a batch that fails is retried, then its variables are sent one at
a time.

Check what will be sent first, without sending anything (works with Ollama stopped):

```sh
uv run topic-tagger tag variables.jsonl --out tags/ --dry-run
```

`uv run topic-tagger tag --help` lists every option with its default. The ones you are
most likely to change are `--model`, `--batch-size` (variables per request, default 20)
and `--workers` (requests at once, default 2).

**Speed** depends on the model and your machine. A model that does not fit in your GPU's
memory runs partly on the CPU and can take minutes per request; a smaller model, or a
smaller `--batch-size`, helps.

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
