"""Model hosts. Each one is a ``Provider``; ``get_provider`` picks one by name.

There are two kinds of host. A chat host is a ``Provider``: it completes chat messages. A
decision host (``ollama-decision``, for models such as Clef) is a ``DecisionProvider``: it
answers a choice question about one state, and is used only through
``tiered.DecisionDecider``.

To add a host, write a class with the three methods of ``Provider`` and register it in
``get_provider``. A host with an OpenAI-compatible API needs no new class: register
``OpenAICompatProvider`` with the host's own wording for its error messages, or none for
neutral ones. Its API key, if any, comes from ``TOPIC_TAGGER_API_KEY``.
"""

from __future__ import annotations

from typing import Protocol


class ProviderError(Exception):
    """The host could not be reached, or did not answer usefully."""


class OptionLimitError(ProviderError):
    """The model refused a question because it offers too many options.

    The limit is the model's, not the tagger's, and differs between models. Asking the same
    question again cannot succeed, so the run stops (see ``runner``) instead of retrying.

    Attributes:
        status: The HTTP status the host answered with.
        host_message: The host's own error text.
        options: How many options the refused question offered.
        question: Which question it was, in words; filled in by the tier walk.
        advice: What the user can change; filled in by the tier walk.
    """

    def __init__(self, status: int, host_message: str, options: int):
        self.status = status
        self.host_message = host_message
        self.options = options
        self.question = ""
        self.advice = ""
        super().__init__(
            f"the model refused a question with {options} options: HTTP {status}: {host_message}"
        )


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


class DecisionProvider(Protocol):
    """What the tool needs from a decision-model host."""

    def check(self) -> None:
        """Raise ProviderError unless the host is reachable and has the model."""

    def is_remote(self) -> bool:
        """True when requests leave the maintainer's machine."""

    def decide(self, state: dict, instructions: str, options: dict[str, str]) -> dict[str, float]:
        """Ask which of ``options`` fits ``state``; return each option's probability."""


def get_provider(
    name: str, *, base_url: str, model: str, timeout: float, api_key: str | None = None
) -> Provider | DecisionProvider:
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
    from topic_tagger.providers.ollama_decision import OllamaDecisionProvider
    from topic_tagger.providers.openai_compat import OpenAICompatProvider

    if name == "ollama-decision":
        return OllamaDecisionProvider(
            base_url=base_url, model=model, timeout=timeout, api_key=api_key
        )

    # Each host's own wording for its messages, and its own rules for what is remote.
    providers = {
        "ollama": (
            OpenAICompatProvider,
            {"host": "Ollama", "install": "ollama pull {model}", "remote_suffix": "-cloud"},
        ),
    }
    if name not in providers:
        known = ", ".join([*providers, "ollama-decision"])
        raise ProviderError(f"unknown provider '{name}'; known: {known}")
    cls, extra = providers[name]
    return cls(base_url=base_url, model=model, timeout=timeout, api_key=api_key, **extra)
