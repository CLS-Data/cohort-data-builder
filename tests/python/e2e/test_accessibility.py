"""Automated accessibility check (SC-009): no serious or critical axe-core violations in any
view, in either theme."""

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect

AXE = Axe()


def serious(page):
    """Return the serious and critical violations axe finds, one readable line each."""
    found = AXE.run(page).response["violations"]
    return [
        f"{v['id']} ({v['impact']}): {v['help']} — "
        + "; ".join(n["target"][0] for n in v["nodes"][:5])
        for v in found
        if v["impact"] in ("serious", "critical")
    ]


@pytest.fixture(params=["light", "dark"])
def themed(request, page, serve, mini_site):
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.emulate_media(color_scheme=request.param)
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    page.evaluate(f"document.documentElement.dataset.theme = {request.param!r}")
    return page


def test_variables_view_with_topics_open_and_a_row_expanded(themed):
    page = themed
    page.locator("#tgrid-toggle").click()
    page.get_by_role("button", name="Show the topics in Health").click()
    page.get_by_role("button", name="Show details for smoke5").click()
    expect(page.locator(".vm-topic").first).to_be_visible()
    page.locator("#results .vrow-btn").nth(2).click()  # something in the selection panel
    assert serious(page) == []


def test_selection_view(themed):
    page = themed
    page.locator("#results .vrow-btn").nth(2).click()
    page.locator("#results .vrow-btn").nth(3).click()
    page.get_by_role("button", name="Selection").first.click()
    expect(page.locator("#basket-download")).to_be_visible()
    assert serious(page) == []
