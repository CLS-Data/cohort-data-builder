"""Ollama's decision API (``POST /v1/systemone``), for decision models such as Clef.

A decision model does not chat. It is given a ``state`` (here, one variable) and named,
typed questions, and answers each with a probability. The tagger asks only ``noul``
(yes/no) questions: "is this variable about X?", one per option of a tier. See
https://docs.ollama.com/capabilities/decision.

The call is a single JSON POST, so it uses the standard library rather than a client package.
"""

from __future__ import annotations

import json
import math
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from topic_tagger.providers import ProviderError
from topic_tagger.providers.openai_compat import LOCAL_HOSTS, is_cloud_model

#: Most questions Ollama's cloud accepts in one request; more are split across requests.
MAX_QUESTIONS = 64


class OllamaDecisionProvider:
    """A decision model served by Ollama.

    Args:
        base_url: Ollama's OpenAI-compatible base URL, e.g. ``http://localhost:11434/v1``.
        model: The model, e.g. ``clef:cloud``.
        timeout: Seconds before a request is abandoned.
        api_key: Sent as a bearer token when given (for ollama.com directly).
    """

    def __init__(self, base_url: str, model: str, timeout: float, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.api_key = api_key

    def check(self) -> None:
        """Raise ProviderError unless Ollama answers and lists the model."""
        try:
            listed = self._call("GET", "/models")
        except ProviderError as e:
            if isinstance(e.__cause__, urllib.error.URLError) and not isinstance(
                e.__cause__, urllib.error.HTTPError
            ):
                raise ProviderError(f"Ollama is not reachable at {self.base_url}") from e
            raise
        if self.model not in {m.get("id") for m in listed.get("data", [])}:
            raise ProviderError(
                f"model {self.model} is not installed; run: ollama pull {self.model}"
            )

    def is_remote(self) -> bool:
        """True for a host other than this machine, or a model Ollama runs in its cloud."""
        return urlparse(self.base_url).hostname not in LOCAL_HOSTS or is_cloud_model(self.model)

    @staticmethod
    def requests_for(questions: int) -> int:
        """How many requests ``decide`` sends for this many questions."""
        return max(1, math.ceil(questions / MAX_QUESTIONS))

    def decide(self, state: dict, questions: dict[str, str]) -> dict[str, float]:
        """Ask yes/no questions about one state.

        Args:
            state: What is being judged, as JSON (here, one variable).
            questions: ``{question id: instructions}``.

        Returns:
            ``{question id: probability the answer is yes}``.

        Raises:
            ProviderError: If a request fails, times out, or leaves a question unanswered.
        """
        ids = list(questions)
        got: dict[str, float] = {}
        for start in range(0, len(ids), MAX_QUESTIONS):
            chunk = ids[start : start + MAX_QUESTIONS]
            body = {
                "model": self.model,
                "state": state,
                "questions": {q: {"type": "noul", "instructions": questions[q]} for q in chunk},
            }
            answers = self._call("POST", "/systemone", body).get("answers", {})
            for q in chunk:
                try:
                    got[q] = float(answers[q]["noul"])
                except (KeyError, TypeError, ValueError) as e:
                    raise ProviderError(f"the decision model gave no answer for {q}") from e
        return got

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base_url + path, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        # Retries are the runner's job, with its own rules, so none here.
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise ProviderError(f"the host answered with an error: HTTP {e.code}") from e
        except TimeoutError as e:
            raise ProviderError("the request timed out") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError | socket.timeout):
                raise ProviderError("the request timed out") from e
            raise ProviderError(f"Ollama is not reachable at {self.base_url}") from e
        except json.JSONDecodeError as e:
            raise ProviderError("the host did not answer with JSON") from e
