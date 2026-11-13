"""Checking the model's reply: only scheme topics, confidences from 0 to 1."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import Literal

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from topic_tagger.scheme import Scheme


class ReplyError(Exception):
    """The reply cannot be used; the batch is retried."""


@lru_cache(maxsize=8)
def _model(topic_ids: tuple[str, ...]) -> type[BaseModel]:
    forbid = ConfigDict(extra="forbid")
    tag = create_model(
        "TopicTag",
        __config__=forbid,
        topic=(Literal[topic_ids], ...),
        confidence=(float, Field(ge=0, le=1)),
    )
    var = create_model("VariableTags", __config__=forbid, id=(int, ...), topics=(list[tag], ...))
    return create_model("Reply", __config__=forbid, variables=(list[var], ...))


def reply_model(scheme: Scheme) -> type[BaseModel]:
    """The pydantic model of a reply, with ``topic`` limited to the scheme's ids.

    The same model gives the JSON schema sent to the host and the check applied to what
    comes back, so the two cannot disagree.
    """
    return _model(tuple(scheme.topic_ids))


def output_parser(scheme: Scheme) -> PydanticOutputParser:
    """LangChain's parser for a reply.

    It reads JSON, in a code fence or not, and checks it against ``reply_model``. Its
    format instructions go in the prompt.
    """
    return _parser(tuple(scheme.topic_ids))


@lru_cache(maxsize=64)
def _parser(topic_ids: tuple[str, ...]) -> PydanticOutputParser:
    return PydanticOutputParser(pydantic_object=_model(topic_ids))


def options_parser(option_ids: Sequence[str]) -> PydanticOutputParser:
    """LangChain's parser for a reply whose ``topic`` may only be one of ``option_ids``.

    Used for one tier of tiered tagging, where the options are a node's children.
    """
    return _parser(tuple(option_ids))


def options_schema(option_ids: Sequence[str]) -> dict:
    """The JSON schema of a reply limited to ``option_ids``."""
    return _model(tuple(option_ids)).model_json_schema()


def parse_reply(text: str, scheme: Scheme, batch_size: int) -> dict[int, list[tuple[str, float]]]:
    """Check a reply and return each variable's tags.

    Args:
        text: The reply's text.
        scheme: The topic scheme.
        batch_size: How many variables were sent; ids must be below it.

    Returns:
        ``{id: [(topic, confidence), …]}``, strongest first with ties in scheme order and
        confidences rounded to 2 places. A topic given twice keeps its highest confidence.
        Variables with no tags are left out, so the caller treats them as missing.

    Raises:
        ReplyError: If the reply is not valid JSON, names a topic outside the scheme, gives
            a confidence outside 0–1, or an id outside the batch.
    """
    return parse_options_reply(text, scheme.topic_ids, batch_size, scheme.topic_number)


def parse_options_reply(
    text: str, option_ids: Sequence[str], batch_size: int, order: Callable[[str], int]
) -> dict[int, list[tuple[str, float]]]:
    """Check a reply whose topics may only be ``option_ids``, and return each variable's.

    Args:
        text: The reply's text.
        option_ids: The ids the reply may use (a scheme's topics, or a node's children).
        batch_size: How many variables were sent; ids must be below it.
        order: Gives each option's position, to break ties between equal confidences.

    Returns:
        As ``parse_reply``.

    Raises:
        ReplyError: As ``parse_reply``, for ids outside ``option_ids``.
    """
    try:
        reply = options_parser(option_ids).parse(text)
    except OutputParserException as e:
        cause = e.__cause__
        if isinstance(cause, ValidationError):
            first = cause.errors()[0]
            where = ".".join(str(part) for part in first["loc"])
            raise ReplyError(
                f"the reply does not match the schema ({cause.error_count()} problems), first "
                f"at {where}: {first['input']!r}: {first['msg']}"
            ) from e
        raise ReplyError("the reply is not JSON") from e

    tags: dict[int, list[tuple[str, float]]] = {}
    for v in reply.variables:
        if not 0 <= v.id < batch_size:
            raise ReplyError(f"the reply names variable {v.id}, outside the batch")
        best: dict[str, float] = {}
        for t in v.topics:
            best[t.topic] = max(best.get(t.topic, 0.0), round(t.confidence, 2))
        if best:
            tags[v.id] = sorted(best.items(), key=lambda kv: (-kv[1], order(kv[0])))
    return tags
