"""A host with an OpenAI-compatible chat API: Ollama now, others later.

The class itself is host-neutral. ``get_provider`` gives it a host's name, how to install a
missing model and which model names run remotely, so its messages can be specific.
"""

from __future__ import annotations

from urllib.parse import urlparse

import openai

from topic_tagger.providers import ProviderError

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class OpenAICompatProvider:
    """Calls ``/chat/completions`` with a JSON schema for the reply.

    Args:
        base_url: The API's base URL, e.g. ``http://localhost:11434/v1``.
        model: The model name.
        timeout: Seconds before a request is abandoned.
        api_key: The key; hosts that need none ignore it, so it defaults to a placeholder.
        host: The host's name for messages, e.g. ``Ollama``; None for neutral wording.
        install: A command that installs a missing model, with ``{model}`` in it; None to
            say only that the model is not available.
        remote_suffix: Model names ending in this run on the host's own servers even
            through a local address (Ollama's ``-cloud`` models); None if there are none.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: float,
        api_key: str | None = None,
        host: str | None = None,
        install: str | None = None,
        remote_suffix: str | None = None,
    ):
        self.base_url = base_url
        self.model = model
        self.host = host
        self.install = install
        self.remote_suffix = remote_suffix
        # Retries are the runner's job, with its own rules, so the client makes none.
        self._client = openai.OpenAI(
            base_url=base_url, api_key=api_key or "ollama", timeout=timeout, max_retries=0
        )

    def check(self) -> None:
        """Raise ProviderError unless the host answers and lists the model."""
        try:
            names = {m.id for m in self._client.models.list()}
        except openai.APIConnectionError as e:
            raise ProviderError(self._unreachable()) from e
        except openai.APIError as e:
            raise ProviderError(f"{self.base_url} answered with an error: {e}") from e
        if self.model not in names:
            if self.install:
                command = self.install.format(model=self.model)
                raise ProviderError(f"model {self.model} is not installed; run: {command}")
            raise ProviderError(f"model {self.model} is not available at {self.base_url}")

    def _unreachable(self) -> str:
        if self.host:
            return f"{self.host} is not reachable at {self.base_url}"
        return f"The host at {self.base_url} is not reachable"

    def is_remote(self) -> bool:
        """True for a host other than this machine, or a model the host runs remotely."""
        if urlparse(self.base_url).hostname not in LOCAL_HOSTS:
            return True
        return bool(self.remote_suffix) and self.model.endswith(self.remote_suffix)

    def complete(self, messages: list[dict], schema: dict) -> str:
        """Send the messages and return the reply's text."""
        try:
            reply = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "tags", "schema": schema, "strict": True},
                },
            )
        except openai.APITimeoutError as e:
            raise ProviderError("the request timed out") from e
        except openai.APIConnectionError as e:
            raise ProviderError(self._unreachable()) from e
        except openai.APIError as e:
            raise ProviderError(f"the host answered with an error: {e}") from e
        return reply.choices[0].message.content or ""
