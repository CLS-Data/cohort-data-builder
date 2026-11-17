"""Ollama's decision API (``POST /v1/systemone``), for decision models such as Clef.

A decision model does not chat. It is given a ``state`` (here, one variable) and named,
typed questions, and answers each with probabilities. The tagger asks one ``choice``
question per request: which of a tier's options the variable is about. The answer gives
every option a probability, summing to about 1. See
https://docs.ollama.com/capabilities/decision.

How many options a question may offer depends on the model, and the API offers no way to
ask. So nothing is checked here: a host that refuses a question for having too many options
raises ``OptionLimitError`` (see ``_refusal``), and the run stops.

The call is a single JSON POST, so it uses the standard library rather than a client package.
"""

from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from topic_tagger.providers import OptionLimitError, ProviderError
from topic_tagger.providers.openai_compat import LOCAL_HOSTS, is_cloud_model

# A refusal for too many options names the options and a size, and is not about the
# context window (a prompt too long for the model is a different 400). Research R1.
_OPTIONS = re.compile(r"option|choice|criteri", re.IGNORECASE)
_SIZE = re.compile(r"too many|exceed|limit|at most|maximum", re.IGNORECASE)
_NOT_OPTIONS = re.compile(r"context|token", re.IGNORECASE)

#: The name of the one question in each request.
QUESTION = "option"


def choice_body(model: str, state: dict, instructions: str, options: dict[str, str]) -> dict:
    """The ``/v1/systemone`` body asking one ``choice`` question among ``options``.

    Args:
        model: The decision model, e.g. ``clef:cloud``.
        state: What is being judged, as JSON (here, one variable).
        instructions: The question.
        options: ``{option id: description}``; how many a model takes is up to the model.
    """
    return {
        "model": model,
        "state": state,
        "questions": {
            QUESTION: {"type": "choice", "instructions": instructions, "criteria": options}
        },
    }


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

    def decide(self, state: dict, instructions: str, options: dict[str, str]) -> dict[str, float]:
        """Ask which of ``options`` fits ``state``, as one ``choice`` question.

        Args:
            state: What is being judged, as JSON (here, one variable).
            instructions: The question.
            options: ``{option id: description}``.

        Returns:
            ``{option id: probability}``, summing to about 1.

        Raises:
            OptionLimitError: If the model refused the question for its number of options.
            ProviderError: If a request fails, times out, or leaves an option without a
                probability.
        """
        body = choice_body(self.model, state, instructions, options)
        try:
            reply = self._call("POST", "/systemone", body)
        except ProviderError as e:
            refusal = _refusal(e, len(options))
            if refusal is not None:
                raise refusal from e
            raise
        answer = reply.get("answers", {}).get(QUESTION, {})
        probabilities = answer.get("probabilities") or {}
        got = {}
        for option in options:
            try:
                got[option] = float(probabilities[option])
            except (KeyError, TypeError, ValueError) as e:
                raise ProviderError(f"the decision model gave no probability for {option}") from e
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
            text = _error_text(e)
            detail = f"HTTP {e.code}: {text}" if text else f"HTTP {e.code}"
            raise ProviderError(f"the host answered with an error: {detail}") from e
        except TimeoutError as e:
            raise ProviderError("the request timed out") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError | socket.timeout):
                raise ProviderError("the request timed out") from e
            raise ProviderError(f"Ollama is not reachable at {self.base_url}") from e
        except json.JSONDecodeError as e:
            raise ProviderError("the host did not answer with JSON") from e


def _error_text(e: urllib.error.HTTPError) -> str:
    """The ``error`` field of an error reply, or its text, or ``""``."""
    try:
        raw = e.read().decode("utf-8", "replace")
    except Exception:  # an error body that cannot be read is no reason to fail differently
        return ""
    try:
        return str(json.loads(raw).get("error", "")) or raw.strip()
    except (json.JSONDecodeError, AttributeError):
        return raw.strip()


def _refusal(error: ProviderError, options: int) -> OptionLimitError | None:
    """An ``OptionLimitError`` when ``error`` is a refusal for too many options, else None."""
    cause = error.__cause__
    if not isinstance(cause, urllib.error.HTTPError) or cause.code not in (400, 413):
        return None
    text = str(error).split(f"HTTP {cause.code}: ", 1)[-1]
    if _OPTIONS.search(text) and _SIZE.search(text) and not _NOT_OPTIONS.search(text):
        return OptionLimitError(cause.code, text, options)
    return None
