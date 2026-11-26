"""Feature 007, user story 1: choose several cohorts and search them together.

The fixture site holds three fictional cohorts: mini (16 variables), mini2 (12) and mini3
(3, no topic tags). See specs/007-multi-cohort-search/contracts/cohort-choice.md and
contracts/variables-view.md ("Filter bar and results").
"""

import re

from playwright.sync_api import expect


def coh(page, key):
    """The header's toggle button for a cohort."""
    return page.locator(f'.cohorts button[data-cohort="{key}"]')


def group(page, key):
    """The result list's heading for a cohort."""
    return page.locator(f'#results .v-group[data-cohort="{key}"]')


def both(mini):
    """Choose mini2 as well as mini, and wait for both to be listed."""
    coh(mini, "mini2").click()
    expect(mini.locator("#results .v-group")).to_have_count(2)
    return mini


# T018 ─ choosing


def test_first_visit_chooses_the_first_cohort_only(mini):
    expect(coh(mini, "mini")).to_have_attribute("aria-pressed", "true")
    expect(coh(mini, "mini2")).to_have_attribute("aria-pressed", "false")
    expect(coh(mini, "mini3")).to_have_attribute("aria-pressed", "false")
    expect(mini.locator("#results .v-group")).to_have_count(0)
    expect(mini.locator("#results .coh-tag")).to_have_count(0)


def test_pressing_a_second_cohort_adds_it(mini):
    both(mini)
    expect(coh(mini, "mini")).to_have_attribute("aria-pressed", "true")
    expect(coh(mini, "mini2")).to_have_attribute("aria-pressed", "true")
    expect(mini).to_have_url(re.compile(r"#mini\+mini2$"))
    headings = mini.locator("#results .v-group")
    expect(headings.nth(0)).to_contain_text("Mini Test Cohort")
    expect(headings.nth(0)).to_contain_text("16")
    expect(headings.nth(1)).to_contain_text("Second Mini Test Cohort")
    expect(headings.nth(1)).to_contain_text("12")
    expect(mini.locator("#result-count")).to_contain_text("28 variables")


def test_the_choice_survives_a_reload(mini):
    both(mini)
    mini.goto(mini.url.split("#")[0])
    expect(coh(mini, "mini2")).to_have_attribute("aria-pressed", "true")
    expect(mini.locator("#results .v-group")).to_have_count(2)


def test_the_address_chooses_in_catalogue_order(page, serve, mini_site):
    page.goto(serve(mini_site) + "#mini2+mini")
    expect(coh(page, "mini")).to_have_attribute("aria-pressed", "true")
    expect(coh(page, "mini2")).to_have_attribute("aria-pressed", "true")
    expect(page).to_have_url(re.compile(r"#mini\+mini2$"))


def test_unknown_keys_in_the_address_are_dropped(page, serve, mini_site):
    page.goto(serve(mini_site) + "#mini2+nope")
    expect(coh(page, "mini2")).to_have_attribute("aria-pressed", "true")
    expect(coh(page, "mini")).to_have_attribute("aria-pressed", "false")
    expect(page.locator("#result-count")).to_have_text("12 variables")


def test_the_last_chosen_cohort_stays_chosen(mini):
    only = coh(mini, "mini")
    expect(only).to_have_attribute("aria-disabled", "true")
    only.click(force=True)  # aria-disabled: Playwright would wait for it to be enabled
    expect(only).to_have_attribute("aria-pressed", "true")
    expect(mini.locator("#result-count")).to_have_text("16 variables")
    both(mini)
    expect(only).not_to_have_attribute("aria-disabled", "true")


def test_removing_a_cohort_goes_back_to_one(mini):
    both(mini)
    coh(mini, "mini").click()
    expect(mini).to_have_url(re.compile(r"#mini2$"))
    expect(mini.locator("#results .v-group")).to_have_count(0)
    expect(mini.locator("#result-count")).to_have_text("12 variables")


# T019 ─ one search, results grouped by cohort


def test_one_search_runs_across_the_chosen_cohorts(mini):
    both(mini)
    mini.get_by_label("Search variables").fill("smok")
    expect(group(mini, "mini")).to_contain_text("1")
    expect(mini.locator('#results .vrow[data-key="mini:0:smoke5"]')).to_be_visible()
    expect(mini.locator('#results .vrow[data-key="mini2:2:smok11"]')).to_be_visible()
    count = mini.locator("#result-count")
    expect(count).to_contain_text("2 variables")
    expect(count.get_by_role("button", name=re.compile("^Mini 1"))).to_be_visible()
    expect(count.get_by_role("button", name=re.compile("^Mini2 1"))).to_be_visible()


