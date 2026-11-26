"""The site is usable at phone width (FR-035)."""

import json
import shutil

import pytest
from playwright.sync_api import expect

PHONE = {"width": 375, "height": 812}


@pytest.fixture
def phone(page, serve, mini_site):
    page.set_viewport_size(PHONE)
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    return page


def no_sideways_scroll(page):
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= PHONE["width"], f"page is {width}px wide"


def inside_screen(locator):
    box = locator.bounding_box()
    assert box is not None, "not shown"
    assert box["x"] >= 0 and box["x"] + box["width"] <= PHONE["width"] + 0.5, box


def test_variables_view_fits_and_works(phone):
    no_sideways_scroll(phone)
    search = phone.get_by_label("Search variables")
    inside_screen(search)
    search.fill("tenure")
    expect(phone.locator("#result-count")).to_have_text("2 variables")
    first = phone.locator("#results .vrow-btn").first
    inside_screen(first)
    first.click()
    expect(first).to_have_attribute("aria-pressed", "true")
    no_sideways_scroll(phone)


def test_selection_panel_opens_from_its_toggle(phone):
    phone.locator("#results .vrow-btn").nth(2).click()
    toggle = phone.locator("#sp-toggle")
    inside_screen(toggle)
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    listed = phone.locator("#sp-list").get_by_text("smoke5")
    expect(listed).to_be_visible()
    inside_screen(listed)
    assert phone.locator("#sp-list").bounding_box()["height"] > 20, "the list is collapsed"
    no_sideways_scroll(phone)


def test_selection_view_fits_and_downloads(phone):
    phone.locator("#results .vrow-btn").nth(2).click()
    phone.get_by_role("button", name="Selection").first.click()
    button = phone.locator("#basket-download")
    button.scroll_into_view_if_needed()
    inside_screen(button)
    inside_screen(phone.get_by_label("Output column name for smoke5"))
    no_sideways_scroll(phone)
    with phone.expect_download():
        button.click()


@pytest.fixture
def four_cohort_site(mini_site):
    """The fixture site with a fourth fictional cohort: a copy of the first under a new key."""
    data = mini_site / "data"
    catalogue = json.loads((data / "datasets.json").read_text())
    first = catalogue["datasets"][0]
    shutil.copytree(data / first["key"], data / "mini4")
    catalogue["datasets"].append({**first, "key": "mini4", "name": "Mini4"})
    (data / "datasets.json").write_text(json.dumps(catalogue))
    return mini_site


@pytest.mark.parametrize("text", ["Normal text", "Larger text", "Largest text"])
def test_four_cohorts_wrap_in_the_header_at_phone_width(page, serve, four_cohort_site, text):
    page.set_viewport_size({"width": 390, "height": 812})
    page.goto(serve(four_cohort_site))
    buttons = page.locator(".cohorts button")
    expect(buttons).to_have_count(4)
    page.get_by_role("group", name="Text size").get_by_role("button", name=text).click()
    for i in range(1, 4):
        buttons.nth(i).click()
    expect(page.locator("#results .v-group")).to_have_count(4)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    for i in range(4):
        box = buttons.nth(i).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390.5, box
