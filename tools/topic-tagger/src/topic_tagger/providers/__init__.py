"""Model hosts. Each one is a ``Provider``; ``get_provider`` picks one by name.

To add a host, write a class with the three methods of ``Provider`` and register it in
``get_provider``. A host with an OpenAI-compatible API needs no new class: register
``OpenAICompatProvider`` with the host's own wording for its error messages, or none for
neutral ones. Its API key, if any, comes from ``TOPIC_TAGGER_API_KEY``.
"""

from __future__ import annotations

from typing import Protocol


class ProviderError(Exception):
    """The host could not be reached, or did not answer usefully."""


class Provider(Protocol):
    """What the tool needs from a model host."""

    def check(self) -> None:
        """Raise ProviderError unless the host is reachable and has the model."""

    def is_remote(self) -> bool:
        """True when requests leave the maintainer's machine."""

    def complete(self, messages: list[dict], schema: dict) -> str:
        """Send chat messages, asking for a reply that matches the JSON schema.

        Returns:
            The reply's text. Raises ProviderError on any failure.
        """


def get_provider(
    name: str, *, base_url: str, model: str, timeout: float, api_key: str | None = None
) -> Provider:
    """Make the named provider.

    Args:
        name: The provider's name, e.g. ``ollama``.
        base_url: Where the host's API is.
        model: The model name on the host.
        timeout: Seconds before a request is abandoned.
        api_key: The key, for hosts that need one.

    Raises:
        ProviderError: If the name is not known.
    """
    from topic_tagger.providers.openai_compat import OpenAICompatProvider

    # Each host's own wording for its messages, and its own rules for what is remote.
    providers = {
        "ollama": (
            OpenAICompatProvider,
            {"host": "Ollama", "install": "ollama pull {model}", "remote_suffix": "-cloud"},
        ),
    }
    if name not in providers:
        raise ProviderError(f"unknown provider '{name}'; known: {', '.join(providers)}")
    cls, extra = providers[name]
    return cls(base_url=base_url, model=model, timeout=timeout, api_key=api_key, **extra)
