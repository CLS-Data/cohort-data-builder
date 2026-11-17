"""The Ollama decision provider: Clef through POST /v1/systemone (feature 004)."""

import contextlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from topic_tagger.providers import ProviderError, get_provider
from topic_tagger.providers.ollama_decision import OllamaDecisionProvider


class FakeDecisionHost:
    """A local server answering like Ollama: GET /v1/models and POST /v1/systemone.

    Each question is a ``choice``: ``probability(state, option)`` gives each option's
    probability; ``status`` and ``delay`` drive the failure cases; ``drop`` names options
    left out of the probabilities.
    """

    def __init__(self, models=("clef:cloud",), probability=lambda state, q: 0.5):
        self.models = list(models)
        self.probability = probability
        self.status = 200
        self.delay = 0.0
        self.drop: set[str] = set()
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, body, status=200):
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                # The client may have given up first (the timeout tests).
                with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                    self.wfile.write(data)

            def do_GET(self):
                fake.requests.append({"path": self.path})
                self._send({"object": "list", "data": [{"id": m} for m in fake.models]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append({"path": self.path, "body": body})
                time.sleep(fake.delay)
                if fake.status != 200:
                    self._send({"error": "boom"}, fake.status)
                    return
                answers = {}
                for name, q in body["questions"].items():
                    probs = {
                        o: fake.probability(body["state"], o)
                        for o in q["criteria"]
                        if o not in fake.drop
                    }
                    best = max(probs, key=probs.get) if probs else None
                    answers[name] = {
                        "type": "choice",
                        "choice": best,
                        "probabilities": probs,
                        "confidence": 0.9,
                    }
                self._send({"model": body["model"], "answers": answers, "usage": {}})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # Request threads are joined on close, so none is left writing at exit.
        self.server.daemon_threads = False
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def host():
    server = FakeDecisionHost()
    yield server
    server.close()


def provider(url, model="clef:cloud", timeout=5):
    return OllamaDecisionProvider(base_url=url, model=model, timeout=timeout)


STATE = {"name": "smk", "label": "Smokes", "values": ["1: Yes"]}


def test_decide_asks_one_choice_question_and_returns_its_probabilities(host):
    host.probability = lambda state, o: {"smoking": 0.9, "alcohol": 0.1}[o]
    options = {"smoking": "Smoking: tobacco use.", "alcohol": "Alcohol: drinking."}
    got = provider(host.url).decide(STATE, "Which topic is it about?", options)
    assert got == {"smoking": 0.9, "alcohol": 0.1}
    request = host.requests[-1]
    assert request["path"] == "/v1/systemone"
    assert request["body"] == {
        "model": "clef:cloud",
        "state": STATE,
        "questions": {
            "option": {
                "type": "choice",
                "instructions": "Which topic is it about?",
                "criteria": options,
            }
        },
    }


def test_check_names_a_missing_model_and_how_to_get_it(host):
    provider(host.url).check()
    with pytest.raises(ProviderError) as err:
        provider(host.url, model="clef").check()
    assert "model clef is not installed; run: ollama pull clef" in str(err.value)


def test_check_says_when_ollama_is_not_reachable():
    with pytest.raises(ProviderError) as err:
        provider("http://127.0.0.1:9/v1").check()
    assert "Ollama is not reachable at http://127.0.0.1:9/v1" in str(err.value)


def test_an_error_status_a_timeout_or_a_missing_answer_is_a_provider_error(host):
    host.status = 500
    options = {"a": "A", "b": "B"}
    with pytest.raises(ProviderError, match="500"):
        provider(host.url).decide(STATE, "Which?", options)
    host.status, host.drop = 200, {"b"}
    with pytest.raises(ProviderError, match="no probability for b"):
        provider(host.url).decide(STATE, "Which?", options)
    host.drop, host.delay = set(), 1.0
    with pytest.raises(ProviderError, match="timed out"):
        provider(host.url, timeout=0.2).decide(STATE, "Which?", options)


@pytest.mark.parametrize(
    "url,model,remote",
    [
        ("http://localhost:11434/v1", "clef:cloud", True),
        ("http://localhost:11434/v1", "clef:27b-cloud", True),
        ("http://localhost:11434/v1", "clef", False),
        ("https://ollama.example.org/v1", "clef", True),
    ],
)
def test_cloud_models_and_other_hosts_are_remote(url, model, remote):
    assert provider(url, model=model).is_remote() is remote


def test_it_is_registered_as_ollama_decision():
    p = get_provider(
        "ollama-decision", base_url="http://localhost:11434/v1", model="clef", timeout=5
    )
    assert isinstance(p, OllamaDecisionProvider)


# --- No built-in option limit; a model's refusal is recognised (feature 005, US2) -------
# These patch urlopen rather than serving HTTP, so they run anywhere.

import io  # noqa: E402
import urllib.error  # noqa: E402

from topic_tagger.providers import OptionLimitError  # noqa: E402


class Reply:
    """What urlopen returns: a context manager with ``read()``."""

    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.body


def answering(monkeypatch):
    sent = []

    def urlopen(request, timeout):
        body = json.loads(request.data)
        sent.append(body)
        criteria = body["questions"]["option"]["criteria"]
        return Reply({"answers": {"option": {"probabilities": dict.fromkeys(criteria, 0.01)}}})

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return sent


def refusing(monkeypatch, status, error):
    def urlopen(request, timeout):
        body = io.BytesIO(json.dumps({"error": error}).encode())
        raise urllib.error.HTTPError(request.full_url, status, "Bad Request", {}, body)

    monkeypatch.setattr("urllib.request.urlopen", urlopen)


OPTIONS_27 = {f"t{i}": f"T{i}" for i in range(27)}


def test_any_number_of_options_is_sent(monkeypatch):
    sent = answering(monkeypatch)
    got = provider("http://localhost:11434/v1").decide(STATE, "Which?", OPTIONS_27)
    assert len(got) == 27 and len(sent[0]["questions"]["option"]["criteria"]) == 27


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (400, "too many options for choice question"),
        (413, "criteria exceed the maximum for this model"),
        (400, "choice questions take at most 26 options"),
    ],
)
def test_a_refusal_for_too_many_options_is_an_option_limit_error(monkeypatch, status, error):
    refusing(monkeypatch, status, error)
    with pytest.raises(OptionLimitError) as err:
        provider("http://localhost:11434/v1").decide(STATE, "Which?", OPTIONS_27)
    e = err.value
    assert (e.status, e.host_message, e.options) == (status, error, 27)
    assert isinstance(e, ProviderError) and error in str(e)


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (400, "prompt exceeds context window"),
        (400, "prompt for choice question exceeds the model's context window"),
        (400, "token limit exceeded for options"),
        (500, "too many options"),
    ],
)
def test_other_errors_stay_plain_provider_errors(monkeypatch, status, error):
    refusing(monkeypatch, status, error)
    with pytest.raises(ProviderError) as err:
        provider("http://localhost:11434/v1").decide(STATE, "Which?", OPTIONS_27)
    assert not isinstance(err.value, OptionLimitError)
    assert error in str(err.value) and str(status) in str(err.value)
