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


def row(page, name):
    return page.locator("#results .vrow").filter(
        has=page.locator(".v-name", has_text=re.compile(f"^{name}$"))
    )


def open_details(page, name):
    page.get_by_role("button", name=f"Show details for {name}").first.click()
    return row(page, name).first.locator(".vrow-more")


def names(page):
    return page.locator("#results .vrow .v-name").all_inner_texts()


def test_overview_shows_cohort_counts_and_sweeps_in_order(mini):
    about = mini.locator("#ov-about")
    expect(about).to_contain_text("Mini Test Cohort")
    expect(about).to_contain_text("A tiny fictional cohort for tests.")
    expect(about).to_contain_text("16 variables in 4 files")
    bars = mini.locator("#spine-track [data-wave]")
    expect(bars.locator(".node-age")).to_have_text(["5y", "10y", "xwave"])
    expect(bars.locator(".node-n")).to_have_text(["6", "9", "1"])
    expect(mini.locator("#spine-title")).to_have_text("All variables")


def test_typing_filters_and_highlights(mini):
    mini.get_by_label("Search variables").fill("SMOK")
    expect(mini.locator("#result-count")).to_have_text("1 variable")
    assert names(mini) == ["smoke5"]
    expect(row(mini, "smoke5").locator(".v-name mark")).to_have_text("smok")
    expect(row(mini, "smoke5").locator(".v-label mark")).to_have_text("smok")
    expect(mini.locator("#spine-title")).to_have_text("Matching variables")


def test_sweep_bar_filters_and_clicking_again_clears(mini):
    bar = mini.locator("#spine-track [data-wave='1']")
    bar.click()
    expect(mini.locator("#result-count")).to_have_text("9 variables")
    expect(bar).to_have_attribute("aria-pressed", "true")
    expect(mini.locator("#active-filters .chip")).to_have_text(re.compile("10y"))
    mini.locator("#spine-track [data-wave='1']").click()
    expect(mini.locator("#result-count")).to_have_text("16 variables")
    expect(mini.locator("#active-filters .chip")).to_have_count(0)


def test_empty_sweep_is_still_drawn(mini):
    mini.get_by_label("Search variables").fill("sex")
    expect(mini.locator("#result-count")).to_have_text("2 variables")
    xwave = mini.locator("#spine-track [data-wave='2']")
    expect(xwave).to_have_class(re.compile("is-empty"))
    expect(xwave.locator(".node-n")).to_have_text("—")


def test_level_dropdown_counts_and_disables_empty_levels(mini):
    level = mini.get_by_label("Measurement level")
    expect(level.locator("option")).to_have_text(
        ["Any level (16)", "Nominal (11)", "Ordinal (3)", "Scale (1)", "Unrecorded (1)"]
    )
    mini.get_by_label("Search variables").fill("sex")
    expect(level.locator("option", has_text="Scale")).to_be_disabled()
    mini.get_by_label("Search variables").fill("")
    level.select_option(label="Scale (1)")
    assert names(mini) == ["weight10"]


def test_file_filter_chip_and_clear(mini):
    open_details(mini, "hhrel").get_by_role("button", name="all in this file").click()
    expect(mini.locator("#result-count")).to_have_text("2 variables")
    chip = mini.locator("#active-filters .chip")
    expect(chip).to_have_text(re.compile("mini_grid"))
    chip.click()
    expect(mini.locator("#result-count")).to_have_text("16 variables")

    mini.get_by_label("Search variables").fill("e")
    mini.locator("#spine-track [data-wave='0']").click()
    mini.get_by_label("Measurement level").select_option("0")
    mini.get_by_role("button", name="Clear", exact=True).click()
    expect(mini.locator("#result-count")).to_have_text("16 variables")
    expect(mini.get_by_label("Search variables")).to_have_value("")


def test_details_answers_before_missing_with_facts(mini):
    more = open_details(mini, "tenure5")
    expect(more.locator(".vm-values").first).to_contain_text("Owned")
    expect(more.locator(".vm-values.is-na")).to_contain_text("Not applicable")
    expect(more).to_contain_text("mini_age5")
    expect(more).to_contain_text("Age 5 interview")
    expect(more).to_contain_text("Nominal")
    expand = mini.get_by_role("button", name="Hide details for tenure5")
    expect(expand).to_be_focused()
    expect(expand).to_have_attribute("aria-expanded", "true")


def test_details_kept_and_lossy(mini):
    expect(open_details(mini, "alc10")).to_contain_text("Kept as answers")
    expect(open_details(mini, "mood10").locator(".vm-lossy")).to_contain_text("Don't know ⚠")


def test_details_identifier_and_continuous(mini):
    expect(open_details(mini, "weight10")).to_contain_text("continuous")
    expect(open_details(mini, "pid")).to_contain_text("identifier")


def test_same_label_link_jumps_to_the_other_variable(mini):
    more = open_details(mini, "tenure5")
    more.get_by_role("button", name=re.compile("tenure10")).click()
    expect(mini.get_by_label("Search variables")).to_have_value("Housing tenure of the family home")
    expect(row(mini, "tenure10").locator(".vrow-more")).to_be_visible()


def test_no_match_message_and_clear(mini):
    mini.get_by_label("Search variables").fill("zzzz")
    expect(mini.locator("#results")).to_contain_text("No variables match")
    mini.get_by_role("button", name="Clear the filters").click()
    expect(mini.locator("#result-count")).to_have_text("16 variables")


def test_real_bcs70_search_paging_and_details(page, serve):
    page.goto(serve(SITE) + "#bcs70")
    expect(page.locator("#result-count")).to_have_text("32,452 variables")
    expect(page.locator("#results .vrow")).to_have_count(200)
    page.get_by_role("button", name="Show 200 more").click()
    expect(page.locator("#results .vrow")).to_have_count(400)

    page.get_by_label("Search variables").fill("smoke")
    expect(page.locator("#result-count")).not_to_have_text("32,452 variables")
    page.locator("#spine-track [data-wave]:not(.is-empty)").nth(2).click()
    page.locator("#results .v-expand").first.click()
    more = page.locator("#results .vrow-more").first
    expect(more.locator(".vm-meta")).to_be_visible()
    expect(more.locator(".vm-values, .vm-note").first).to_be_visible()
