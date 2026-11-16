"""Tiered tagging: walk the taxonomy one tier at a time (features 004 and 005).

The scheme becomes a tree of ``Node``s: a root, its tier-1 categories, and so on down to the
leaves, one to three tiers deep. Tagging tiered asks, for each variable, which tier-1
categories apply, then which categories within each group that passed the threshold, and so
on down to the leaves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from topic_tagger.prompt import MAX_VALUES, build_option_messages
from topic_tagger.providers import DecisionProvider, OptionLimitError, Provider, ProviderError
from topic_tagger.providers.ollama_decision import choice_body
from topic_tagger.reply import ReplyError, options_schema, parse_options_reply
from topic_tagger.scheme import Scheme
from topic_tagger.variables import Variable


@dataclass(frozen=True)
class Node:
    """One option in the taxonomy: a group (with children) or a leaf.

    Attributes:
        id: The category id; ``""`` for the root.
        label: Its label.
        description: Its description; may be empty.
        children: Its children, in scheme order; empty for a leaf.
        is_exit: True for the fallback offered at tier 1: kept only when nothing else is
            found.
    """

    id: str
    label: str
    description: str
    children: tuple[Node, ...] = ()
    is_exit: bool = False

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
    """The taxonomy as a tree of nodes, with the fallback offered at tier 1 as an exit.

    The fallback leaf is moved out of wherever it sits and offered beside the tier-1
    categories, for variables the model cannot place: it is taken like a group (see
    ``walk``) and kept only when nothing else is found. Groups the move leaves empty are
    dropped, all the way up.
    """
    fallback = scheme.fallback_topic

    def convert(c) -> Node | None:
        if c.is_leaf:
            return None if c.id == fallback else Node(c.id, c.label, c.description)
        children = tuple(n for n in map(convert, c.children) if n is not None)
        return Node(c.id, c.label, c.description, children) if children else None

    tier1 = [n for n in map(convert, scheme.root.children) if n is not None]
    leaf = next(t for t in scheme.topics if t.id == fallback)
    exit_ = Node(leaf.id, leaf.label, leaf.description, is_exit=True)
    return Node("", scheme.name, "", (*tier1, exit_))


def flat_tree(scheme: Scheme) -> Node:
    """Every leaf as an option of one question: flat tagging with a decision model.

    The fallback is one of the leaves, as in a flat prompt. Walking this tree asks one
    question per variable and keeps leaves as at any all-leaf tier (``keep_at``).
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

    Each request is one ``choice`` question over the tier's options ("Which area of a survey
    is this variable about?"), each described by its label, description and, for an area,
    its topics. Clef gives every option a probability, summing to about 1, which is used as
    the confidence. Walked over ``flat_tree`` it tags flat, over ``build_tree`` tiered. How
    many options a question may offer is the model's limit; a refusal is raised, not
    skipped, so the run stops (``OptionLimitError``).

    Args:
        provider: The decision-model host.
        keep_at: Topics below this probability are dropped, but the strongest is always kept.
            Areas, and a topic offered among them (the exit), are all returned; the walk decides
            which to follow.
    """

    def __init__(self, provider: DecisionProvider, keep_at: float = 0.3):
        self.provider = provider
        self.keep_at = keep_at

    def decide(self, node: Node, variables: list[Variable]) -> tuple[dict[int, Tags], int]:
        """Ask each variable which of ``node``'s children fits, one request per variable.

        A variable whose request fails is left out, so the walk asks it again alone; the
        others keep their answers.
        """
        instructions, options = _choice(node)
        leaf = {c.id: c.is_leaf for c in node.children}
        position = {c.id: i for i, c in enumerate(node.children)}
        got: dict[int, Tags] = {}
        error: ProviderError | None = None
        for i, v in enumerate(variables):
            try:
                probs = self.provider.decide(_state(v), instructions, options)
            except OptionLimitError:
                raise  # the same question would be refused for every variable
            except ProviderError as e:
                error = e
                continue
            ranked = [
                (c, round(p, 2))
                for c, p in sorted(probs.items(), key=lambda kv: (-kv[1], position[kv[0]]))
            ]
            if not all(leaf.values()):
                # A tier of areas (and the exit): every option comes back with its
                # probability, and the walk applies --descend-at to all of them alike.
                got[i] = ranked
                continue
            got[i] = [(c, p) for c, p in ranked if p >= self.keep_at] or ranked[:1]
        if not got and error is not None:
            raise error  # nothing answered: let the walk retry the whole group
        return got, len(variables)


def decision_request(model: str, node: Node, variable: Variable) -> dict:
    """The ``/v1/systemone`` body the decision decider sends for one variable at ``node``.

    Used by ``--dry-run``; the provider sends the same body.
    """
    instructions, options = _choice(node)
    return choice_body(model, _state(variable), instructions, options)


def _choice(node: Node) -> tuple[str, dict[str, str]]:
    """The question and described options for ``node``'s children."""
    kind = "topics" if all(c.is_leaf for c in node.children) else "areas"
    # A choice question gives one answer; asking it to share the probability lets a variable
    # with two true areas or topics reach the thresholds with both.
    question = (
        f"Which {kind} of a survey is this variable about? If more than one applies, share "
        "the probability between them."
    )
    return question, {c.id: _criterion(c) for c in node.children}


