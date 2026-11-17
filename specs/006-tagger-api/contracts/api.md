# Contract: the Python API

Everything here is importable from `topic_tagger` and listed in `topic_tagger.__all__`.
Anything else in the package is internal and may change without notice.

```python
from topic_tagger import (
    tag, classify, Tagger, Result, Results, Tag,
    Variable, Scheme, load_scheme, parse_scheme,
    SchemeError, ProviderError, OptionLimitError, RemoteModelError,
)
```

## `tag`

```python
def tag(
    inputs: Iterable[str | Variable | dict],
    scheme: Scheme | str | os.PathLike | None = None,
    *,
    provider: str | Provider | DecisionProvider | None = None,
    model: str | None = None,
    method: Literal["flat", "tiered"] | None = None,
    descend_at: float | None = None,
    max_follow: int | None = None,
    keep_at: float | None = None,
    base_url: str = "http://localhost:11434/v1",
    api_key: str | None = None,
    timeout: float = 120,
    batch_size: int = 20,
    workers: int = 2,
    retries: int = 2,
    allow_remote: bool = False,
    check: bool = True,
) -> Results
```

`tag(...)` is the same as `Tagger(scheme, ...).tag(inputs)`.

**Arguments:**
- `None` means "not given": the scheme's `[run]` applies, else the default (FR-006).
- `api_key` defaults to the `TOPIC_TAGGER_API_KEY` environment variable, as on the
  command line.

**Raises:**
- `SchemeError`: bad scheme;
- `ValueError`: bad setting or bad dict input;
- `TypeError`: unsupported input;
- `RemoteModelError`: cloud model without `allow_remote=True`;
- `ProviderError`: host unreachable or model missing;
- `OptionLimitError`: model refused a question.

## `classify`

```python
def classify(input: str | Variable | dict, scheme=None, **options) -> Result
```

`classify(...)` is the same as `tag([input], scheme, **options)[0]`.

## `Tagger`

```python
class Tagger:
    def __init__(self, scheme=None, *, <the same keyword arguments as tag>) -> None
    scheme: Scheme
    settings: dict      # resolved values
    sources: dict       # "call" | "file" | "default" per setting
    notes: list[str]
    def tag(self, inputs) -> Results
    def classify(self, input) -> Result
```

**Constructing a tagger:**
- It loads the scheme, resolves and checks the settings, and makes the provider.
- It makes no network request, and raises the same `SchemeError` and `ValueError` as
  `tag`.

**Calling it:**
- The first non-empty call checks the host, unless `check=False`.
- Each call checks remote consent.
- An empty call returns empty `Results` without any request.

## `parse_scheme` and `load_scheme`

```python
def parse_scheme(text: str, source: str = "<text>") -> Scheme
def load_scheme(path: str | os.PathLike) -> Scheme
```

- **Same checks:** both apply the checks `check-scheme` applies.
- **Same hash:** the same content gives the same hash whichever way it is loaded.
- **Errors:** `SchemeError` messages start with `source` (or the path).

## Results

See [data-model.md](../data-model.md) for the fields of `Result`, `Results` and `Tag`.

**Ordering and tags:**
- Results are in input order.
- `tags` are strongest first, and every `topic` is a leaf id of the scheme.

**Equivalence with the command line (FR-014):** for the same scheme, settings and model
replies, `[t.topic for t in result.tags]` and their confidences equal the `topics` of that
variable's record in `tags.jsonl`. The same holds for `path`.

## Guarantees

- **No side effects:** no files are created, nothing is written to stdout or stderr, and
  there are no prompts and no `sys.exit` (FR-011).
- **Retries:** per-input failures after retries are results, not exceptions.
- **Concurrency:** one call at a time per `Tagger`. Separate taggers are independent.
