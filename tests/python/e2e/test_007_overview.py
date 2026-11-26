"""Feature 007, user story 2: the overview stacks by cohort on one age axis.

Fixture sweeps: mini 5y, 10y, xwave; mini2 3y, w2 (age 7), 11y, extra; so with both the
axis reads 3, 5, 7, 10, 11, ?. See contracts/variables-view.md ("Overview").
"""

from playwright.sync_api import expect


def coh(page, key):
    """The header's toggle button for a cohort."""
    return page.locator(f'.cohorts button[data-cohort="{key}"]')


def sweep_row(page, key):
    """A cohort's row of sweep bars in the overview."""
    return page.locator(f'#ov-chart .ov-coh[data-cohort="{key}"]')


def columns_with_bars(page, key):
    """The axis columns in which a cohort's row has a bar."""
    cells = sweep_row(page, key).locator("li:has(button.node)")
    return [cells.nth(i).get_attribute("data-col") for i in range(cells.count())]


def sub_row(page, topic, key):
    """A cohort's sub-row under a topic row ("t:<id>") or domain row ("d:<id>")."""
    return page.locator(f'#tgrid-body .tg-sub[data-of="{topic}"][data-cohort="{key}"]')


def both(mini):
    """Choose mini2 as well as mini."""
    coh(mini, "mini2").click()
    expect(sweep_row(mini, "mini2")).to_be_visible()
    return mini


def open_health(page):
    """Open the topic rows and the health domain."""
    page.locator("#tgrid-toggle").click()
    page.locator('#tgrid-body [data-expand="health"]').click()


# T027 ─ one cohort as today; two on one age axis


def test_one_cohort_keeps_todays_overview(mini):
    expect(mini.locator("#spine-track li")).to_have_count(3)
    expect(mini.locator("#spine-track .node-age")).to_have_text(["5y", "10y", "xwave"])
    expect(mini.locator("#spine-track.is-axis")).to_have_count(0)
    expect(mini.locator("#ov-chart .ov-coh")).to_have_count(0)


def test_two_cohorts_have_a_line_each_in_the_description(mini):
    both(mini)
    lines = mini.locator("#ov-about .ov-about-line")
    expect(lines).to_have_count(2)
    expect(lines.nth(0)).to_contain_text("Mini Test Cohort")
    expect(lines.nth(0)).to_contain_text("16 variables")
    expect(lines.nth(1)).to_contain_text("Second Mini Test Cohort")
    expect(lines.locator(".coh-mark")).to_have_count(2)


def test_two_cohorts_share_an_age_axis(mini):
    both(mini)
    expect(mini.locator("#spine-track.is-axis li")).to_have_text(["3", "5", "7", "10", "11", "?"])
    expect(sweep_row(mini, "mini").locator(".ov-label")).to_contain_text("Mini")
    expect(sweep_row(mini, "mini").locator(".ov-count")).to_have_text("16")
    expect(sweep_row(mini, "mini2").locator(".ov-count")).to_have_text("12")
    assert columns_with_bars(mini, "mini") == ["1", "3", "5"]
    assert columns_with_bars(mini, "mini2") == ["0", "2", "4", "5"]


# T028 ─ empty rows, clicking a bar, topic sub-rows


def test_a_cohort_with_no_matches_keeps_its_row(mini):
    both(mini)
    mini.get_by_label("Search variables").fill("zzzz")
    expect(sweep_row(mini, "mini").locator(".ov-count")).to_have_text("0")
    expect(sweep_row(mini, "mini2").locator(".ov-count")).to_have_text("0")


def test_a_bar_filters_to_that_cohorts_sweep(mini):
    both(mini)
    bar = sweep_row(mini, "mini2").locator('li[data-col="2"] button')
    expect(bar).to_have_attribute("title", "Mini2 w2 (age 7) — 3 variables")
    bar.click()
    expect(mini.locator("#active-filters")).to_contain_text("Mini2 · w2")
    expect(mini.locator("#result-count")).to_contain_text("3 variables")
    expect(bar).to_have_attribute("aria-pressed", "true")


def test_topic_rows_have_a_sub_row_per_cohort(mini):
    both(mini)
    open_health(mini)
    expect(sub_row(mini, "t:smoking", "mini").locator("button.tg-cell")).to_have_count(3)
    mini2_at_11 = sub_row(mini, "t:smoking", "mini2").locator('[data-col="4"]')
    expect(mini2_at_11).to_have_attribute("aria-label", "Smoking, Mini2 at 11y: 1")
    # vaping is in mini2's topics only
    expect(sub_row(mini, "t:vaping", "mini").locator("button.tg-cell")).to_have_count(0)
    expect(sub_row(mini, "t:vaping", "mini2").locator("button.tg-cell")).to_have_count(4)


def test_an_untagged_cohort_says_so_in_the_topic_rows(mini):
    both(mini)
    coh(mini, "mini3").click()
    expect(sweep_row(mini, "mini3")).to_be_visible()
    open_health(mini)
    expect(sub_row(mini, "d:health", "mini3")).to_contain_text("no topic tags")
    expect(sub_row(mini, "t:smoking", "mini3")).to_contain_text("no topic tags")


def test_a_sub_row_cell_filters_to_that_topic_at_that_sweep(mini):
    both(mini)
    open_health(mini)
    sub_row(mini, "t:smoking", "mini").locator('[data-col="1"]').click()
    chips = mini.locator("#active-filters")
    expect(chips).to_contain_text("Mini · 5y")
    expect(chips).to_contain_text("Smoking")
    expect(mini.locator('#results .vrow[data-key="mini:0:smoke5"]')).to_be_visible()


# T029 ─ phone width


def test_the_chart_scrolls_inside_itself_at_phone_width(page, serve, mini_site):
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(serve(mini_site) + "#mini+mini2")
    expect(sweep_row(page, "mini2").locator(".ov-label")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
