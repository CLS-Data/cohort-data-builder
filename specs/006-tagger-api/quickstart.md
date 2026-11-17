# Quickstart: validating the Python API

Run from `tools/topic-tagger/`. Steps 1–5 need no model host: they use the test suite's
scripted fakes, or a provider object. Step 6 needs a local Ollama.

## Prerequisites

```sh
cd tools/topic-tagger
uv sync
```

## 1. Tests and lint

```sh
uv run pytest && uv run ruff check . && uv run ruff format --check .
```

Expected: every test passes, including the new `tests/test_api.py`. The CLI tests pass
unchanged (FR-016).

## 2. Three lines, with a provider object (no host)

```python
from topic_tagger import tag


class Fake:  # a decision model that always prefers the first option
    def check(self):
        pass

    def is_remote(self):
        return False

    def decide(self, state, instructions, options):
        first = next(iter(options))
        return {o: (0.9 if o == first else 0.1 / (len(options) - 1)) for o in options}


results = tag(
    ["Do you smoke?", "Household income"],
    "src/topic_tagger/schemes/example-3-tier.toml",
    provider=Fake(),
)
print([r.topics for r in results], results.settings["method"], results.sources)
```

Expected:
- two results, each with one leaf topic;
- `method` is `tiered`, from the file;
- `provider` has source `call`;
- no files appear in the working directory.

## 3. Settings: call over file over default

Run step 2 again with `method="flat"`. Expected: `results.settings["method"] == "flat"`,
`results.sources["method"] == "call"`, and every `r.path is None`.

With the one-tier example (`example-1-tier.toml`) and `method="tiered"`, expected:
`results.notes == ["This taxonomy has one tier: tagging flat."]`.

## 4. Schemes from text

```python
from pathlib import Path
from topic_tagger import parse_scheme, load_scheme

p = Path("src/topic_tagger/schemes/closer.toml")
assert parse_scheme(p.read_text()).hash == load_scheme(p).hash == "3c9f6b4b4ef9"
```

## 5. Errors

Each of these raises the named exception, and prints nothing:

| Call | Raises |
|---|---|
| `tag(["x"], parse_scheme("name = 1"))` | `SchemeError` (at `parse_scheme`) |
| `tag(["x"], provider=Fake(), descend_at=1.5)` | `ValueError: --descend-at must be between 0 and 1` |
| `tag(["x"], provider="ollama", keep_at=0.4)` | `ValueError` (keep-at needs a decision model) |
| `tag([42], provider=Fake())` | `TypeError` naming position 0 |
| a `Fake` whose `is_remote()` is True, without `allow_remote=True` | `RemoteModelError`, and `decide` is never called |
| a `Fake` whose `decide` raises `OptionLimitError(400, "too many options", 107)` | `OptionLimitError` with `.question` filled in |

## 6. Against a real model (optional; local Ollama, fictional text only)

```sh
uv run python -c "
from topic_tagger import tag
r = tag(['Do you smoke?', 'Weight in kg'], provider='ollama-decision',
        model='clef:cloud', allow_remote=True)
print([x.topics for x in r], r.requests_by_tier)"
```

Expected:
- each text gets leaf topics from the bundled scheme, for example `smoking` and
  `anthropometry`;
- the run is tiered, the default for a decision model.

Run the same call without `allow_remote=True`. Expected: `RemoteModelError`.