def _state(v: Variable) -> dict:
    """One variable as the decision model's state, with value labels capped as in prompts."""
    values = [f"{value}: {label}" for value, label in v.values[:MAX_VALUES]]
    if len(v.values) > MAX_VALUES:
        values.append(f"… and {len(v.values) - MAX_VALUES} more")
    return {"name": v.variable, "label": v.label or "", "values": values}


def _criterion(option: Node) -> str:
    text = f"{option.label}: {option.description}"
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
    area is then asked once, for all the batch's variables routed to it. A topic offered
    among areas (the fallback, an exit) is chosen the same way, and kept only if no area
    gives the variable a topic.

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
    exits: set[str] = set()
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
        mixed = any(not c.is_leaf for c in node.children)
        for i, _ in members:
            chosen = answers.get(i, [])
            if not mixed:
                for child_id, conf in chosen:
                    reach(_child(node, child_id), tier + 1, i, conf)
                continue
            # A tier with groups, perhaps with leaves beside them (the exit, or real leaves
            # in an uneven taxonomy): all are chosen alike, by descend_at, the strongest
            # always, at most max_areas.
            areas = sorted(chosen, key=lambda kv: (-kv[1], order[kv[0]]))
            follow = [(c, conf) for c, conf in areas if conf >= descend_at] or areas[:1]
            if max_areas:
                follow = follow[:max_areas]
            for child_id, conf in follow:
                child = _child(node, child_id)
                if child.is_exit:
                    exits.add(child.id)
                reach(child, tier + 1, i, conf)

    for i in range(len(batch)):
        found = best.get(i, {})
        if any(t not in exits for t in found):
            # The exit is for variables nothing else fits: drop it when an area gave topics.
            best[i] = {t: c for t, c in found.items() if t not in exits}
        if best.get(i):
            result.tags[i] = sorted(best[i].items(), key=lambda kv: (-kv[1], order[kv[0]]))
        else:
            result.failed.append(i)
    return result


def _ask(decider, node, positions, batch, tier, retries, result) -> dict[int, Tags]:
    """Ask one group, with the same ladder as flat batches: retries, then each one alone.

    A refusal for too many options is not retried: it is named and raised, to stop the run.
    """
    got = None
    for attempt in range(retries + 1):
        try:
            got, sent = decider.decide(node, [batch[i] for i in positions])
            result.requests_by_tier[tier] += sent
            break
        except OptionLimitError as e:
            _name_refusal(e, node, tier)
            raise
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
        except OptionLimitError as e:
            _name_refusal(e, node, tier)
            raise
        except (ReplyError, ProviderError) as e:
            result.requests_by_tier[tier] += 1
            result.last_error = str(e)
            continue
        if 0 in one:
            answers[i] = one[0]
    return answers


def _name_refusal(error: OptionLimitError, node: Node, tier: int) -> None:
    """Say which question was refused, and what the user can change, on the error."""
    more = "or use a model that takes more options."
    if node.id and tier:
        error.question = f'the categories in group {node.id}, "{node.label}", tier {tier}'
        error.advice = f"Split {node.id} into smaller groups, {more}"
    elif any(c.is_exit for c in node.children):
        error.question = "the tier-1 categories and the fallback exit"
        error.advice = f"Put the tier-1 categories into fewer, larger groups, {more}"
    else:
        error.question = "every topic, asked flat"
        error.advice = f"Tag tiered (--method tiered) so each question offers fewer options, {more}"


def refusal_message(model: str, error: OptionLimitError) -> str:
    """What to tell the user when a model refused a question: which, why, and what next.

    Args:
        model: The model's name as the user gave it.
        error: The refusal, named by the walk.
    """
    return (
        f"The model {model} refused a question with {error.options} options "
        f"({error.question}):\n  HTTP {error.status}: {error.host_message}\n{error.advice} "
        "Tags made so far are saved; a run with the same scheme and method carries on from them."
    )


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
