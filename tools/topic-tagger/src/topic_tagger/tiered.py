"""Tiered tagging: walk the taxonomy one tier at a time (feature 004).

The scheme becomes a tree of ``Node``s: a root, its areas (the scheme's domains), and their
topics. Tagging tiered asks, for each variable, which areas apply, then which topics within
each area that passed the threshold, and so on for deeper trees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from topic_tagger.prompt import MAX_VALUES, build_option_messages
from topic_tagger.providers import DecisionProvider, Provider, ProviderError
from topic_tagger.reply import ReplyError, options_schema, parse_options_reply
from topic_tagger.scheme import Scheme
from topic_tagger.variables import Variable


@dataclass(frozen=True)
class Node:
    """One option in the taxonomy: an area (with children) or a topic (a leaf).

    Attributes:
        id: The area or topic id; ``""`` for the root.
        label: Its label.
        description: Its description.
        children: Its children, in scheme order; empty for a topic.
    """

    id: str
    label: str
    description: str
    children: tuple[Node, ...] = ()

    @property
    def is_leaf(self) -> bool:
        """True for a topic: something a variable can be tagged with."""
        return not self.children

    def find(self, node_id: str) -> Node | None:
        """The node with this id, here or below, or None."""
        if self.id == node_id:
            return self
        for child in self.children:
            found = child.find(node_id)
            if found is not None:
                return found
        return None


def build_tree(scheme: Scheme) -> Node:
    """The scheme as a tree: root → one node per domain → one leaf per topic."""
    return Node(
        "",
        scheme.name,
        "",
        tuple(
            Node(
                d.id,
                d.label,
                d.description,
                tuple(Node(t.id, t.label, t.description) for t in d.topics),
            )
            for d in scheme.domains
        ),
    )


def flat_tree(scheme: Scheme) -> Node:
    """The scheme as one tier: the root's children are every topic.

    Walking it asks every topic at once, as the flat method does; a decision model uses it
    to tag flat with the same questions and keep rule as tiered.
    """
    return Node(
        "", scheme.name, "", tuple(Node(t.id, t.label, t.description) for t in scheme.topics)
    )


Tags = list[tuple[str, float]]


class Decider(Protocol):
    """Answers one tier: which of a node's children apply to each variable."""

    def decide(self, node: Node, variables: list[Variable]) -> tuple[dict[int, Tags], int]:
        """Decide among ``node.children`` for each variable.

        Args:
            node: The node whose children are the options.
            variables: The variables to decide for; ids in the answer are their positions.

        Returns:
            ``({position: [(child id, confidence), …]}, requests sent)``. Variables it could
            not answer are left out, so the walk asks them again alone.

        Raises:
            ReplyError, ProviderError: When the whole request failed; the walk retries it.
        """


class ChatDecider:
    """Decides with a chat model: one request per tier for a group of variables.

    Args:
        provider: The model host.
        guidance: The scheme's instructions to the model.
    """

    def __init__(self, provider: Provider, guidance: str):
        self.provider = provider
        self.guidance = guidance

    def decide(self, node: Node, variables: list[Variable]) -> tuple[dict[int, Tags], int]:
        """Send one request listing ``node``'s children and check the reply against them."""
        ids = [c.id for c in node.children]
        position = {c: i for i, c in enumerate(ids)}
        messages = build_option_messages(self.guidance, node, variables)
        text = self.provider.complete(messages, options_schema(ids))
        return parse_options_reply(text, ids, len(variables), position.__getitem__), 1


class DecisionDecider:
    """Decides with a decision model such as Clef: one variable per request.

    Each option of the tier becomes a yes/no (``noul``) question, "Is this survey variable
    about <label>? <description>", and its probability is the confidence. Yes/no questions
    give each option its own probability, so a variable can belong to several areas or
    topics; a single ``choice`` question would make them compete.

    Args:
        provider: The decision-model host.
        keep_at: Topics below this probability are dropped, but the strongest is always kept.
            Areas are all returned; the walk decides which to follow.
    """

    def __init__(self, provider: DecisionProvider, keep_at: float = 0.3):
        self.provider = provider
        self.keep_at = keep_at

    def decide(self, node: Node, variables: list[Variable]) -> tuple[dict[int, Tags], int]:
        """Ask each variable about ``node``'s children, one request (or more) per variable.

        A variable whose request fails is left out, so the walk asks it again alone; the
        others keep their answers.
        """
        questions = {c.id: _question(c) for c in node.children}
        leaf = {c.id: c.is_leaf for c in node.children}
        position = {c.id: i for i, c in enumerate(node.children)}
        got: dict[int, Tags] = {}
        sent = 0
        error: ProviderError | None = None
        for i, v in enumerate(variables):
            sent += self.provider.requests_for(len(questions))
            try:
                probs = self.provider.decide(_state(v), questions)
            except ProviderError as e:
                error = e
                continue
            ranked = sorted(probs.items(), key=lambda kv: (-kv[1], position[kv[0]]))
            leaves = [(c, round(p, 2)) for c, p in ranked if leaf[c]]
            kept = [(c, p) for c, p in leaves if p >= self.keep_at] or leaves[:1]
            areas = [(c, round(p, 2)) for c, p in ranked if not leaf[c]]
            got[i] = sorted(kept + areas, key=lambda kv: (-kv[1], position[kv[0]]))
        if not got and error is not None:
            raise error  # nothing answered: let the walk retry the whole group
        return got, sent


def _state(v: Variable) -> dict:
    """One variable as the decision model's state, with value labels capped as in prompts."""
    values = [f"{value}: {label}" for value, label in v.values[:MAX_VALUES]]
    if len(v.values) > MAX_VALUES:
        values.append(f"… and {len(v.values) - MAX_VALUES} more")
    return {"name": v.variable, "label": v.label or "", "values": values}


