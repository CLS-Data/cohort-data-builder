import re

from test_stats import RUN, records, variables
from topic_tagger.report import render_report
from topic_tagger.stats import compute_stats

SECTIONS = ["run", "summary", "areas", "topics", "confidence", "groups", "speed", "files"]


def make(small_scheme, group_by="sweep", failed=("f2/v10",)):
    run = {
        **RUN,
        "status": "finished",
        "failed": list(failed),
        "timeline": [[0, 3], [10, 5], [20, 2]],
        "settings": {"model": "gpt-oss:20b", "provider": "ollama", "batch_size": 20},
    }
    stats = compute_stats(records(small_scheme.hash), variables(), small_scheme, run, group_by)
    return render_report(run, stats, small_scheme)


def test_has_the_eight_sections_in_order(small_scheme):
    html = make(small_scheme)
    found = re.findall(r'<section id="([a-z]+)"', html)
    assert found == SECTIONS


def test_the_group_section_is_left_out_without_the_field(small_scheme):
    html = make(small_scheme, group_by="nope")
    assert re.findall(r'<section id="([a-z]+)"', html) == [s for s in SECTIONS if s != "groups"]


def test_names_the_run(small_scheme):
    html = make(small_scheme)
    for part in ("2027-01-15", "gpt-oss:20b", small_scheme.name, small_scheme.hash):
        assert part in html


def test_is_self_contained(small_scheme):
    html = make(small_scheme)
    for bad in ("<script", 'src="http', 'href="http', "@import"):
        assert bad not in html


def test_follows_the_dark_preference(small_scheme):
    assert "@media (prefers-color-scheme: dark)" in make(small_scheme)


def test_lists_unused_topics_and_failed_variables_escaped(small_scheme):
    html = make(small_scheme, failed=("f2/<b>v10</b>",))
    assert "f2/&lt;b&gt;v10&lt;/b&gt;" in html and "<b>v10" not in html
    assert "Survey weights" in html  # the unused topic
