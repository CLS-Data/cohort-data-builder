"""Tiered tagging: the taxonomy tree, the tier walk and the two deciders (feature 004)."""

from topic_tagger.tiered import Node, build_tree


def test_the_tree_is_domains_then_topics(small_scheme):
    root = build_tree(small_scheme)
    assert root.id == "" and not root.is_leaf
    assert [d.id for d in root.children] == [d.id for d in small_scheme.domains]
    health = root.find("health")
    assert [t.id for t in health.children] == ["smoking", "alcohol", "physical_health"]
    assert health.label == "Health" and health.description
    smoking = root.find("smoking")
    assert smoking.is_leaf and smoking.children == ()
    assert root.find("nope") is None


def test_a_node_can_hold_any_depth():
    leaf = Node("asthma", "Asthma", "Asthma.")
    mid = Node("respiratory", "Respiratory", "Lungs.", (leaf,))
    root = Node("", "", "", (Node("health", "Health", "Health.", (mid,)),))
    assert root.find("asthma") is leaf
    assert not mid.is_leaf
