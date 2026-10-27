import pytest

from topic_tagger.stats import compute_stats
from topic_tagger.variables import Variable

# 12 variables in two files. v0–v9 are tagged, v10 failed and v11 has only a stale record.
TOPICS = {
    "v0": [["age", 0.9]],
    "v1": [["age", 0.8], ["gender", 0.6]],
    "v2": [["smoking", 0.95], ["alcohol", 0.45]],
    "v3": [["smoking", 1.0]],
    "v4": [["physical_health", 0.3]],
    "v5": [["other", 0.2]],
    "v6": [["age", 0.7], ["smoking", 0.7]],
    "v7": [["alcohol", 0.55]],
    "v8": [["identifiers", 1.0]],
    "v9": [["gender", 0.49]],
}


def variables():
    out = []
    for i in range(12):
        file = "f1" if i < 6 else "f2"
        extra = {"sweep": "0y" if i < 6 else "5y"} if i != 11 else {}
        if i < 2:
            extra["questionnaire"] = "parent"
        out.append(Variable(file, f"v{i}", extra=extra))
    return out


def records(scheme_hash):
    recs = [
        {
            "file": "f1" if int(v[1:]) < 6 else "f2",
            "variable": v,
            "topics": t,
            "scheme": scheme_hash,
        }
        for v, t in TOPICS.items()
    ]
    recs.append({"file": "f2", "variable": "v11", "topics": [["age", 1.0]], "scheme": "stale"})
    recs.append({"file": "f9", "variable": "gone", "topics": [["age", 1.0]], "scheme": scheme_hash})
    return recs


RUN = {
    "started": "2027-01-15T08:00:00Z",
    "ended": "2027-01-15T08:02:00Z",
    "counts": {"tagged": 10},
    "failed": ["f2/v10"],
}


@pytest.fixture
def stats(small_scheme):
    return compute_stats(records(small_scheme.hash), variables(), small_scheme, RUN)


def test_per_topic_includes_the_zeros(stats, small_scheme):
    assert list(stats["per_topic"]) == small_scheme.topic_ids
    assert stats["per_topic"] == {
        "age": 3,
        "gender": 2,
        "smoking": 3,
        "alcohol": 2,
        "physical_health": 1,
        "identifiers": 1,
        "survey_weights": 0,
        "other": 1,
    }


def test_per_domain_counts_each_variable_once(stats):
    assert stats["per_domain"] == {"demographics": 4, "health": 5, "survey": 2}


def test_unused(stats):
    assert stats["unused"] == ["survey_weights"]


def test_confidence_histogram_has_10_bins_with_1_in_the_last(stats):
    assert stats["confidence_histogram"] == [0, 0, 1, 1, 2, 1, 1, 2, 1, 4]


def test_below_default_and_mean_topics(stats):
    assert stats["below_default"] == 0.3  # v4, v5 and v9
    assert stats["mean_topics"] == 1.3  # 13 tags on 10 variables


def test_per_file(stats):
    assert stats["per_file"] == {"f1": {"tagged": 6, "failed": 0}, "f2": {"tagged": 4, "failed": 1}}


def test_grouped_by_sweep_by_default(stats):
    assert stats["group_by"] == "sweep"
    assert stats["per_group"] == {"0y": 6, "5y": 4}
    assert stats["domain_by_group"] == {
        "0y": {"demographics": 2, "health": 3, "survey": 1},
        "5y": {"demographics": 2, "health": 2, "survey": 1},
    }


def test_grouped_by_another_field(small_scheme):
    s = compute_stats(records(small_scheme.hash), variables(), small_scheme, RUN, "questionnaire")
    assert s["group_by"] == "questionnaire"
    assert s["per_group"] == {"parent": 2}
    assert s["domain_by_group"] == {"parent": {"demographics": 2, "health": 0, "survey": 0}}


def test_no_variable_has_the_field(small_scheme):
    s = compute_stats(records(small_scheme.hash), variables(), small_scheme, RUN, "nope")
    assert s["per_group"] == {} and s["domain_by_group"] == {}


def test_speed(stats):
    assert stats["speed"] == 5.0  # 10 variables in 2 minutes


def test_nothing_tagged(small_scheme):
    run = {**RUN, "counts": {"tagged": 0}, "ended": RUN["started"]}
    s = compute_stats([], variables(), small_scheme, run)
    assert s["below_default"] == 0 and s["mean_topics"] == 0 and s["speed"] == 0
    assert len(s["unused"]) == len(small_scheme.topic_ids)
