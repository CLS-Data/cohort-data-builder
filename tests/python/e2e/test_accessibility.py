"""Automated accessibility check (SC-009): no serious or critical axe-core violations in any
view, in either theme."""

import pytest
from playwright.sync_api import expect


@pytest.fixture(params=["light", "dark"])
def themed(request, page, serve, mini_site):
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.emulate_media(color_scheme=request.param)
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    page.evaluate(f"document.documentElement.dataset.theme = {request.param!r}")
    return page


def test_variables_view_with_topics_open_and_a_row_expanded(themed, serious):
    page = themed
    page.locator("#tgrid-toggle").click()
    page.get_by_role("button", name="Show the topics in Health").click()
    page.get_by_role("button", name="Show details for smoke5").click()
    expect(page.locator(".vm-topic").first).to_be_visible()
    page.locator("#results .vrow-btn").nth(2).click()  # something in the selection panel
    assert serious(page) == []


def test_selection_view(themed, serious):
    page = themed
    page.locator("#results .vrow-btn").nth(2).click()
    page.locator("#results .vrow-btn").nth(3).click()
    page.get_by_role("button", name="Selection").first.click()
    expect(page.locator("#basket-download")).to_be_visible()
    assert serious(page) == []


@pytest.mark.parametrize("text", ["", "larger"])
def test_two_cohorts_with_topics_open(themed, serious, text):
    page = themed
    if text:
        page.get_by_role("button", name="Largest text").click()
    page.locator('.cohorts button[data-cohort="mini2"]').click()
    expect(page.locator("#results .v-group")).to_have_count(2)
    page.locator("#tgrid-toggle").click()
    page.get_by_role("button", name="Show the topics in Health").click()
    page.locator('#results .vrow[data-key="mini2:2:smok11"] .vrow-btn').click()
    assert serious(page) == []
    page.get_by_role("button", name="Selection").first.click()
    expect(page.locator("#basket-download")).to_be_visible()
    assert serious(page) == []
