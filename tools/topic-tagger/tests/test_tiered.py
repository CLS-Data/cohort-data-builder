"""Tiered tagging: the taxonomy tree, the tier walk and the two deciders (feature 004)."""

import json

import pytest

from conftest import StubProvider
from topic_tagger.providers import ProviderError
from topic_tagger.tiered import (
    ChatDecider,
    DecisionDecider,
    Node,
    build_tree,
    choice_problems,
    walk,
)
from topic_tagger.variables import Variable


def test_the_tree_is_domains_then_topics(small_scheme):
    root = build_tree(small_scheme)
    assert root.id == "" and not root.is_leaf
    assert [d.id for d in root.children] == [d.id for d in small_scheme.domains] + ["other"]
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
    assert asked[0] == ["demographics", "health", "survey", "other"]
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
def test_requests_are_one_plus_distinct_areas(small_scheme, descend_at):
    result, stub = do_walk(
        small_scheme, ANSWERS, ["smk", "age", "both", "weak"], descend_at=descend_at
    )
    areas = {a for p in result.paths.values() for a, _ in p}
    # plus one for each variable a reply left out, asked again alone
    assert len(stub.calls) == 1 + len(areas) + result.singles


# --- The decision decider: Clef (US4) -----------------------------------------------


class StubDecision:
    """A stand-in decision host answering one choice question: ``probability(name, option)``."""

    def __init__(self, probability, fail_for=()):
        self.probability = probability
        self.fail_for = set(fail_for)
        self.calls: list[tuple[dict, str, dict]] = []

    def decide(self, state, instructions, options):
        self.calls.append((state, instructions, options))
        if state["name"] in self.fail_for:
            raise ProviderError("down")
        return {o: self.probability(state["name"], o) for o in options}


# Probabilities from one choice question sum to about 1 within each tier.
PROBS = {
    "smk": {
        "health": 0.9,
        "demographics": 0.06,
        "survey": 0.04,
        "smoking": 0.6,
        "alcohol": 0.35,
        "physical_health": 0.05,
    },
    "age": {"health": 0.02, "demographics": 0.97, "survey": 0.01, "age": 0.9, "gender": 0.1},
}


def clef_walk(scheme, names, keep_at=0.3, fail_for=(), **kw):
    stub = StubDecision(lambda n, o: PROBS[n].get(o, 0.0), fail_for)
    decider = DecisionDecider(stub, keep_at=keep_at)
    result = walk(
        build_tree(scheme),
        [var(n) for n in names],
        decider,
        descend_at=kw.get("descend_at", 0.5),
        max_areas=kw.get("max_areas", 3),
        retries=kw.get("retries", 1),
    )
    return result, stub


def test_clef_is_asked_one_choice_question_per_variable_per_tier(small_scheme):
    v = Variable("f", "smk", "Smokes now", tuple((str(i), f"L{i}") for i in range(40)))
    stub = StubDecision(lambda n, o: PROBS["smk"].get(o, 0.0))
    got, sent = DecisionDecider(stub).decide(build_tree(small_scheme), [v])
    assert sent == 1 and len(stub.calls) == 1
    state, instructions, options = stub.calls[0]
    assert state["name"] == "smk" and state["label"] == "Smokes now"
    assert len(state["values"]) == 31 and state["values"][0] == "0: L0"
    assert state["values"][-1] == "… and 10 more"
    assert instructions.startswith("Which areas of a survey is this variable about?")
    assert list(options) == ["demographics", "health", "survey", "other"]
    assert options["health"] == (
        "Health: Health and health behaviour. It includes: Smoking, Alcohol, Physical health."
    )
    # areas come back with every probability; the walk applies --descend-at
    assert got[0] == [("health", 0.9), ("demographics", 0.06), ("survey", 0.04), ("other", 0.0)]
    stub.calls.clear()
    DecisionDecider(stub).decide(build_tree(small_scheme).find("health"), [v])
    _, instructions, options = stub.calls[0]
    assert instructions.startswith("Which topics of a survey is this variable about?")
    assert options["smoking"] == "Smoking: Tobacco use."


def test_clef_tiered_tags_follow_both_thresholds(small_scheme):
    result, stub = clef_walk(small_scheme, ["smk", "age"])
    assert result.tags[0] == [("smoking", 0.6), ("alcohol", 0.35)]
    assert result.paths[0] == [("health", 0.9)]
    assert result.tags[1] == [("age", 0.9)]
    assert len(stub.calls) == 4  # each variable: tier 1, then one area
    assert result.requests_by_tier == [2, 2]


def test_keep_at_drops_weak_topics_but_never_all(small_scheme):
    result, _ = clef_walk(small_scheme, ["smk"], keep_at=0.5)
    assert result.tags[0] == [("smoking", 0.6)]
    result, _ = clef_walk(small_scheme, ["age"], keep_at=0.95)
    assert result.tags[0] == [("age", 0.9)]  # the strongest is kept when none pass


def test_keep_at_zero_keeps_every_topic(small_scheme):
    result, _ = clef_walk(small_scheme, ["smk"], keep_at=0)
    assert [t for t, _ in result.tags[0]] == ["smoking", "alcohol", "physical_health"]


