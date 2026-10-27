import json

import pytest
from topic_tagger.variables import InputError, Variable, read_variables


def write(tmp_path, lines):
    path = tmp_path / "v.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_reads_the_fixture_in_file_order(variables_path):
    rows = read_variables(variables_path)
    assert len(rows) == 60
    assert rows[0] == Variable("alpha", "PID", "Participant identifier", (), "0y", True)
    assert rows[1].key == "alpha/A01AGE"
    assert rows[1].values == (("1", "Yes"), ("2", "No"))
    assert sum(r.identifier for r in rows) == 1


def test_missing_optional_fields_are_absent(tmp_path):
    (row,) = read_variables(write(tmp_path, ['{"file": "f", "variable": "v"}']))
    assert row == Variable("f", "v", None, (), None, False)


def test_null_optional_fields_are_absent(tmp_path):
    line = '{"file": "f", "variable": "v", "label": null, "values": null, "sweep": null}'
    (row,) = read_variables(write(tmp_path, [line]))
    assert row == Variable("f", "v", None, (), None, False)


def test_blank_lines_are_ignored(tmp_path):
    lines = ['{"file": "f", "variable": "a"}', "", "   ", '{"file": "f", "variable": "b"}']
    assert [r.variable for r in read_variables(write(tmp_path, lines))] == ["a", "b"]


def test_duplicates_are_listed_with_line_numbers_ignoring_case(tmp_path):
    lines = [json.dumps({"file": "f", "variable": v}) for v in ("A", "b", "a", "B", "c")]
    with pytest.raises(InputError) as err:
        read_variables(write(tmp_path, lines))
    text = str(err.value)
    assert "f/a" in text.lower() and "lines 1, 3" in text
    assert "lines 2, 4" in text


@pytest.mark.parametrize(
    "line, words",
    [
        ("{not json", "line 2"),
        ('{"file": "", "variable": "v"}', "line 2"),
        ('{"file": "f", "variable": ""}', "line 2"),
        ('{"file": "f"}', "line 2"),
        ("[1, 2]", "line 2"),
    ],
)
def test_bad_lines_are_named(tmp_path, line, words):
    with pytest.raises(InputError) as err:
        read_variables(write(tmp_path, ['{"file": "f", "variable": "ok"}', line]))
    assert words in str(err.value)


def test_a_missing_file_is_an_input_error(tmp_path):
    with pytest.raises(InputError):
        read_variables(tmp_path / "nope.jsonl")
