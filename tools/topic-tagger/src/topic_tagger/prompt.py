"""The messages sent to the model for one batch of variables."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from topic_tagger.reply import options_parser, output_parser, reply_model
from topic_tagger.scheme import Scheme
from topic_tagger.variables import Variable

if TYPE_CHECKING:
    from topic_tagger.tiered import Node

#: At most this many value labels are sent per variable, so one variable cannot overflow
#: a request.
MAX_VALUES = 30


def build_messages(scheme: Scheme, batch: list[Variable]) -> list[dict]:
    """Build the chat messages for one batch.

    The system message holds the guidance, the topics and the reply rules; the user message
    lists the variables, one JSON object per line. Each variable gets a short id, its
    position in the batch, so the model never has to copy a variable name back.

    Args:
        scheme: The topic scheme.
        batch: The variables to tag.

    Returns:
        ``[system message, user message]``.
    """
    return [
        {"role": "system", "content": _system(scheme)},
        {"role": "user", "content": _user(batch)},
    ]


def build_option_messages(
    guidance: str, node: Node, batch: list[Variable], show_children_of_options: bool = True
) -> list[dict]:
    """Build the chat messages for one tier: the variables, and only ``node``'s children.

    Args:
        guidance: The scheme's instructions to the model.
        node: The node whose children are the options (the root at tier 1, an area at tier 2).
        batch: The variables to decide for.
        show_children_of_options: List each option's own children's labels after it, so
            the model can see where a topic lives without reading every description.

    Returns:
        ``[system message, user message]``; the user message is the same as the flat one.
    """
    ids = [c.id for c in node.children]
    lines = [guidance, "", "Options. Use only these ids:"]
    for c in node.children:
        lines.append(f"- {c.id}: {c.label} — {c.description}")
        if show_children_of_options and c.children:
            lines.append("  Includes: " + ", ".join(g.label for g in c.children))
    lines += [
        "",
        "Rules:",
        "- Each line of the next message is one variable: its id, name, label and value labels.",
        "- Reply with every variable's id and the options that apply, each with a confidence "
        "from 0 to 1.",
        "- Give every variable at least one option: the best fit, with a low confidence if "
        "nothing fits well.",
        "",
        options_parser(ids).get_format_instructions(),
    ]
    return [
        {"role": "system", "content": "\n".join(lines)},
        {"role": "user", "content": _user(batch)},
    ]


def reply_schema(scheme: Scheme) -> dict:
    """The JSON schema a reply must match: only scheme topics, confidences from 0 to 1."""
    return reply_model(scheme).model_json_schema()


def _system(scheme: Scheme) -> str:
    lines = [scheme.guidance, "", "Topics, grouped by area. Use only these ids:"]
    for d in scheme.domains:
        lines += ["", f"## {d.label}"]
        lines += [f"- {t.id}: {t.label} — {t.description}" for t in d.topics]
    lines += [
        "",
        "Rules:",
        "- Each line of the next message is one variable: its id, name, label and value labels.",
        "- Reply with every variable's id and its topics, each with a confidence from 0 to 1.",
        "- Give every variable at least one topic. "
        f"If nothing fits, use `{scheme.fallback_topic}` with a low confidence.",
        # Said in words as well as sent as a schema: some hosts ignore the schema.
        "",
        output_parser(scheme).get_format_instructions(),
    ]
    return "\n".join(lines)


def _user(batch: list[Variable]) -> str:
    lines = ["Variables:"]
    for i, v in enumerate(batch):
        values = [f"{value}: {label}" for value, label in v.values[:MAX_VALUES]]
        if len(v.values) > MAX_VALUES:
            values.append(f"… and {len(v.values) - MAX_VALUES} more")
        row = {"id": i, "name": v.variable, "label": v.label or "", "values": values}
        lines.append(json.dumps(row, ensure_ascii=False))
    return "\n".join(lines)
