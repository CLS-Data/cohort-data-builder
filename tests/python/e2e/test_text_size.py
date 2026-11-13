"""A text-size control for readers who need larger text (US5)."""

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect

AXE = Axe()


@pytest.fixture
def mini(page, serve, mini_site):
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    return page


def size(page, selector):
    return page.locator(selector).first.evaluate("e => parseFloat(getComputedStyle(e).fontSize)")


def test_text_size_buttons_enlarge_every_text_and_are_remembered(mini):
    group = mini.get_by_role("group", name="Text size")
    normal = group.get_by_role("button", name="Normal text")
    expect(normal).to_have_attribute("aria-pressed", "true")
    body, name = size(mini, "body"), size(mini, "#results .v-name")

    group.get_by_role("button", name="Largest text").click()
    expect(group.get_by_role("button", name="Largest text")).to_have_attribute(
        "aria-pressed", "true"
    )
    assert size(mini, "body") == pytest.approx(body * 1.5)
    assert size(mini, "#results .v-name") == pytest.approx(name * 1.5)

    mini.reload()
    expect(mini.locator("#result-count")).to_have_text("16 variables")
    assert size(mini, "body") == pytest.approx(body * 1.5)
    mini.goto(mini.url.split("#")[0] + "tutorial/")  # same origin, same storage
    assert size(mini, "body") == pytest.approx(body * 1.5)


@pytest.mark.parametrize("width", [1366, 390])
def test_largest_text_still_fits_without_sideways_scrolling(mini, width):
    mini.set_viewport_size({"width": width, "height": 800})
    mini.get_by_role("group", name="Text size").get_by_role("button", name="Largest text").click()
    assert mini.evaluate("document.documentElement.scrollWidth") <= width
    mini.locator("#results .vrow-btn:not([aria-disabled])").first.click()
    mini.get_by_role("button", name="Selection").first.click()
    expect(mini.locator("#basket-download")).to_be_visible()
    assert mini.evaluate("document.documentElement.scrollWidth") <= width
    found = AXE.run(mini).response["violations"]
    assert [v["id"] for v in found if v["impact"] in ("serious", "critical")] == []
