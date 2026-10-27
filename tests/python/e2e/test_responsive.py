"""The site is usable at phone width (FR-035)."""

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
    expect(phone.locator("#sp-list")).to_contain_text("smoke5")
    inside_screen(phone.locator("#sp-list"))
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
