import json
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

SITE = Path(__file__).resolve().parents[3] / "site"


@pytest.fixture
def mini_url(serve, mini_site):
    return serve(mini_site, "/cohort-data-builder/")


@pytest.fixture
def real_url(serve):
    return serve(SITE)


def test_page_shell(page, mini_url):
    page.goto(mini_url)
    expect(page).to_have_title(re.compile("Cohort Data Builder"))
    expect(page.get_by_role("link", name="Skip to content")).to_have_attribute("href", "#main")
    beta = page.get_by_role("note")
    expect(beta).to_contain_text("Beta")
    expect(beta.get_by_role("link")).to_have_attribute("href", re.compile(r"/issues"))


def test_cohort_name_and_footer_counts(page, mini_url):
    page.goto(mini_url)
    expect(page.locator("#mark-sub")).to_have_text("Mini Test Cohort")
    expect(page.locator("#foot-counts")).to_contain_text("16 variables · 4 files · 3 sweeps")
    expect(page).to_have_title("Mini · Cohort Data Builder")


def test_picker_lists_every_cohort(page, real_url):
    keys = [d["key"] for d in json.loads((SITE / "data/datasets.json").read_text())["datasets"]]
    page.goto(real_url)
    options = page.get_by_label("Cohort").locator("option")
    expect(options).to_have_count(len(keys))
    assert [options.nth(i).get_attribute("value") for i in range(len(keys))] == keys


def test_hash_opens_cohort_and_picker_updates_hash(page, real_url):
    page.goto(real_url + "#next_steps")
    expect(page.locator("#mark-sub")).to_contain_text("Next Steps")
    expect(page.get_by_label("Cohort")).to_have_value("next_steps")
    page.get_by_label("Cohort").select_option("bcs70")
    expect(page).to_have_url(re.compile("#bcs70$"))
    expect(page.locator("#mark-sub")).to_have_text("1970 British Cohort Study")


def test_last_cohort_reopens_without_hash(page, real_url):
    page.goto(real_url)
    page.get_by_label("Cohort").select_option("next_steps")
    expect(page).to_have_url(re.compile("#next_steps$"))
    page.goto(real_url)
    expect(page.get_by_label("Cohort")).to_have_value("next_steps")


def test_missing_data_shows_message(page, serve, site_with_data):
    page.goto(serve(site_with_data(None)))
    expect(page.get_by_text("Could not load the site data")).to_be_visible()


def test_theme_choice_survives_reload(page, mini_url):
    page.emulate_media(color_scheme="light")
    page.goto(mini_url)
    html = page.locator("html")
    page.get_by_role("button", name="Switch colour theme").click()
    expect(html).to_have_attribute("data-theme", "dark")
    page.reload()
    expect(html).to_have_attribute("data-theme", "dark")
    page.get_by_role("button", name="Switch colour theme").click()
    expect(html).to_have_attribute("data-theme", "light")
