import re

import pytest

from topic_tagger import svg

CHARTS = {
    "bars": (lambda: svg.bars([("Health", 12), ("Demographics", 7)], "Per area"), 2),
    "histogram": (lambda: svg.histogram([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "Confidence"), 10),
    "heat_grid": (
        lambda: svg.heat_grid(
            ["Health", "Survey"], ["0y", "5y", "10y"], [[1, 2, 3], [4, 5, 0]], "G"
        ),
        6,
    ),
    "line": (lambda: svg.line([(0, 0), (10, 60), (20, 120)], "Speed"), 1),
}


@pytest.mark.parametrize("name", CHARTS)
def test_each_chart_is_an_accessible_svg(name):
    make, marks = CHARTS[name]
    out = make()
    assert out.startswith("<svg") and 'viewBox="' in out
    assert re.search(r"<title>[^<]+</title>", out)
    assert len(re.findall(r'class="mark', out)) == marks


@pytest.mark.parametrize("name", CHARTS)
def test_colours_come_only_from_css_variables(name):
    out = CHARTS[name][0]()
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", out)
    assert not re.search(r"\b(rgb|hsl)a?\(", out)
    assert "var(--" in out


def test_values_are_labelled():
    assert ">12<" in svg.bars([("Health", 12), ("Demographics", 7)], "t")
    assert ">9<" in svg.histogram([0, 0, 0, 0, 0, 0, 0, 0, 0, 9], "t")
    grid = svg.heat_grid(["A"], ["x", "y"], [[3, 4]], "t")
    assert ">3<" in grid and ">4<" in grid
    assert ">120<" in svg.line([(0, 0), (10, 120)], "t")


def test_each_mark_has_a_tooltip():
    out = svg.bars([("Health", 12)], "t")
    assert re.search(r'class="mark[^>]*>\s*<title>Health: 12</title>', out)


def test_text_is_escaped():
    out = svg.bars([("<b>x</b>", 1)], "a & b")
    assert "<b>" not in out and "&lt;b&gt;" in out and "a &amp; b" in out


@pytest.mark.parametrize(
    "make",
    [
        lambda: svg.bars([], "t"),
        lambda: svg.histogram([0] * 10, "t"),
        lambda: svg.heat_grid([], [], [], "t"),
        lambda: svg.line([], "t"),
    ],
)
def test_empty_input_says_no_data(make):
    out = make()
    assert out.startswith("<svg") and "No data" in out
