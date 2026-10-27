import json

import pytest
from checks import check_data
from topics import export, main, merge
from topics_data import read

SCHEME = {
    "name": "Mini topics",
    "version": 2,
    "hash": "abcdef123456",
    "guidance": "Tag each variable.",
    "fallback_topic": "other",
    "domains": [
        {
            "id": "health",
            "label": "Health",
            "description": "Physical and mental health.",
            "topics": [
                {"id": "smoking", "label": "Smoking", "description": "Tobacco use."},
                {"id": "alcohol", "label": "Alcohol", "description": "Drinking."},
            ],
        },
        {
            "id": "housing",
            "label": "Housing",
            "description": "Where people live.",
            "topics": [{"id": "tenure", "label": "Tenure", "description": "Owning or renting."}],
        },
        {
            "id": "admin",
            "label": "Administration",
            "description": "About the study itself.",
            "topics": [
                {"id": "identifiers", "label": "Identifiers", "description": "Ids."},
                {"id": "other", "label": "Other", "description": "Anything else."},
            ],
        },
    ],
}
NUMBER = {"smoking": 0, "alcohol": 1, "tenure": 2, "identifiers": 3, "other": 4}

# Out of order on purpose: the merge sorts strongest first, ties in scheme order.
TAGS = {
    "smoke5": [["alcohol", 0.4], ["smoking", 0.9]],
    "tenure5": [["tenure", 0.6]],
    "alc10": [["alcohol", 0.8]],
    "tenure10": [["other", 0.5], ["tenure", 0.5]],
}
UNTAGGED = "nolab5"


def tag_folder(cohort, tmp_path, scheme=SCHEME, extra=()):
    """Export the cohort, then write tags for it as the tool would."""
    variables = tmp_path / "variables.jsonl"
    export(cohort, variables)
    tags = tmp_path / "tags"
    tags.mkdir(exist_ok=True)
    (tags / "scheme.json").write_text(json.dumps(scheme), encoding="utf-8")
    records = []
    for line in variables.read_text(encoding="utf-8").splitlines():
        v = json.loads(line)
        if v["variable"] == UNTAGGED:
            continue
        topics = TAGS.get(v["variable"], [["other", 0.2]])
        records.append(
            {
                "file": v["file"],
                "variable": v["variable"],
                "topics": topics,
                "scheme": scheme["hash"],
                "model": "stub:test",
                "tagged": "2027-01-15T08:00:00Z",
            }
        )
    records += list(extra)
    text = "\n".join(json.dumps(r) for r in records) + "\n"
    (tags / "tags.jsonl").write_text(text, encoding="utf-8")
    return tags


def variables_of(cohort):
    out = {}
    for f in read(cohort / "manifest.json")["files"]:
        for v in read(cohort / "dict" / f"{f['name']}.json")["variables"]:
            out[(f["name"], v["variable"])] = v
    return out


def index_of(cohort):
    files = [f["name"] for f in read(cohort / "manifest.json")["files"]]
    return {(files[r[2]], r[0]): r for r in read(cohort / "index.json")}


def test_round_trip(cohort, data_dir, tmp_path):
    merge(cohort, tag_folder(cohort, tmp_path))
    assert check_data(data_dir) == []
    v = variables_of(cohort)
    assert v[("mini_age5", "smoke5")]["topics"] == [["smoking", 0.9], ["alcohol", 0.4]]
    assert v[("mini_age10", "tenure10")]["topics"] == [["tenure", 0.5], ["other", 0.5]]
    assert v[("mini_age10", "mood10")]["topics"] == [["other", 0.2]]
    idx = index_of(cohort)
    assert idx[("mini_age5", "smoke5")][5] == [0, 90, 1, 40]


def test_manifest_topics_have_the_site_shape(cohort, tmp_path):
    merge(cohort, tag_folder(cohort, tmp_path))
    topics = read(cohort / "manifest.json")["topics"]
    assert set(topics) == {"name", "version", "hash", "domains"}
    assert (topics["name"], topics["version"], topics["hash"]) == ("Mini topics", 2, "abcdef123456")
    assert topics["domains"][0] == SCHEME["domains"][0]


def test_the_identifier_is_tagged_in_every_file_that_has_it(cohort, tmp_path):
    merge(cohort, tag_folder(cohort, tmp_path))
    v, idx = variables_of(cohort), index_of(cohort)
    for key in [("mini_age5", "PID"), ("mini_age10", "pid"), ("mini_grid", "PID")]:
        assert v[key]["topics"] == [["identifiers", 1.0]]
        assert idx[key][5] == [NUMBER["identifiers"], 100]


