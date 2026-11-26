"""The tutorial page, site/tutorial/: self-contained, accurate to the data it is served with,
and every control on it works."""

import re

import pytest
from playwright.sync_api import expect

PREFIX = "/cohort-data-builder/"


@pytest.fixture
def base(serve, mini_site):
    """The site with the fixture cohort, served under a GitHub Pages-like subpath."""
    return serve(mini_site, PREFIX)


@pytest.fixture
def tutorial(page, base):
    page.goto(base + "tutorial/")
    expect(page.locator("#t-total")).to_have_text("31")  # mini 16 + mini2 12 + mini3 3
    return page


def test_loads_only_its_own_files_the_data_and_the_builders_styles(page, base):
    requested = []
    page.on("request", lambda r: requested.append(r.url))
    page.goto(base + "tutorial/")
    expect(page.locator("#t-total")).to_have_text("31")  # mini 16 + mini2 12 + mini3 3
    own = (base + "tutorial/", base + "data/", base + "styles.css")
    outside = [u for u in requested if not u.startswith(own)]
    assert outside == []
    assert base + "styles.css" in requested


def test_shares_the_builders_theme_setting(page, base):
    page.emulate_media(color_scheme="light")
    page.goto(base)
    expect(page.locator("#result-count")).to_have_text("16 variables")
    page.locator("#theme").click()
    page.goto(base + "tutorial/")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    page.locator("#theme").click()
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    page.goto(base)
    expect(page.locator("html")).to_have_attribute("data-theme", "light")


def test_title_and_counts_come_from_the_data(tutorial):
    page = tutorial
    expect(page).to_have_title(re.compile("Tutorial"))
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    expect(page.locator("#t-cohorts")).to_have_text("3")
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


def test_clicking_a_topic_shows_it_alone_in_the_sweep_bars(tutorial):
    page = tutorial
    expect(page.locator("#spine-name")).to_have_text("All six topics")
    page.locator("#heat").get_by_role("button", name="Smoking").click()
    expect(page.locator("#spine-name")).to_have_text("Smoking")
    expect(page.locator("#spine-total")).to_have_text("322")
    page.locator("#heat").get_by_role("button", name="Smoking").click()
    expect(page.locator("#spine-name")).to_have_text("All six topics")


def test_selection_groups_by_sweep_or_file(tutorial):
    page = tutorial
    demo = page.locator("#select-demo")
    demo.get_by_role("button", name="Select cgprega4").click()
    expect(page.locator("#select-panel")).to_contain_text("Age 29/30")
    demo.get_by_role("button", name="File").click()
    expect(page.locator("#select-panel")).to_contain_text("bcs2000")


def test_download_options_update_the_summary(tutorial):
    page = tutorial
    demo = page.locator("#download-demo")
    demo.get_by_label("Python").check()
    demo.get_by_label("Stata", exact=True).check()
    demo.get_by_label("Turn missing codes into NA").uncheck()
    summary = page.locator("#dl-summary")
    expect(summary).to_contain_text("R and Python")
    expect(summary).to_contain_text("Stata")
    expect(summary).to_contain_text("missing codes kept")
    demo.get_by_label("R", exact=True).uncheck()
    expect(summary).not_to_contain_text("R and Python")


def test_stata_code_is_a_download_option(tutorial):
    page = tutorial
    demo = page.locator("#download-demo")
    demo.get_by_label("Python").check()
    demo.get_by_label("Stata (do-file)").check()
    expect(page.locator("#dl-summary")).to_contain_text("R, Python and Stata")
    expect(page.locator("#dl-tree")).to_contain_text("stata/merge.do")


