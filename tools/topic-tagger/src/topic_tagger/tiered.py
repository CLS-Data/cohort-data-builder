"""Tiered tagging: walk the taxonomy one tier at a time (feature 004).

The scheme becomes a tree of ``Node``s: a root, its areas (the scheme's domains), and their
topics. Tagging tiered asks, for each variable, which areas apply, then which topics within
each area that passed the threshold, and so on for deeper trees.
"""

from __future__ import annotations

from dataclasses import dataclass

from topic_tagger.scheme import Scheme


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