def test_a_clef_failure_for_one_variable_leaves_the_others(small_scheme):
    result, stub = clef_walk(small_scheme, ["smk", "age"], fail_for={"age"})
    assert result.tags[0] == [("smoking", 0.6), ("alcohol", 0.35)]
    assert 1 in result.failed and result.singles == 1


def test_the_bundled_scheme_fits_clefs_choice_limit(bundled_scheme_path):
    from topic_tagger.scheme import load_scheme

    assert choice_problems(build_tree(load_scheme(bundled_scheme_path))) == []


def test_a_tier_with_more_than_26_options_is_named():
    big = Node("big", "Big", "", tuple(Node(f"t{i}", f"T{i}", "") for i in range(27)))
    root = Node("", "S", "", (big, Node("small", "Small", "", (Node("x", "X", ""),))))
    assert choice_problems(root) == ["area big has 27 topics; Clef can choose among at most 26"]
    areas = tuple(Node(f"a{i}", f"A{i}", "", (Node(f"x{i}", "X", ""),)) for i in range(30))
    many = Node("", "S", "", areas)
    assert choice_problems(many) == ["the scheme has 30 areas; Clef can choose among at most 26"]


# --- The fallback topic is an exit at tier 1 -----------------------------------------


def test_the_fallback_topic_is_offered_beside_the_areas(small_scheme):
    root = build_tree(small_scheme)
    assert [c.id for c in root.children] == ["demographics", "health", "survey", "other"]
    assert root.children[-1].is_leaf
    assert [c.id for c in root.find("survey").children] == ["identifiers", "survey_weights"]


def test_a_domain_left_empty_by_the_move_is_dropped(tmp_path):
    from topic_tagger.scheme import load_scheme

    path = tmp_path / "s.toml"
    path.write_text(
        'name = "S"\nversion = 1\nfallback_topic = "other"\nguidance = "G"\n'
        '[[domains]]\nid = "a"\nlabel = "A"\ndescription = "A."\n'
        '  [[domains.topics]]\n  id = "x"\n  label = "X"\n  description = "X."\n'
        '  [[domains.topics]]\n  id = "y"\n  label = "Y"\n  description = "Y."\n'
        '[[domains]]\nid = "misc"\nlabel = "Misc"\ndescription = "M."\n'
        '  [[domains.topics]]\n  id = "other"\n  label = "Other"\n  description = "None."\n'
    )
    assert [c.id for c in build_tree(load_scheme(path)).children] == ["a", "other"]


def test_the_exit_is_taken_when_it_is_the_strongest_option(small_scheme):
    answers = {"junk": {"other": 0.7, "health": 0.2}}
    result, calls = do_walk(small_scheme, answers, ["junk"])
    assert result.tags[0] == [("other", 0.7)]
    assert result.paths.get(0, []) == [] and result.requests_by_tier == [1, 0]


def test_the_exit_needs_the_descend_threshold_like_an_area(small_scheme):
    answers = {"smk": {"health": 0.9, "other": 0.4, "smoking": 0.9}}
    result, _ = do_walk(small_scheme, answers, ["smk"])
    assert result.tags[0] == [("smoking", 0.9)]


def test_the_exit_is_dropped_when_a_followed_area_gives_topics(small_scheme):
    answers = {"smk": {"health": 0.6, "other": 0.55, "smoking": 0.8}}
    result, _ = do_walk(small_scheme, answers, ["smk"])
    assert result.tags[0] == [("smoking", 0.8)]


def test_clef_sees_the_exit_and_its_probability_is_not_cut_by_keep_at(small_scheme):
    stub = StubDecision(lambda n, o: {"other": 0.25, "health": 0.2}.get(o, 0.18))
    got, _ = DecisionDecider(stub, keep_at=0.3).decide(build_tree(small_scheme), [var("q")])
    _, _, options = stub.calls[0]
    assert list(options) == ["demographics", "health", "survey", "other"]
    assert options["other"].startswith("Other: ")
    assert got[0][0] == ("other", 0.25) and len(got[0]) == 4


# --- Every method can tag one variable with topics from several areas ----------------


def test_clef_follows_every_area_at_the_threshold_and_tags_from_each(small_scheme):
    probs = {"health": 0.5, "demographics": 0.4, "survey": 0.06, "other": 0.04,
             "smoking": 0.8, "alcohol": 0.15, "age": 0.7, "gender": 0.3}  # fmt: skip
    stub = StubDecision(lambda n, o: probs.get(o, 0.0))
    result = walk(build_tree(small_scheme), [var("pregsmk")], DecisionDecider(stub, 0.3),
                  descend_at=0.3, max_areas=3)  # fmt: skip
    assert result.paths[0] == [("health", 0.5), ("demographics", 0.4)]
    assert result.tags[0] == [("smoking", 0.8), ("age", 0.7), ("gender", 0.3)]


def test_clefs_questions_ask_for_every_option_that_applies(small_scheme):
    stub = StubDecision(lambda n, o: 0.25)
    root = build_tree(small_scheme)
    DecisionDecider(stub).decide(root, [var("x")])
    DecisionDecider(stub).decide(root.find("health"), [var("x")])
    tier1, tier2 = stub.calls[0][1], stub.calls[1][1]
    assert tier1.startswith("Which areas of a survey is this variable about?")
    assert tier2.startswith("Which topics of a survey is this variable about?")
    for text in (tier1, tier2):
        assert "If more than one applies, share the probability between them" in text
