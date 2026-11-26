"""Feature 007, user story 4: one colour per cohort everywhere, always with its name.

The colour lives on `.coh-mark` (background) and `.coh-tag` (left border); each sits inside
an element whose `data-cohort` names the cohort.
"""

from playwright.sync_api import expect

COLOURS = """() => {
  const out = {};
  for (const el of document.querySelectorAll(".coh-mark, .coh-tag")) {
    const host = el.closest("[data-cohort]");
    const key = host ? host.dataset.cohort : "(no cohort)";
    const cs = getComputedStyle(el);
    const colour = el.classList.contains("coh-tag") ? cs.borderLeftColor : cs.backgroundColor;
    (out[key] ||= []).push(colour);
  }
  return Object.fromEntries(Object.entries(out).map(([k, v]) => [k, [...new Set(v)]]));
}"""


def everywhere(mini):
    """Both cohorts chosen, a variable selected from each, topics and a row open, and the
    Selection view drawn once, so every place a cohort's colour appears is on the page."""
    mini.set_viewport_size({"width": 1400, "height": 1000})
    mini.locator('.cohorts button[data-cohort="mini2"]').click()
    expect(mini.locator("#results .v-group")).to_have_count(2)
    mini.locator("#tgrid-toggle").click()
    mini.get_by_role("button", name="Show the topics in Health").click()
    mini.get_by_label("Search variables").fill("smok")
    for key in ("mini:0:smoke5", "mini2:2:smok11"):
        mini.locator(f'#results .vrow[data-key="{key}"] .vrow-btn').click()
    mini.get_by_role("button", name="Show details for smok11").click()
    expect(mini.locator(".vm-cohort")).to_be_visible()
    mini.get_by_role("button", name="Selection").first.click()
    expect(mini.locator("#basket-detail .sel-coh")).to_have_count(2)
    mini.get_by_role("button", name="Variables").first.click()
    return mini


def colours(page):
    """Each cohort's distinct mark colours."""
    return page.evaluate(COLOURS)


def test_each_cohort_has_one_colour_everywhere_in_both_themes(mini):
    everywhere(mini)
    seen = {}
    for theme in ("light", "dark"):
        mini.evaluate(f"document.documentElement.dataset.theme = {theme!r}")
        found = colours(mini)
        assert "(no cohort)" not in found, found
        assert len(found["mini"]) == 1, found
        assert len(found["mini2"]) == 1, found
        assert found["mini"] != found["mini2"]
        seen[theme] = found
    assert seen["light"]["mini"] != seen["dark"]["mini"]


def test_every_place_names_the_cohort_its_colour_marks(mini):
    everywhere(mini)
    places = mini.evaluate(
        """() => [...document.querySelectorAll(".coh-mark, .coh-tag")].map((el) => {
          const host = el.closest("[data-cohort]");
          return host ? host.textContent.trim() : "";
        })"""
    )
    assert len(places) >= 10
    assert all(places), places


def test_a_cohort_mark_looks_unlike_a_topic_area_square(mini):
    everywhere(mini)
    size = """(sel) => { const r = document.querySelector(sel).getBoundingClientRect();
                         return [Math.round(r.width), Math.round(r.height)]; }"""
    mark = mini.evaluate(size, "#ov-about .coh-mark")
    square = mini.evaluate(size, "#tgrid-body .dom-swatch")
    assert square[0] == square[1], square
    assert mark[1] > mark[0] * 2, mark  # tall and thin, not square
