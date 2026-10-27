import pytest
from cls_metadata import derive_na, fix_text, parse_value_labels, sweep_key, sweep_label


def test_c1_characters_become_their_cp1252_meaning():
    assert fix_text("Don\x92t know \x85 \x80") == "Don’t know … €"
    assert fix_text("plain é text") == "plain é text"


def test_value_labels_are_split_on_padded_codes():
    text = "(-1                ) Missing: not applicable   (1) Yes   (2) No (not now)   "
    assert parse_value_labels(text, numeric=True) == (
        [["-1", "Missing: not applicable"], ["1", "Yes"], ["2", "No (not now)"]],
        False,
    )


def test_empty_value_labels():
    assert parse_value_labels("", numeric=True) == ([], False)


def test_a_cut_off_list_drops_its_last_label_and_says_so():
    text = "(1) Leeds   (2) York   (3) Derby, Derbys... AND MORE"
    assert parse_value_labels(text, numeric=True) == ([["1", "Leeds"], ["2", "York"]], True)


def test_system_missing_and_blank_codes_are_dropped():
    text = "(SysMiss ) Missing/Not Applicable   (        ) Blank   (1) Yes   "
    assert parse_value_labels(text, numeric=True) == ([["1", "Yes"]], False)


def test_text_codes_are_kept_only_for_string_variables():
    text = "(X) Unknown   (Y) Yes   "
    assert parse_value_labels(text, numeric=False) == ([["X", "Unknown"], ["Y", "Yes"]], False)
    assert parse_value_labels(text, numeric=True) == ([], False)


def test_negative_codes_with_missing_labels_become_na():
    values = [["-9", "Refusal"], ["-8", "Don’t know"], ["-1", "Not applicable"], ["1", "Yes"]]
    assert derive_na(values) == {"values": [-9, -8, -1], "ranges": []}


def test_negative_codes_that_read_as_answers_are_kept():
    values = [["-2", "Armed Services"], ["-1", "Not known"], ["1", "North"]]
    assert derive_na(values) == {"values": [-1], "ranges": [], "kept": [[-2, "Armed Services"]]}


def test_no_negative_codes_means_no_na():
    assert derive_na([["1", "Yes"], ["2", "No"]]) is None
    assert derive_na([]) is None


def test_decimal_codes_stay_decimal():
    assert derive_na([["-1.5", "Not stated"]]) == {"values": [-1.5], "ranges": []}


@pytest.mark.parametrize(
    ("sweep", "key"), [("-1.0", "xwave"), ("0.0", "s0"), ("6.1", "s6_1"), ("10.0", "s10")]
)
def test_sweep_keys(sweep, key):
    assert sweep_key(sweep) == key


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("cross-sweep", "Cross-sweep"),
        ("Sweep0 - 1958 - birth", "Sweep 0: birth, 1958"),
        ("Sweep6.1 - 2002/04 - 44/45 years old", "Sweep 6.1: age 44/45, 2002/04"),
        ("Sweep1 - 2001/03 - 9 months old", "Sweep 1: age 9 months, 2001/03"),
        ("Something else", "Something else"),
    ],
)
def test_sweep_labels(text, label):
    assert sweep_label(text) == label
