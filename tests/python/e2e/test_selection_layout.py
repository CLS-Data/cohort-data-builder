"""The Selection view keeps the download in reach however long the selection is (US2)."""

import re
from pathlib import Path

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect

SITE = Path(__file__).resolve().parents[3] / "site"
AXE = Axe()


def select_285(page):
    """BCS70's 285 linkage-source variables: a real, long selection."""
    expect(page.locator("#result-count")).to_have_text("37,562 variables")
    page.get_by_label("Search variables").fill("Source by which individual was linked")
    page.get_by_role("button", name="Show details for source", exact=True).click()
    page.get_by_role("button", name="all in this file").click()
    expect(page.locator("#result-count")).to_have_text("286 variables")
    page.locator("#select-all").click()
    expect(page.locator("#sp-count")).to_have_text("285 variables selected")


def open_selection(page):
    page.get_by_role("button", name=re.compile("^Selection")).click()
    expect(page.locator("#basket-cols li")).to_have_count(286)


def in_viewport(page, selector):
    box = page.locator(selector).bounding_box()
    size = page.viewport_size
    return (
        box is not None
        and box["y"] >= 0
        and box["y"] + box["height"] <= size["height"] + 1
        and box["x"] >= 0
        and box["x"] + box["width"] <= size["width"] + 1
    )


@pytest.fixture
def bcs70(page, serve):
    page.goto(serve(SITE) + "#bcs70")
    return page


def test_download_stays_in_view_while_the_list_scrolls(bcs70):
    page = bcs70
    page.set_viewport_size({"width": 1366, "height": 768})
    select_285(page)
    open_selection(page)
    assert in_viewport(page, "#basket-download")
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1")
    expect(page.get_by_role("button", name="Download options")).to_be_hidden()
    expect(page.get_by_label("R", exact=True)).to_be_visible()
    # The download panel is beside the list, on the right, from the top of the view.
    listing = page.locator("#basket-scroll").bounding_box()
    panel = page.locator("#basket-download-area").bounding_box()
    assert panel["x"] >= listing["x"] + listing["width"] - 1
    assert abs(panel["y"] - listing["y"]) <= 1
    assert in_viewport(page, "#basket-download-area")
    before = page.locator("#basket-download").bounding_box()["y"]
    page.locator("#basket-scroll").evaluate("el => el.scrollBy(0, 2000)")
    assert page.locator("#basket-scroll").evaluate("el => el.scrollTop") > 0
    assert page.locator("#basket-download").bounding_box()["y"] == before


def test_a_blocked_download_says_why_and_shows_the_problem(bcs70):
    page = bcs70
    page.set_viewport_size({"width": 1366, "height": 768})
    select_285(page)
    open_selection(page)
    name = page.locator("#basket-cols .col-input").last
    name.fill("1bad")
    name.press("Enter")
    expect(page.locator("#basket-download")).to_be_disabled()
    area = page.locator("#basket-download-area")
    expect(area).to_contain_text("1 column name needs changing")
    page.locator("#basket-scroll").evaluate("el => el.scrollTo(0, 0)")
    area.get_by_role("button", name="Show").click()
    bad = page.locator("#basket-cols .col-input[aria-invalid='true']")
    expect(bad).to_be_focused()
    assert in_viewport(page, "#basket-cols .col-input[aria-invalid='true']")


def test_on_a_phone_the_download_bar_sticks_to_the_bottom(bcs70):
    page = bcs70
    page.set_viewport_size({"width": 390, "height": 844})
    select_285(page)
    open_selection(page)
    assert in_viewport(page, "#basket-download")
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    expect(page.get_by_label("R", exact=True)).to_be_hidden()
    page.get_by_role("button", name="Download options").click()
    expect(page.get_by_label("R", exact=True)).to_be_visible()
    found = AXE.run(page).response["violations"]
    assert [v["id"] for v in found if v["impact"] in ("serious", "critical")] == []
