"""The Python API and the command line give the same tags (feature 006, FR-014, SC-002).

Kept apart from ``test_api.py``, whose tests must write and print nothing: the command
line writes an output folder and prints its summary.
"""

import json
import zlib

import pytest

from conftest import FakeClock, FakeDecisionModel, StubProvider, schema_options
from topic_tagger import tag
from topic_tagger.cli import main
from topic_tagger.variables import read_variables


def score(*parts: str) -> int:
    return zlib.crc32("|".join(parts).encode())


def chat_reply(messages, schema):
    """Each variable gets one or two options, chosen from its name and the options alone."""
    options = schema_options(schema)
    rows = [json.loads(x) for x in messages[1]["content"].split("\n") if x.startswith("{")]
    out = []
    for r in rows:
        ranked = sorted(options, key=lambda o: score(r["name"], o))
        picks = ranked[: 1 + score(r["name"]) % 2]
        out.append(
            {
                "id": r["id"],
                "topics": [
                    {"topic": o, "confidence": round(0.9 - 0.3 * k, 2)} for k, o in enumerate(picks)
                ],
            }
        )
    return json.dumps({"variables": out})


def decision_probability(state, option):
    return (score(state["name"], option) % 100) / 100


def model(kind):
    if kind == "chat":
        return StubProvider(chat_reply)
    return FakeDecisionModel(decision_probability)


@pytest.mark.parametrize("kind", ["chat", "decision"])
@pytest.mark.parametrize("method", ["flat", "tiered"])
def test_the_api_and_the_cli_give_the_same_tags(
    tmp_path, variables_path, small_scheme_path, kind, method, capsys
):
    provider = "ollama" if kind == "chat" else "ollama-decision"
    out = tmp_path / "out"
    argv = [
        "tag",
        str(variables_path),
        "--out",
        str(out),
        "--scheme",
        str(small_scheme_path),
        "--provider",
        provider,
        "--model",
        "fake",
        "--method",
        method,
        "--batch-size",
        "20",
        "--workers",
        "1",
        "--yes",
        "--plain",
    ]
    assert main(argv, provider_factory=lambda args: model(kind), clock=FakeClock()) == 0
    capsys.readouterr()
    cli = {}
    for line in (out / "tags.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        cli[(r["file"], r["variable"])] = (r["topics"], r.get("path"))

    variables = read_variables(variables_path)
    results = tag(
        variables,
        small_scheme_path,
        provider=model(kind),
        model="fake",
        method=method,
        batch_size=20,
        workers=1,
    )
    api = {
        (v.file, v.variable): ([[t.topic, t.confidence] for t in r.tags], r.to_dict().get("path"))
        for v, r in zip(variables, results, strict=True)
    }
    assert len(api) == len(cli) == len(variables)
    assert api == cli
    assert all(r.model == f"{provider}:fake" for r in results)
