import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

SITE = Path(__file__).resolve().parents[3] / "site"


@pytest.fixture
def mini(page, serve, mini_site):
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    return page


def row(page, name, nth=0):
    return (
        page.locator("#results .vrow")
        .filter(has=page.locator(".v-name", has_text=re.compile(f"^{name}$")))
        .nth(nth)
    )


def pick(page, name, nth=0, **kwargs):
    row(page, name, nth).locator(".vrow-btn").click(**kwargs)


def count(page):
    return page.locator("#sp-count")


def test_click_toggles_mark_count_and_tally(mini):
    pick(mini, "smoke5")
    btn = row(mini, "smoke5").locator(".vrow-btn")
    expect(btn).to_have_attribute("aria-pressed", "true")
    expect(btn.locator(".v-check")).to_have_text("✓")
    expect(count(mini)).to_have_text("1 variable selected")
    expect(mini.locator("#basket-tally")).to_have_text("1")
    pick(mini, "smoke5")
    expect(btn.locator(".v-check")).to_have_text("＋")
    expect(count(mini)).to_have_text("Nothing selected yet")
    expect(mini.locator("#basket-tally")).to_be_hidden()


def test_shift_click_adds_then_removes_a_range_and_announces_it(mini):
    pick(mini, "sex")
    pick(mini, "nolab5", modifiers=["Shift"])
    expect(count(mini)).to_have_text("5 variables selected")
    expect(mini.get_by_role("status").filter(has_text="Added")).to_have_text("Added 4 variables")
    pick(mini, "smoke5", modifiers=["Shift"])
    expect(count(mini)).to_have_text("1 variable selected")
    expect(mini.get_by_role("status").filter(has_text="Removed")).to_have_text(
        "Removed 4 variables"
    )


def test_select_all_appears_for_selectable_results_and_flips(mini):
    select_all = mini.locator("#select-all")
    expect(select_all).to_have_text("Select all 12")
    mini.locator("#spine-track [data-wave='0']").click()
    expect(select_all).to_have_text("Select all 5")
    select_all.click()
    expect(count(mini)).to_have_text("5 variables selected")
    expect(select_all).to_have_text("Remove all 5")
    select_all.click()
    expect(count(mini)).to_have_text("Nothing selected yet")
    mini.locator("#spine-track [data-wave='0']").click()
    mini.get_by_label("Search variables").fill("person")
    expect(mini.locator("#result-count")).to_have_text("3 variables")
    expect(select_all).to_be_hidden()


def test_identifier_is_always_included_and_not_toggleable(mini):
    btn = row(mini, "PID").locator(".vrow-btn")
    expect(btn.locator(".v-check")).to_have_text("✓")
    expect(btn).to_have_attribute("aria-disabled", "true")
    expect(btn).to_have_attribute("title", re.compile("every download"))
    btn.click(force=True)
    expect(count(mini)).to_have_text("Nothing selected yet")


def test_file_without_identifier_cannot_be_selected(mini):
    btn = row(mini, "areacode").locator(".vrow-btn")
    expect(btn).to_have_attribute("aria-disabled", "true")
    expect(btn).to_have_attribute("title", re.compile("mini_noid has no PID column"))
    btn.click(force=True)
    expect(count(mini)).to_have_text("Nothing selected yet")


def test_selection_survives_reload_for_its_cohort(mini):
    pick(mini, "smoke5")
    pick(mini, "sex", nth=1)
    pick(mini, "hhrel")
    expect(count(mini)).to_have_text("3 variables selected")
    keys = mini.evaluate("Object.keys(localStorage)")
    assert "cohort-data-builder:mini:selection" in keys
    mini.reload()
    expect(count(mini)).to_have_text("3 variables selected")
    expect(row(mini, "hhrel").locator(".vrow-btn")).to_have_attribute("aria-pressed", "true")


def test_panel_groups_filters_removes_and_clears(mini):
    for name in ("smoke5", "tenure5", "alc10", "hhrel"):
        pick(mini, name)
    heads = mini.locator("#sp-list .sp-grp-name")
    expect(heads).to_have_text(["5y", "10y"])
    mini.locator("#spanel").get_by_role("button", name="File").click()
    expect(heads).to_have_text(["mini_age10", "mini_age5", "mini_grid"])

    mini.get_by_label("Filter the selection").fill("tenure")
    expect(mini.locator("#sp-list .sp-name")).to_have_text(["tenure5"])
    mini.get_by_label("Filter the selection").fill("")

    first_x = mini.locator("#sp-list .sp-x").first
    first_x.focus()
    first_x.press("Enter")
    expect(count(mini)).to_have_text("3 variables selected")
    expect(mini.locator("#sp-list .sp-x").first).to_be_focused()

    clear = mini.locator("#sp-clear")
    clear.click()
    expect(clear).to_have_text("Clear all 3?")
    expect(count(mini)).to_have_text("3 variables selected")
    clear.click()
    expect(count(mini)).to_have_text("Nothing selected yet")


def test_review_button_opens_the_selection_view(mini):
    pick(mini, "smoke5")
    mini.get_by_role("button", name=re.compile("Review & download")).click()
    expect(mini.get_by_role("button", name=re.compile("^Selection"))).to_have_attribute(
        "aria-current", "page"
    )


def test_site_works_when_storage_throws(page, serve, mini_site):
    page.add_init_script(
        "Object.defineProperty(window, 'localStorage', "
        "{get() { throw new DOMException('denied', 'SecurityError'); }});"
    )
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    pick(page, "smoke5")
    expect(count(page)).to_have_text("1 variable selected")


def test_real_large_group_shows_200_until_show_all(page, serve):
    page.goto(serve(SITE) + "#bcs70")
    expect(page.locator("#result-count")).to_have_text("32,452 variables")
    expect(page.locator("#select-all")).to_be_hidden()  # 32,452 is over the limit
    page.get_by_label("Search variables").fill("Source by which individual was linked")
    page.get_by_role("button", name="Show details for source", exact=True).click()
    page.get_by_role("button", name="all in this file").click()
    expect(page.locator("#result-count")).to_have_text("286 variables")
    page.locator("#select-all").click()
    expect(count(page)).to_have_text("285 variables selected")
    expect(page.locator("#sp-list .sp-row")).to_have_count(200)
    page.get_by_role("button", name="Show all 285").click()
    expect(page.locator("#sp-list .sp-row")).to_have_count(285)
