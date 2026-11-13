"""Tiered tagging: the taxonomy tree, the tier walk and the two deciders (feature 004)."""

import json

import pytest

from conftest import StubProvider
from topic_tagger.providers import ProviderError
from topic_tagger.tiered import ChatDecider, Node, build_tree, walk
from topic_tagger.variables import Variable


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


# --- The tier walk with a chat model (US1) -------------------------------------------


def options_in(messages):
    """The option ids a tier request lists."""
    head = messages[0]["content"].split("Rules:")[0]
    return [line[2:].split(":")[0] for line in head.splitlines() if line.startswith("- ")]


def names_in(messages):
    return [json.loads(x)["name"] for x in messages[1]["content"].split("\n") if x.startswith("{")]


def scripted(answers, fail=()):
    """A chat stand-in answering from ``{variable: {option: confidence}}``.

    Only the options a request lists are answered, as a real reply would. Requests whose
    options include an id in ``fail`` raise, to drive the retry ladder.
    """

    def reply(messages, schema):
        opts = options_in(messages)
        if any(o in fail for o in opts):
            raise ProviderError("down")
        rows = []
        for i, name in enumerate(names_in(messages)):
            got = [(o, c) for o, c in answers.get(name, {}).items() if o in opts]
            if got:
                rows.append({"id": i, "topics": [{"topic": o, "confidence": c} for o, c in got]})
        return json.dumps({"variables": rows})

    return reply


def var(name):
    return Variable("f", name, name)


def do_walk(scheme, answers, names, fail=(), **kw):
    stub = StubProvider(scripted(answers, fail))
    decider = ChatDecider(stub, scheme.guidance)
    result = walk(
        build_tree(scheme),
        [var(n) for n in names],
        decider,
        descend_at=kw.get("descend_at", 0.5),
        max_areas=kw.get("max_areas", 3),
        retries=kw.get("retries", 1),
    )
    return result, stub


ANSWERS = {
    "smk": {"health": 0.9, "smoking": 0.9},
    "age": {"demographics": 0.95, "age": 0.8},
    "both": {"health": 0.8, "demographics": 0.6, "smoking": 0.7, "gender": 0.4},
    "weak": {"health": 0.3, "demographics": 0.2, "alcohol": 0.5},
}


def test_tier_1_asks_areas_then_each_followed_area_is_asked_once(small_scheme):
    result, stub = do_walk(small_scheme, ANSWERS, ["smk", "age", "both", "weak"])
    asked = [options_in(m) for m, _ in stub.calls]
    assert asked[0] == ["demographics", "health", "survey"]
    assert sorted(map(tuple, asked[1:])) == [
        ("age", "gender"),
        ("smoking", "alcohol", "physical_health"),
    ]
    assert result.requests_by_tier == [1, 2]


def test_areas_are_followed_by_threshold_and_the_strongest_always(small_scheme):
    result, _ = do_walk(small_scheme, ANSWERS, ["smk", "age", "both", "weak"])
    assert result.paths[2] == [("health", 0.8), ("demographics", 0.6)]
    # "weak": nothing reaches 0.5, so only its strongest area is followed
    assert result.paths[3] == [("health", 0.3)]
    assert result.tags[3] == [("alcohol", 0.5)]


def test_max_areas_caps_and_zero_means_no_cap(small_scheme):
    result, _ = do_walk(small_scheme, ANSWERS, ["both"], descend_at=0.1, max_areas=1)
    assert result.paths[0] == [("health", 0.8)]
    result, _ = do_walk(small_scheme, ANSWERS, ["both"], descend_at=0.1, max_areas=0)
    assert [a for a, _ in result.paths[0]] == ["health", "demographics"]


def test_tags_from_two_areas_are_merged_strongest_first_with_tier_2_confidence(small_scheme):
    result, _ = do_walk(small_scheme, ANSWERS, ["smk", "both"])
    assert result.tags[0] == [("smoking", 0.9)]
    assert result.tags[1] == [("smoking", 0.7), ("gender", 0.4)]


