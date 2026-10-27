import json

import pytest

from topic_tagger.reply import ReplyError, parse_reply


def reply(*variables):
    return json.dumps(
        {
            "variables": [
                {"id": i, "topics": [{"topic": t, "confidence": c} for t, c in tags]}
                for i, tags in variables
            ]
        }
    )


def test_parses_a_good_reply(small_scheme):
    text = reply((0, [("smoking", 0.9)]), (1, [("age", 0.6), ("gender", 0.3)]))
    assert parse_reply(text, small_scheme, 2) == {
        0: [("smoking", 0.9)],
        1: [("age", 0.6), ("gender", 0.3)],
    }


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        '{"nothing": []}',
        reply((0, [("vaping", 0.9)])),  # not in the scheme
        reply((0, [("smoking", 1.2)])),  # confidence over 1
        reply((0, [("smoking", -0.1)])),  # under 0
        reply((5, [("smoking", 0.9)])),  # id outside the batch of 2
        reply((-1, [("smoking", 0.9)])),
    ],
)
def test_rejects_a_bad_reply(small_scheme, text):
    with pytest.raises(ReplyError):
        parse_reply(text, small_scheme, 2)


def test_duplicate_topics_keep_the_highest_confidence(small_scheme):
    text = reply((0, [("smoking", 0.4), ("smoking", 0.8)]))
    assert parse_reply(text, small_scheme, 1) == {0: [("smoking", 0.8)]}


def test_confidences_are_rounded_to_two_places(small_scheme):
    text = reply((0, [("smoking", 0.876543)]))
    assert parse_reply(text, small_scheme, 1) == {0: [("smoking", 0.88)]}


def test_tags_are_strongest_first_with_ties_in_scheme_order(small_scheme):
    text = reply((0, [("other", 0.5), ("alcohol", 0.5), ("age", 0.9), ("smoking", 0.5)]))
    assert parse_reply(text, small_scheme, 1) == {
        0: [("age", 0.9), ("smoking", 0.5), ("alcohol", 0.5), ("other", 0.5)]
    }


def test_variables_without_tags_are_left_out(small_scheme):
    text = reply((0, [("smoking", 0.9)]), (1, []))
    assert parse_reply(text, small_scheme, 2) == {0: [("smoking", 0.9)]}
