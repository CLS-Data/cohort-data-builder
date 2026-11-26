"""The cohort colours in site/styles.css (feature 007, user story 4): readable on the page
in both themes, and never mistaken for each other or for a topic area's colour."""

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).resolve().parents[2] / "site" / "styles.css").read_text()


def block(selector):
    """The custom properties set in the first rule for a selector."""
    start = CSS.index(selector + " {")
    body = CSS[start : CSS.index("\n}", start)]
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", body))


def luminance(hex_colour):
    """WCAG relative luminance."""
    rgb = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    """WCAG contrast ratio."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


THEMES = {"light": block(':root[data-theme="light"]'), "dark": block(':root[data-theme="dark"]')}


@pytest.mark.parametrize("theme", THEMES)
def test_six_cohort_colours_readable_on_the_page(theme):
    tokens = THEMES[theme]
    colours = [tokens[f"coh-{i}"] for i in range(1, 7)]
    for background in (tokens["paper"], tokens["paper-2"]):
        for c in colours:
            assert contrast(c, background) >= 3, (theme, c, background)


@pytest.mark.parametrize("theme", THEMES)
def test_cohort_colours_are_distinct_from_each_other_and_the_topic_areas(theme):
    tokens = THEMES[theme]
    colours = [tokens[f"coh-{i}"].lower() for i in range(1, 7)]
    assert len(set(colours)) == 6
    domains = {v.lower() for k, v in tokens.items() if k.startswith("d-")}
    assert domains, "the topic-area colours were found"
    assert not set(colours) & domains


def test_the_default_light_values_match_the_chosen_light_theme():
    light_root = block(":root")
    for i in range(1, 7):
        assert light_root[f"coh-{i}"] == THEMES["light"][f"coh-{i}"]
