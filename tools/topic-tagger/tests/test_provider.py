import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from topic_tagger.providers import ProviderError, get_provider
from topic_tagger.providers.openai_compat import OpenAICompatProvider

SCHEMA = {"type": "object", "properties": {"variables": {"type": "array"}}}


class FakeOllama:
    """A local HTTP server that answers like Ollama's OpenAI-compatible API."""

    def __init__(self, models=("gpt-oss:20b",), content='{"variables": []}', delay=0.0):
        self.models = list(models)
        self.content = content
        self.delay = delay
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, body):
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                fake.requests.append({"path": self.path, "headers": dict(self.headers)})
                self._send(
                    {
                        "object": "list",
                        "data": [
                            {"id": m, "object": "model", "created": 0, "owned_by": "library"}
                            for m in fake.models
                        ],
                    }
                )

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append(
                    {"path": self.path, "body": body, "headers": dict(self.headers)}
                )
                time.sleep(fake.delay)
                self._send(
                    {
                        "id": "c1",
                        "object": "chat.completion",
                        "created": 0,
                        "model": body["model"],
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {"role": "assistant", "content": fake.content},
                            }
                        ],
                    }
                )

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake():
    server = FakeOllama()
    yield server
    server.close()


def provider(url, model="gpt-oss:20b", **kw):
    return OpenAICompatProvider(base_url=url, model=model, timeout=kw.pop("timeout", 5), **kw)


def test_check_passes_when_the_model_is_installed(fake):
    provider(fake.url).check()
    assert fake.requests[0]["path"] == "/v1/models"


def test_check_names_a_missing_model_and_how_to_get_it(fake):
    with pytest.raises(ProviderError) as err:
        provider(fake.url, model="llama9").check()
    assert "llama9 is not installed" in str(err.value)
    assert "ollama pull llama9" in str(err.value)


def test_check_says_when_the_host_is_not_reachable():
    url = "http://127.0.0.1:9/v1"  # the discard port: nothing listens there
    with pytest.raises(ProviderError) as err:
        provider(url).check()
    assert f"is not reachable at {url}" in str(err.value)


def test_complete_sends_the_schema_and_returns_the_content(fake):
    fake.content = '{"variables": [{"id": 0, "topics": []}]}'
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    out = provider(fake.url).complete(messages, SCHEMA)
    assert out == fake.content
    body = fake.requests[-1]["body"]
    assert fake.requests[-1]["path"] == "/v1/chat/completions"
    assert body["model"] == "gpt-oss:20b"
    assert body["messages"] == messages
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "tags", "schema": SCHEMA, "strict": True},
    }


def test_the_api_key_defaults_to_a_placeholder_and_can_be_given(fake):
    provider(fake.url).check()
    assert fake.requests[-1]["headers"]["Authorization"] == "Bearer ollama"
    provider(fake.url, api_key="sekret").check()
    assert fake.requests[-1]["headers"]["Authorization"] == "Bearer sekret"


def test_a_slow_reply_times_out_as_a_provider_error(fake):
    fake.delay = 1.0
    with pytest.raises(ProviderError) as err:
        provider(fake.url, timeout=0.2).complete([{"role": "user", "content": "u"}], SCHEMA)
    assert "timed out" in str(err.value)


@pytest.mark.parametrize(
    "url, model, remote",
    [
        ("http://localhost:11434/v1", "gpt-oss:20b", False),
        ("http://127.0.0.1:11434/v1", "gpt-oss:20b", False),
        ("http://[::1]:11434/v1", "gpt-oss:20b", False),
        ("http://localhost:11434/v1", "gpt-oss:120b-cloud", True),
        ("https://ollama.com/v1", "gpt-oss:20b", True),
        ("http://gpu-box.lan:11434/v1", "gpt-oss:20b", True),
    ],
)
def test_is_remote(url, model, remote):
    assert provider(url, model=model).is_remote() is remote


def test_get_provider_knows_ollama():
    p = get_provider("ollama", base_url="http://localhost:11434/v1", model="m", timeout=3)
    assert isinstance(p, OpenAICompatProvider)


def test_get_provider_lists_the_known_ones_for_an_unknown_name():
    with pytest.raises(ProviderError) as err:
        get_provider("nope", base_url="http://x/v1", model="m", timeout=3)
    assert "nope" in str(err.value) and "ollama" in str(err.value)
