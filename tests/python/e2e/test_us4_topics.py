import json
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import expect

FIXTURE_DATA = Path(__file__).resolve().parents[2] / "fixtures" / "data"


@pytest.fixture
def mini(page, serve, mini_site):
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    return page


def open_topics(page):
    page.locator("#tgrid-toggle").click()
    return page.locator("#tgrid-body")


def topic(page, name):
    return page.locator("#tgrid-body").get_by_role("button", name=name, exact=True)


def row(page, name):
    return page.locator("#results .vrow").filter(has=page.locator(f'.v-name:text-is("{name}")'))


def count(page, text):
    expect(page.locator("#result-count")).to_have_text(text)


def test_overview_shows_domains_by_sweep_and_opens_onto_topics(mini):
    grid = open_topics(mini)
    expect(mini.locator("#tgrid-toggle")).to_have_attribute("aria-expanded", "true")
    rows = grid.locator(".tg-row")
    expect(rows).to_have_count(2)
    expect(rows.nth(0)).to_contain_text("Health")
    expect(rows.nth(1)).to_contain_text("Housing")
    expect(rows.nth(1).locator(".ov-count")).to_have_text("2")
    expect(rows.nth(1).locator(".tg-cell")).to_have_count(3)
    expect(grid.get_by_label("Housing at 10y: 1")).to_have_attribute("data-l", "4")
    expect(grid.get_by_label("Housing at xwave: 0")).to_have_attribute("data-l", "0")
    grid.get_by_role("button", name="Show the topics in Health").click()
    expect(rows).to_have_count(4)
    topics = grid.locator(".tg-row.is-topic")
    expect(topics).to_have_count(2)
    expect(topics.nth(0)).to_contain_text("Smoking")
    expect(topics.nth(1)).to_contain_text("Alcohol")


def test_selecting_a_topic_filters_and_adds_a_chip(mini):
    open_topics(mini)
    topic(mini, "Housing").click()
    count(mini, "2 variables")
    chip = mini.locator("#active-filters .chip-topic")
    expect(chip).to_have_text("Housing ✕")
    expect(topic(mini, "Housing")).to_have_attribute("aria-pressed", "true")
    expect(mini.locator(".match-mode")).to_have_count(0)
    chip.click()
    count(mini, "16 variables")


def test_any_and_all_combine_two_topics(mini):
    open_topics(mini)
    mini.get_by_label("Minimum topic confidence").select_option("30")
    mini.get_by_role("button", name="Show the topics in Health").click()
    topic(mini, "Smoking").click()
    topic(mini, "Alcohol").click()
    count(mini, "2 variables")
    mode = mini.locator(".match-mode")
    expect(mode.get_by_role("button", name="any")).to_have_attribute("aria-pressed", "true")
    mode.get_by_role("button", name="all").click()
    count(mini, "1 variable")
    expect(row(mini, "smoke5")).to_have_count(1)


def test_threshold_changes_chips_counts_and_filter_and_is_remembered(mini):
    open_topics(mini)
    health = mini.locator("#tgrid-body .tg-row").nth(0)
    expect(health.locator(".ov-count")).to_have_text("1")
    expect(row(mini, "alc10").locator(".topic-chip")).to_have_count(0)
    mini.get_by_label("Minimum topic confidence").select_option("30")
    expect(health.locator(".ov-count")).to_have_text("2")
    expect(row(mini, "alc10").locator(".topic-chip")).to_have_text(["Alcohol"])
    topic(mini, "Health").click()
    count(mini, "2 variables")
    mini.get_by_label("Minimum topic confidence").select_option("90")
    count(mini, "1 variable")
    mini.reload()
    count(mini, "16 variables")
    open_topics(mini)
    expect(mini.get_by_label("Minimum topic confidence")).to_have_value("90")
    expect(row(mini, "smoke5").locator(".topic-chip")).to_have_text(["Smoking"])


def test_a_cell_filters_to_that_topic_at_that_sweep_and_again_releases_the_sweep(mini):
    grid = open_topics(mini)
    grid.get_by_label("Housing at 10y: 1").click()
    count(mini, "1 variable")
    expect(row(mini, "tenure10")).to_have_count(1)
    chips = mini.locator("#active-filters .chip")
    expect(chips).to_have_text(["10y ✕", "Housing ✕"])
    grid.get_by_label("Housing at 10y: 1").click()
    count(mini, "2 variables")
    expect(chips).to_have_text(["Housing ✕"])


def test_rows_show_their_strongest_topics_and_a_domain_stripe(mini):
    smoke = row(mini, "smoke5")
    expect(smoke.locator(".topic-chip")).to_have_text(["Smoking", "Alcohol"])
    expect(smoke).to_have_attribute("data-domain", "health")
    expect(row(mini, "tenure10")).to_have_attribute("data-domain", "housing")
    assert row(mini, "sex").first.get_attribute("data-domain") is None


def test_details_list_every_topic_dim_those_below_and_filter_on_click(mini):
    open_topics(mini)
    mini.get_by_label("Minimum topic confidence").select_option("70")
    row(mini, "smoke5").get_by_role("button", name="Show details for smoke5").click()
    tags = row(mini, "smoke5").locator(".vm-topic")
    expect(tags).to_have_text(["Smoking 95%", "Alcohol 55%"])
    expect(tags.nth(0)).not_to_have_class("vm-topic is-below")
    expect(tags.nth(1)).to_have_class("vm-topic is-below")
    tags.nth(0).click()
    count(mini, "1 variable")
    expect(mini.locator("#active-filters .chip-topic")).to_have_text("Smoking ✕")


@pytest.fixture
def untagged_site(site_with_data, tmp_path):
    data = tmp_path / "data"
    shutil.copytree(FIXTURE_DATA, data)
    path = data / "mini" / "manifest.json"
    manifest = json.loads(path.read_text())
    del manifest["topics"]
    path.write_text(json.dumps(manifest))
    return site_with_data(data)


def test_a_cohort_without_topics_hides_every_topic_feature(page, serve, untagged_site):
    page.goto(serve(untagged_site))
    count(page, "16 variables")
    expect(page.locator("#tgrid")).to_be_hidden()
    expect(page.locator("#results .topic-chip")).to_have_count(0)
    smoke = row(page, "smoke5")
    assert smoke.get_attribute("data-domain") is None
    smoke.get_by_role("button", name="Show details for smoke5").click()
    expect(smoke.locator(".vm-meta")).to_be_visible()
    expect(smoke.locator(".vm-topics")).to_have_count(0)