def test_run_command_follows_the_language(tutorial):
    page = tutorial
    expect(page.locator("#run-cmd")).to_have_text("Rscript R/merge.R")
    page.locator("#run").get_by_role("button", name="Python").click()
    expect(page.locator("#run-cmd")).to_have_text("python python/merge.py")
    page.locator("#run").get_by_role("button", name="Stata").click()
    expect(page.locator("#run-cmd")).to_have_text("do stata/merge.do")


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
    page.get_by_role("button", name="30%").click()
    expect(off).to_have_count(0)
    page.get_by_role("button", name="90%").click()
    expect(off).not_to_have_count(0)


def test_topics_section_names_closer_and_points_to_the_tagger(tutorial):
    page = tutorial
    section = page.locator("#topics")
    expect(section).to_contain_text("CLOSER")
    expect(section).to_contain_text("large language model")
    expect(section).not_to_contain_text("O'Neill")
    expect(section.get_by_role("link", name=re.compile("CLOSER Discovery"))).to_be_visible()
    expect(section.get_by_role("link", name=re.compile("Topic Tagger")).first).to_have_attribute(
        "href", re.compile(r"#topic-tagging$")
    )


def test_does_not_name_cls(tutorial):
    assert not re.search(r"\bCLS\b", tutorial.locator("body").inner_text())


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_no_serious_accessibility_problems(page, base, theme, serious):
    page.emulate_media(color_scheme=theme)
    page.goto(base + "tutorial/")
    expect(page.locator("#t-total")).to_have_text("31")  # mini 16 + mini2 12 + mini3 3
    page.get_by_role("button", name="Show details for bd7smoke").click()
    assert serious(page) == []


def test_fits_a_phone(page, base):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base + "tutorial/")
    expect(page.locator("#t-total")).to_have_text("31")  # mini 16 + mini2 12 + mini3 3
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= 390


def test_the_builder_links_to_it(page, base):
    page.goto(base)
    expect(page.locator("#result-count")).to_have_text("16 variables")
    link = page.locator("header").get_by_role("link", name="Tutorial")
    expect(link).to_have_attribute("href", "tutorial/")
    link.click()
    expect(page.locator("#t-total")).to_have_text("31")  # mini 16 + mini2 12 + mini3 3


# Feature 007, user story 5: several cohorts


MARK_COLOUR = """(key) => {
  const host = document.querySelector(`[data-cohort="${key}"] .coh-mark`);
  return host && getComputedStyle(host).backgroundColor;
}"""


def test_the_cohort_list_marks_each_cohort_in_the_builders_colour(page, base):
    page.goto(base + "#mini+mini2")
    expect(page.locator('.cohorts button[data-cohort="mini2"]')).to_have_attribute(
        "aria-pressed", "true"
    )
    builder = {k: page.evaluate(MARK_COLOUR, k) for k in ("mini", "mini2", "mini3")}
    page.goto(base + "tutorial/")
    items = page.locator("#t-cohort-list li")
    expect(items).to_have_count(3)
    expect(items.locator(".coh-mark")).to_have_count(3)
    tutorial = {k: page.evaluate(MARK_COLOUR, k) for k in builder}
    assert tutorial == builder
    assert len(set(tutorial.values())) == 3


def test_the_intro_says_cohorts_can_be_searched_together(tutorial):
    expect(tutorial.locator(".t-intro")).to_contain_text("search several cohorts at once")


def test_the_download_step_shows_a_folder_per_cohort(tutorial):
    tree = tutorial.locator("#dl-tree-many")
    expect(tree).to_contain_text("cohorts-merge-")
    assert tree.inner_text().count("-merge-") >= 3  # the zip and two cohort folders
    expect(tutorial.locator("#download")).to_contain_text("a folder per cohort")


def test_the_run_step_says_each_cohort_runs_on_its_own(tutorial):
    run = tutorial.locator("#run")
    expect(run).to_contain_text("each folder on its own")
    expect(run).to_contain_text("not merged with each other")


def test_the_select_step_mentions_selections_from_several_cohorts(tutorial):
    expect(tutorial.locator("#select")).to_contain_text("grouped by cohort")