def test_the_identifier_topic_can_be_changed(cohort, tmp_path):
    merge(cohort, tag_folder(cohort, tmp_path), identifier_topic="other")
    assert variables_of(cohort)[("mini_age5", "PID")]["topics"] == [["other", 1.0]]


def test_an_identifier_topic_missing_from_the_scheme_writes_nothing(cohort, tmp_path, capsys):
    tags = tag_folder(cohort, tmp_path)
    before = {p: p.read_bytes() for p in cohort.rglob("*.json")}
    argv = ["merge", str(cohort), "--tags", str(tags), "--identifier-topic", "ids"]
    assert main(argv) == 2
    assert "ids" in capsys.readouterr().err
    assert {p: p.read_bytes() for p in cohort.rglob("*.json")} == before


def test_untagged_rows_have_exactly_five_elements(cohort, tmp_path):
    merge(cohort, tag_folder(cohort, tmp_path))
    assert len(index_of(cohort)[("mini_age5", UNTAGGED)]) == 5
    assert "topics" not in variables_of(cohort)[("mini_age5", UNTAGGED)]


def test_problems_are_reported_without_stopping(cohort, tmp_path, capsys):
    unknown = {"file": "mini_age5", "variable": "ghost", "topics": [["other", 0.3]]}
    stale = {"file": "mini_age5", "variable": "sex", "topics": [["other", 0.3]]}
    tags = tag_folder(
        cohort,
        tmp_path,
        extra=[{**unknown, "scheme": SCHEME["hash"]}, {**stale, "scheme": "0ld0ld0ld0ld"}],
    )
    result = merge(cohort, tags)
    assert result.unknown == ["mini_age5/ghost"]
    # The stale line for sex comes last, so it wins and is skipped: sex has no tags.
    assert result.stale == ["mini_age5/sex"]
    assert result.untagged == ["mini_age5/sex", "mini_age5/nolab5"]
    assert "topics" not in variables_of(cohort)[("mini_age5", "sex")]
    assert main(["merge", str(cohort), "--tags", str(tags)]) == 0
    err = capsys.readouterr().err
    for part in ("ghost", "nolab5", "stale"):
        assert part in err


def test_nothing_else_changes(cohort, tmp_path):
    before = {p: read(p) for p in cohort.rglob("*.json")}
    tags = tag_folder(cohort, tmp_path)
    merge(cohort, tags)
    after = {p: read(p) for p in cohort.rglob("*.json")}
    after[cohort / "manifest.json"].pop("topics")
    after[cohort / "index.json"] = [r[:5] for r in after[cohort / "index.json"]]
    for p, d in after.items():
        if p.parent.name == "dict":
            for v in d["variables"]:
                v.pop("topics", None)
    assert after == before
    first = {p: p.read_bytes() for p in cohort.rglob("*.json")}
    merge(cohort, tags)
    assert {p: p.read_bytes() for p in cohort.rglob("*.json")} == first


def test_files_are_written_compactly(cohort, tmp_path):
    merge(cohort, tag_folder(cohort, tmp_path))
    text = (cohort / "manifest.json").read_text(encoding="utf-8")
    assert "\n" not in text.strip() and ", " not in text.split('"description"')[0]


def test_exit_1_when_the_checks_find_problems(cohort, tmp_path, capsys):
    bad = json.loads(json.dumps(SCHEME))
    bad["domains"][1]["topics"].append({"id": "smoking", "label": "S", "description": "d"})
    assert main(["merge", str(cohort), "--tags", str(tag_folder(cohort, tmp_path, bad))]) == 1
    assert "used twice" in capsys.readouterr().err


@pytest.mark.parametrize("missing", ["scheme.json", "tags.jsonl"])
def test_exit_2_on_bad_input(cohort, tmp_path, missing, capsys):
    tags = tag_folder(cohort, tmp_path)
    (tags / missing).unlink()
    assert main(["merge", str(cohort), "--tags", str(tags)]) == 2
    assert missing in capsys.readouterr().err


def test_only_newline_ends_a_tags_line(cohort, tmp_path, capsys):
    # A name with U+2028 is valid JSON unescaped; str.splitlines() would split the record.
    odd = {
        "file": "mini_age5",
        "variable": "odd\u2028name",
        "topics": [["other", 0.5]],
        "scheme": SCHEME["hash"],
        "model": "stub:test",
        "tagged": "2027-01-15T08:00:00Z",
    }
    tags = tag_folder(cohort, tmp_path)
    with (tags / "tags.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(odd, ensure_ascii=False) + "\n")
    assert merge(cohort, tags).unknown == ["mini_age5/odd\u2028name"]
