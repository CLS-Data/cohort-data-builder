"""Checking the model's reply: only scheme topics, confidences from 0 to 1."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

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
    try:
        reply = reply_model(scheme).model_validate_json(text)
    except ValidationError as e:
        raise ReplyError(f"the reply does not match the schema: {e.error_count()} problems") from e

    tags: dict[int, list[tuple[str, float]]] = {}
    for v in reply.variables:
        if not 0 <= v.id < batch_size:
            raise ReplyError(f"the reply names variable {v.id}, outside the batch")
        best: dict[str, float] = {}
        for t in v.topics:
            best[t.topic] = max(best.get(t.topic, 0.0), round(t.confidence, 2))
        if best:
            tags[v.id] = sorted(best.items(), key=lambda kv: (-kv[1], scheme.topic_number(kv[0])))
    return tags