def test_a_node_with_one_child_is_routed_without_asking():
    leaf = Node("asthma", "Asthma", "Asthma.")
    only = Node("resp", "Respiratory", "Lungs.", (leaf,))
    other = Node("misc", "Misc", "Other.", (Node("x", "X", "X."), Node("y", "Y", "Y.")))
    root = Node("", "T", "", (only, other))
    stub = StubProvider(scripted({"v": {"resp": 0.7}}))
    result = walk(root, [var("v")], ChatDecider(stub, "g"), descend_at=0.5, max_areas=3)
    assert len(stub.calls) == 1  # tier 1 only
    assert result.tags[0] == [("asthma", 0.7)]


def test_a_scheme_with_one_area_sends_no_tier_1_request():
    root = Node("", "T", "", (Node("a", "A", "A.", (Node("x", "X", "X."), Node("y", "Y", "Y."))),))
    stub = StubProvider(scripted({"v": {"y": 0.6}}))
    result = walk(root, [var("v")], ChatDecider(stub, "g"), descend_at=0.5, max_areas=3)
    assert [options_in(m) for m, _ in stub.calls] == [["x", "y"]]
    assert result.tags[0] == [("y", 0.6)] and result.requests_by_tier == [0, 1]


def test_three_tiers_take_three_rounds_of_requests():
    asthma = Node("asthma", "Asthma", "Asthma.")
    copd = Node("copd", "COPD", "COPD.")
    resp = Node("resp", "Respiratory", "Lungs.", (asthma, copd))
    heart = Node(
        "heart", "Heart", "Heart.", (Node("hf", "Failure", "HF."), Node("af", "AF", "AF."))
    )
    health = Node("health", "Health", "Health.", (resp, heart))
    misc = Node("misc", "Misc", "Other.", (Node("x", "X", "X."), Node("y", "Y", "Y.")))
    root = Node("", "T", "", (health, misc))
    stub = StubProvider(scripted({"v": {"health": 0.9, "resp": 0.8, "asthma": 0.7}}))
    result = walk(root, [var("v")], ChatDecider(stub, "g"), descend_at=0.5, max_areas=3)
    assert result.requests_by_tier == [1, 1, 1]
    assert result.tags[0] == [("asthma", 0.7)]
    assert result.paths[0] == [("health", 0.9), ("resp", 0.8)]


def test_a_failing_area_is_retried_then_asked_alone_and_other_areas_are_kept(small_scheme):
    result, stub = do_walk(small_scheme, ANSWERS, ["both", "age"], fail=("smoking",), retries=1)
    # health failed: 1 try + 1 retry + "both" alone; demographics answered
    assert result.tags[0] == [("gender", 0.4)]
    assert result.tags[1] == [("age", 0.8)]
    assert result.failed == []
    assert result.retries == 1 and result.singles == 1
    assert "down" in result.last_error


def test_a_variable_ending_with_no_tags_is_failed(small_scheme):
    result, _ = do_walk(small_scheme, ANSWERS, ["smk", "age"], fail=("smoking",), retries=0)
    assert 0 in result.failed and 0 not in result.tags
    assert result.tags[1] == [("age", 0.8)]


def test_a_variable_left_out_at_tier_1_is_asked_alone(small_scheme):
    answers = dict(ANSWERS, ghost={})
    result, stub = do_walk(small_scheme, answers, ["smk", "ghost"])
    assert 1 in result.failed
    assert any(names_in(m) == ["ghost"] for m, _ in stub.calls)


@pytest.mark.parametrize("descend_at", [0.0, 0.5, 1.0])
def test_requests_never_exceed_one_plus_distinct_areas(small_scheme, descend_at):
    result, stub = do_walk(
        small_scheme, ANSWERS, ["smk", "age", "both", "weak"], descend_at=descend_at
    )
    areas = {a for p in result.paths.values() for a, _ in p}
    assert len(stub.calls) == 1 + len(areas)
