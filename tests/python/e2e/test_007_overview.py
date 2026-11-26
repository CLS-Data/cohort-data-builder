"""Feature 007, user story 2: the overview with several cohorts is one row of bars on a
shared age axis, each bar stacked by cohort; the topic rows likewise.

Fixture sweeps: mini 5y, 10y, xwave; mini2 3y, w2 (age 7), 11y, extra; so with both the
axis reads 3, 5, 7, 10, 11, ? (xwave and extra share "?"). See contracts/variables-view.md
("Overview").
"""

from playwright.sync_api import expect


def coh(page, key):
    """The header's toggle button for a cohort."""
    return page.locator(f'.cohorts button[data-cohort="{key}"]')


def bar(page, col):
    """The overview's bar for an axis column."""
    return page.locator(f'#spine-track li[data-col="{col}"] button.node')


def segments(locator):
    """The cohorts stacked in a bar or cell, bottom first."""
    segs = locator.locator(".coh-seg")
    return [segs.nth(i).get_attribute("data-cohort") for i in range(segs.count())]


def cell(page, topic, col):
    """A topic ("t:<id>") or domain ("d:<id>") row's cell for an axis column."""
    return page.locator(f'#tgrid-body .tg-row[data-id="{topic}"] .tg-cell[data-col="{col}"]')


def both(mini):
    """Choose mini2 as well as mini."""
    coh(mini, "mini2").click()
    expect(bar(mini, 0)).to_be_visible()
    return mini


def open_health(page):
    """Open the topic rows and the health domain."""
    page.locator("#tgrid-toggle").click()
    page.locator('#tgrid-body [data-expand="health"]').click()


# One cohort: as before


def test_one_cohort_keeps_todays_overview(mini):
    expect(mini.locator("#spine-track li")).to_have_count(3)
    expect(mini.locator("#spine-track .node-age")).to_have_text(["5y", "10y", "xwave"])
    expect(mini.locator("#spine-track .coh-seg")).to_have_count(0)


def test_no_description_text_under_the_header(mini):
    expect(mini.locator("#ov-about")).to_be_hidden()
    both(mini)
    expect(mini.locator("#ov-about")).to_be_hidden()


# Several: one row, stacked


def test_two_cohorts_share_one_row_of_bars_on_an_age_axis(mini):
    both(mini)
    expect(mini.locator("#spine-track li")).to_have_count(6)
    expect(mini.locator("#spine-track .node-age")).to_have_text(["3", "5", "7", "10", "11", "?"])
    expect(mini.locator("#spine-rows .ov-row")).to_have_count(0)
    expect(mini.locator("#spine-note")).to_have_text("28")
    assert segments(bar(mini, 0)) == ["mini2"]
    assert segments(bar(mini, 1)) == ["mini"]
    assert segments(bar(mini, 5)) == ["mini", "mini2"]  # catalogue order, bottom first


def test_segments_are_in_proportion_and_in_each_cohorts_colour(mini):
    both(mini)
    expect(bar(mini, 5).locator(".coh-seg")).to_have_count(2)
    heights = (
        bar(mini, 5)
        .locator(".coh-seg")
        .evaluate_all(
            "els => els.map(e => [e.getBoundingClientRect().height,"
            " getComputedStyle(e).backgroundColor])"
        )
    )
    title = bar(mini, 5).get_attribute("title")
    assert "Mini" in title and "Mini2" in title
    (h1, c1), (h2, c2) = heights
    assert h1 > 0 and h2 > 0
    assert c1 != c2


def test_a_bar_says_each_cohorts_count(mini):
    both(mini)
    expect(bar(mini, 2)).to_have_attribute("title", "Age 7 — 3 variables: Mini2 3 (w2)")


def test_a_bar_filters_every_cohort_to_that_age(mini):
    both(mini)
    bar(mini, 2).click()
    expect(mini.locator("#active-filters")).to_contain_text("age 7")
    expect(mini.locator("#result-count")).to_contain_text("3 variables")
    expect(bar(mini, 2)).to_have_attribute("aria-pressed", "true")
    bar(mini, 5).click()  # "?" holds a sweep of each
    expect(mini.locator("#active-filters")).to_contain_text("age not known")
    expect(mini.locator('#result-count [data-goto="mini"]')).to_be_visible()
    expect(mini.locator('#result-count [data-goto="mini2"]')).to_be_visible()
    bar(mini, 5).click()
    expect(mini.locator("#result-count")).to_contain_text("28 variables")


def test_a_cohort_with_no_matches_is_simply_absent_from_the_bars(mini):
    both(mini)
    mini.get_by_label("Search variables").fill("smok")
    expect(mini.locator("#spine-note")).to_have_text("2")
    assert segments(bar(mini, 1)) == ["mini"]
    assert segments(bar(mini, 4)) == ["mini2"]


# Topic rows: one row each, cells stacked


def test_topic_rows_are_one_row_with_stacked_cells(mini):
    both(mini)
    open_health(mini)
    expect(mini.locator("#tgrid-body .tg-sub")).to_have_count(0)
    expect(mini.locator('#tgrid-body .tg-row[data-id="t:smoking"] .tg-cell')).to_have_count(6)
    expect(cell(mini, "t:smoking", 4)).to_have_attribute(
        "aria-label", "Smoking at age 11: 1 (Mini2 1)"
    )
    assert segments(cell(mini, "t:smoking", 1)) == ["mini"]
    assert segments(cell(mini, "t:vaping", 1)) == []


def test_an_untagged_cohort_is_named_above_the_topic_rows(mini):
    both(mini)
    coh(mini, "mini3").click()
    expect(bar(mini, 0)).to_be_visible()
    open_health(mini)
    expect(mini.locator("#tgrid-body")).to_contain_text("Mini3 has no topic tags")


def test_a_cell_filters_to_that_topic_at_that_age(mini):
    both(mini)
    open_health(mini)
    cell(mini, "t:smoking", 1).click()
    chips = mini.locator("#active-filters")
    expect(chips).to_contain_text("age 5")
    expect(chips).to_contain_text("Smoking")
    expect(mini.locator('#results .vrow[data-key="mini:0:smoke5"]')).to_be_visible()


def test_the_chart_fits_a_phone(page, serve, mini_site):
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(serve(mini_site) + "#mini+mini2")
    expect(bar(page, 0)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
