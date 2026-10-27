import json

from topics import export, main
from topics_data import read


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_one_line_per_index_row_in_order_without_the_identifier(cohort, tmp_path):
    out = tmp_path / "variables.jsonl"
    export(cohort, out)
    rows = lines(out)
    index = read(cohort / "index.json")
    files = [f["name"] for f in read(cohort / "manifest.json")["files"]]
    expected = [(files[r[2]], r[0]) for r in index if r[0].lower() != "pid"]
    assert [(r["file"], r["variable"]) for r in rows] == expected
    assert len(rows) == 13  # 16 rows, less PID in three files


def test_each_line_has_the_metadata_and_the_sweep(cohort, tmp_path):
    out = tmp_path / "variables.jsonl"
    export(cohort, out)
    by_key = {(r["file"], r["variable"]): r for r in lines(out)}
    smoke = by_key[("mini_age5", "smoke5")]
    assert smoke == {
        "file": "mini_age5",
        "variable": "smoke5",
        "label": "Does the mother smoke",
        "values": [["1.0", "Yes"], ["2.0", "No"]],
        "sweep": "5y",
    }
    assert by_key[("mini_noid", "areacode")]["sweep"] == "xwave"
    assert by_key[("mini_age5", "quote5")]["label"] == 'Mother said "fine"\\not fine\nsecond line'


def test_existing_topics_are_not_read(tmp_path):
    from topics_data import FIXTURE

    out = tmp_path / "v.jsonl"
    export(FIXTURE / "mini", out)  # the fixture still has its topics
    assert all("topics" not in r for r in lines(out))


def test_the_command_exits_0_and_2_on_a_folder_with_no_manifest(cohort, tmp_path, capsys):
    out = tmp_path / "v.jsonl"
    assert main(["export", str(cohort), "--out", str(out)]) == 0
    assert out.exists()
    assert main(["export", str(tmp_path), "--out", str(out)]) == 2
    assert "manifest.json" in capsys.readouterr().err