def _question(option: Node) -> str:
    text = f"Is this survey variable about {option.label}? {option.description}"
    if option.children:
        text += " It includes: " + ", ".join(c.label for c in option.children) + "."
    return text


@dataclass
class WalkResult:
    """What tagging one batch tier by tier gave.

    Attributes:
        tags: ``{position: [(topic, confidence), …]}``, strongest first; variables with no
            tags are left out.
        paths: ``{position: [(area, confidence), …]}``: the areas followed, in order.
        failed: Positions of variables that ended with no tags.
        requests_by_tier: Requests sent at each tier, index 0 being tier 1.
        retries: Group requests retried.
        singles: Variables asked alone after their group's request failed or left them out.
        last_error: The last error seen, if any.
    """

    tags: dict[int, Tags] = field(default_factory=dict)
    paths: dict[int, Tags] = field(default_factory=dict)
    failed: list[int] = field(default_factory=list)
    requests_by_tier: list[int] = field(default_factory=list)
    retries: int = 0
    singles: int = 0
    last_error: str = ""


def walk(
    root: Node,
    batch: list[Variable],
    decider: Decider,
    descend_at: float,
    max_areas: int,
    retries: int = 2,
) -> WalkResult:
    """Tag a batch by walking the tree from ``root``, one tier at a time.

    At each node, one request (through ``decider``) asks the node's variables which of its
    children apply. Children that are topics become tags. Children that are areas are
    followed when their confidence is at least ``descend_at``, at most ``max_areas`` of them
    (0 means no cap); the strongest is always followed, so no variable stalls. Each followed
    area is then asked once, for all the batch's variables routed to it.

    Args:
        root: The tree's root.
        batch: The variables.
        decider: Answers each tier.
        descend_at: The confidence an area needs to be followed.
        max_areas: Most areas followed per variable at each node; 0 for no cap.
        retries: Retries of a failed group request before its variables are asked alone.

    Returns:
        The tags, paths, failures and request counts.
    """
    result = WalkResult(requests_by_tier=[0] * _height(root))
    order = _positions(root)
    best: dict[int, dict[str, float]] = {}
    # Groups waiting to be asked, by node id: (node, tier, [(position, incoming confidence)]).
    # A node has one parent, so every group is complete before it is asked.
    pending: dict[str, tuple[Node, int, list[tuple[int, float]]]] = {}

    def reach(node: Node, tier: int, i: int, conf: float) -> None:
        if node.is_leaf:
            tags = best.setdefault(i, {})
            tags[node.id] = max(tags.get(node.id, 0.0), conf)
            return
        if node is not root:
            result.paths.setdefault(i, []).append((node.id, conf))
        pending.setdefault(node.id, (node, tier, []))[2].append((i, conf))

    for i in range(len(batch)):
        reach(root, 0, i, 1.0)
    while pending:
        node, tier, members = pending.pop(next(iter(pending)))
        if len(node.children) == 1:
            # Nothing to choose: route straight on, keeping the confidence it arrived with.
            for i, conf in members:
                reach(node.children[0], tier + 1, i, conf)
            continue
        answers = _ask(decider, node, [i for i, _ in members], batch, tier, retries, result)
        for i, _ in members:
            chosen = answers.get(i, [])
            for child_id, conf in chosen:
                child = _child(node, child_id)
                if child.is_leaf:
                    reach(child, tier + 1, i, conf)
            areas = [(c, conf) for c, conf in chosen if not _child(node, c).is_leaf]
            follow = [(c, conf) for c, conf in areas if conf >= descend_at] or areas[:1]
            if max_areas:
                follow = follow[:max_areas]
            for child_id, conf in follow:
                reach(_child(node, child_id), tier + 1, i, conf)

    for i in range(len(batch)):
        if best.get(i):
            result.tags[i] = sorted(best[i].items(), key=lambda kv: (-kv[1], order[kv[0]]))
        else:
            result.failed.append(i)
    return result


def _ask(decider, node, positions, batch, tier, retries, result) -> dict[int, Tags]:
    """Ask one group, with the same ladder as flat batches: retries, then each one alone."""
    got = None
    for attempt in range(retries + 1):
        try:
            got, sent = decider.decide(node, [batch[i] for i in positions])
            result.requests_by_tier[tier] += sent
            break
        except (ReplyError, ProviderError) as e:
            result.requests_by_tier[tier] += 1
            result.last_error = str(e)
            if attempt < retries:
                result.retries += 1
    answers = {} if got is None else {positions[k]: v for k, v in got.items()}
    for i in [i for i in positions if i not in answers]:
        result.singles += 1
        try:
            one, sent = decider.decide(node, [batch[i]])
            result.requests_by_tier[tier] += sent
        except (ReplyError, ProviderError) as e:
            result.requests_by_tier[tier] += 1
            result.last_error = str(e)
            continue
        if 0 in one:
            answers[i] = one[0]
    return answers


def _child(node: Node, child_id: str) -> Node:
    return next(c for c in node.children if c.id == child_id)


def _height(node: Node) -> int:
    """Tiers below ``node``: 2 for root → areas → topics."""
    return 0 if node.is_leaf else 1 + max(_height(c) for c in node.children)


def _positions(root: Node) -> dict[str, int]:
    """Every node's position in scheme order, for breaking ties between equal confidences."""
    out: dict[str, int] = {}

    def visit(node: Node) -> None:
        out[node.id] = len(out)
        for c in node.children:
            visit(c)

    visit(root)
    return out
