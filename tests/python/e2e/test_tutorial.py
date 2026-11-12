"""The tutorial page, site/tutorial/: self-contained, accurate to the data it is served with,
and every control on it works."""

import re

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect

AXE = Axe()
PREFIX = "/cohort-data-builder/"


@pytest.fixture
def base(serve, mini_site):
    """The site with the fixture cohort, served under a GitHub Pages-like subpath."""
    return serve(mini_site, PREFIX)


@pytest.fixture
def tutorial(page, base):
    page.goto(base + "tutorial/")
    expect(page.locator("#t-total")).to_have_text("16")
    return page


def test_loads_only_its_own_files_and_the_data(page, base):
    requested = []
    page.on("request", lambda r: requested.append(r.url))
    page.goto(base + "tutorial/")
    expect(page.locator("#t-total")).to_have_text("16")
    outside = [u for u in requested if not u.startswith((base + "tutorial/", base + "data/"))]
    assert outside == []


def test_title_and_counts_come_from_the_data(tutorial):
    page = tutorial
    expect(page).to_have_title(re.compile("Tutorial"))
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    expect(page.locator("#t-cohorts")).to_have_text("1")
    expect(page.locator("#t-topics")).to_have_text("3")
    expect(page.locator("#t-domains")).to_have_text("2")
    expect(page.locator("#t-cohort-list")).to_contain_text("Mini")
    expect(page.get_by_role("link", name="Open the builder").first).to_have_attribute("href", "../")


def test_search_demo_filters_and_opens_a_variable(tutorial):
    page = tutorial
    rows = page.locator("#search-demo .demo-row")
    total = rows.count()
    assert total >= 5
    page.get_by_label("Try a search").fill("pregnancy")
    expect(rows).not_to_have_count(total)
    page.get_by_label("Try a search").fill("habits")
    expect(rows).to_have_count(1)
    page.get_by_role("button", name="Show details for bd7smoke").click()
    expect(page.locator("#search-demo")).to_contain_text("never smoked")
    page.get_by_label("Try a search").fill("zzzz")
    expect(page.locator("#search-demo")).to_contain_text("No variables match")


def test_selection_demo_click_shift_click_and_clear(tutorial):
    page = tutorial
    demo = page.locator("#select-demo")
    demo.get_by_role("button", name="Select bd7smoke").click()
    demo.get_by_role("button", name="Select b11nfcigs").click(modifiers=["Shift"])
    expect(page.locator("#select-count")).to_have_text("3 selected")
    expect(demo.get_by_role("button", name="Select B10AGESTR")).to_have_attribute(
        "aria-pressed", "true"
    )
    demo.get_by_role("button", name="Select bd7smoke").click()
    expect(page.locator("#select-count")).to_have_text("2 selected")
    demo.get_by_role("button", name="Clear").click()
    expect(page.locator("#select-count")).to_have_text("0 selected")


def test_download_options_update_the_summary(tutorial):
    page = tutorial
    demo = page.locator("#download-demo")
    demo.get_by_label("Python").check()
    demo.get_by_label("Stata").check()
    demo.get_by_label("Turn missing codes into NA").uncheck()
    summary = page.locator("#dl-summary")
    expect(summary).to_contain_text("R and Python")
    expect(summary).to_contain_text("Stata")
    expect(summary).to_contain_text("missing codes kept")
    demo.get_by_label("R", exact=True).uncheck()
    expect(summary).not_to_contain_text("R and Python")


def test_run_command_follows_the_language(tutorial):
    page = tutorial
    expect(page.locator("#run-cmd")).to_have_text("Rscript R/merge.R")
    page.locator("#run").get_by_role("button", name="Python").click()
    expect(page.locator("#run-cmd")).to_have_text("python python/merge.py")


def test_shade_switch_rescales_the_topic_map(tutorial):
    page = tutorial
    cell = page.locator("#heat .heat-cell").first
    within = cell.get_attribute("style")
    page.get_by_label("Across topics").check()
    expect(page.locator("#heat")).to_have_attribute("data-shade", "across")
    assert cell.get_attribute("style") != within
    expect(page.locator("#shade-explain")).to_contain_text("one scale")
    page.get_by_label("Within each topic").check()
    expect(page.locator("#shade-explain")).to_contain_text("busiest sweep")


def test_confidence_filter_hides_less_certain_topics(tutorial):
    page = tutorial
    off = page.locator("#confidence-demo .chip.is-off")
    page.get_by_role("button", name="0.3").click()
    expect(off).to_have_count(0)
    page.get_by_role("button", name="0.9").click()
    assert off.count() > 0


def test_topics_section_names_closer_and_points_to_the_tagger(tutorial):
    page = tutorial
    section = page.locator("#topics")
    expect(section).to_contain_text("CLOSER")
    expect(section.get_by_role("link", name=re.compile("CLOSER Discovery"))).to_be_visible()
    expect(section.get_by_role("link", name=re.compile("Topic Tagger")).first).to_have_attribute(
        "href", re.compile(r"#topic-tagging$")
    )


def test_does_not_name_cls(tutorial):
    assert not re.search(r"\bCLS\b", tutorial.locator("body").inner_text())


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_no_serious_accessibility_problems(page, base, theme):
    page.emulate_media(color_scheme=theme)
    page.goto(base + "tutorial/")
    expect(page.locator("#t-total")).to_have_text("16")
    page.get_by_role("button", name="Show details for bd7smoke").click()
    found = AXE.run(page).response["violations"]
    serious = [v["id"] for v in found if v["impact"] in ("serious", "critical")]
    assert serious == []


def test_fits_a_phone(page, base):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base + "tutorial/")
    expect(page.locator("#t-total")).to_have_text("16")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= 390


def test_the_builder_links_to_it(page, base):
    page.goto(base)
    expect(page.locator("#result-count")).to_have_text("16 variables")
    link = page.locator("header").get_by_role("link", name="Tutorial")
    expect(link).to_have_attribute("href", "tutorial/")
    link.click()
    expect(page.locator("#t-total")).to_have_text("16")