def test_each_row_carries_its_cohort_tag(mini):
    both(mini)
    mini.get_by_label("Search variables").fill("smok")
    expect(mini.locator('.vrow[data-key="mini:0:smoke5"] .coh-tag')).to_have_text("Mini")
    expect(mini.locator('.vrow[data-key="mini2:2:smok11"] .coh-tag')).to_have_text("Mini2")


def test_a_cohort_count_jumps_to_its_group(mini):
    both(mini)
    mini.set_viewport_size({"width": 1200, "height": 500})
    mini.locator("#result-count").get_by_role("button", name=re.compile("^Mini2")).click()
    expect(group(mini, "mini2")).to_be_in_viewport()


def test_the_same_name_in_two_cohorts_is_two_variables(mini):
    both(mini)
    mini.get_by_label("Search variables").fill("sex")
    first = mini.locator('.vrow[data-key="mini:0:sex"] .vrow-btn')
    other = mini.locator('.vrow[data-key="mini2:0:sex"] .vrow-btn')
    expect(first).to_be_visible()
    expect(other).to_be_visible()
    first.click()
    expect(first).to_have_attribute("aria-pressed", "true")
    expect(other).to_have_attribute("aria-pressed", "false")


# T020 ─ filters with several cohorts


def file_filter_on_mini2(page):
    """Open smok11's details and filter to its file, mini2_age11."""
    page.get_by_label("Search variables").fill("smok11")
    page.get_by_role("button", name="Show details for smok11").click()
    page.get_by_role("button", name="all in this file").click()


def test_a_file_filter_names_its_cohort_and_the_others_say_so(mini):
    both(mini)
    file_filter_on_mini2(mini)
    expect(mini.locator("#active-filters")).to_contain_text("Mini2 · mini2_age11")
    heading = group(mini, "mini")
    expect(heading).to_contain_text("filtered to Mini2 · mini2_age11")
    heading.get_by_role("button", name="Clear filter").click()
    expect(mini.locator("#active-filters")).not_to_contain_text("mini2_age11")
    expect(group(mini, "mini")).to_contain_text("16")


def test_a_newly_chosen_cohort_says_it_is_filtered_away(mini):
    both(mini)
    file_filter_on_mini2(mini)
    coh(mini, "mini3").click()
    expect(group(mini, "mini3")).to_contain_text("filtered to Mini2 · mini2_age11")


def test_removing_the_filtered_cohort_drops_its_filter(mini):
    both(mini)
    file_filter_on_mini2(mini)
    coh(mini, "mini2").click()
    expect(mini.locator("#active-filters")).not_to_contain_text("mini2_age11")
    expect(mini.locator("#result-count")).to_have_text("16 variables")


def test_the_level_filter_applies_to_every_cohort(mini):
    both(mini)
    mini.get_by_label("Measurement level").select_option(label="Ordinal (5)")
    expect(mini.locator("#result-count")).to_contain_text("5 variables")
    expect(group(mini, "mini")).to_contain_text("3")
    expect(group(mini, "mini2")).to_contain_text("2")


# T021 ─ a cohort that fails to load; title and footer


def test_a_cohort_that_fails_to_load_can_be_retried(mini):
    mini.route("**/data/mini2/index.json", lambda route: route.fulfill(status=500))
    coh(mini, "mini2").click()
    failed = group(mini, "mini2")
    expect(failed).to_contain_text("Could not load Mini2")
    expect(mini.locator('.vrow[data-key="mini:0:smoke5"]')).to_be_visible()
    mini.unroute("**/data/mini2/index.json")
    failed.get_by_role("button", name="Retry").click()
    expect(group(mini, "mini2")).to_contain_text("12")
    expect(mini.locator("#result-count")).to_contain_text("28 variables")


def test_title_subtitle_and_footer_name_every_chosen_cohort(mini):
    both(mini)
    expect(mini).to_have_title("Mini + Mini2 · Cohort Data Builder")
    expect(mini.locator("#mark-sub")).to_have_text("Mini + Mini2")
    expect(mini.locator("#foot-counts")).to_contain_text("28 variables · 8 files · 2 cohorts")
