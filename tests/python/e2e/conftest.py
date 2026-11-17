"""Fixtures shared by the browser tests."""

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect

AXE = Axe()


@pytest.fixture
def mini(page, serve, mini_site):
    """The site opened on the fixture cohort, its 16 variables listed."""
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    return page


@pytest.fixture
def serious():
    """A function listing the serious and critical axe violations on a page, one line each."""

    def check(page):
        found = AXE.run(page).response["violations"]
        return [
            f"{v['id']} ({v['impact']}): {v['help']} — "
            + "; ".join(n["target"][0] for n in v["nodes"][:5])
            for v in found
            if v["impact"] in ("serious", "critical")
        ]

    return check
