"""Feature 007, user story 3: one selection across cohorts, downloaded together.

See contracts/variables-view.md ("Selected panel and Selection view") and
contracts/multi-cohort-download.md.
"""

import io
import json
import re
import zipfile

from playwright.sync_api import expect


def coh(page, key):
    """The header's toggle button for a cohort."""
    return page.locator(f'.cohorts button[data-cohort="{key}"]')


def pick(page, key):
    """Select a listed variable by its list key, `<cohort>:<fileIndex>:<name>`."""
    page.locator(f'#results .vrow[data-key="{key}"] .vrow-btn').click()


def two_from_each(mini):
    """Choose mini2 too, and select two variables from each cohort."""
    coh(mini, "mini2").click()
    expect(mini.locator("#results .v-group")).to_have_count(2)
    for key in ("mini:0:smoke5", "mini:1:alc10", "mini2:0:play3", "mini2:2:smok11"):
        pick(mini, key)
    return mini


def review(page):
    """Open the Selection view."""
    page.get_by_role("button", name="Selection").first.click()
    expect(page.locator("#basket-detail")).to_be_visible()


def cohort_heads(page, scope):
    """The cohort headings in the panel (`#sp-list`) or the view (`#basket-detail`)."""
    return page.locator(f"{scope} .sel-coh-head")


# T036 ─ grouped by cohort


def test_the_panel_groups_the_selection_by_cohort(mini):
    two_from_each(mini)
    heads = cohort_heads(mini, "#sp-list")
    expect(heads).to_have_count(2)
    expect(heads.nth(0)).to_contain_text("Mini (2)")
    expect(heads.nth(1)).to_contain_text("Mini2 (2)")
    expect(mini.locator("#sp-list .sp-grp-name").first).to_have_text("5y")


def test_the_selection_view_groups_by_cohort_and_counts_the_download(mini):
    two_from_each(mini)
    review(mini)
    heads = cohort_heads(mini, "#basket-detail")
    expect(heads).to_have_count(2)
    expect(heads.nth(0)).to_contain_text("Mini (2)")
    expect(heads.nth(1)).to_contain_text("Mini2 (2)")
    expect(mini.locator("#basket-download")).to_have_text("Download 4 variables from 2 cohorts")


def test_columns_are_checked_within_each_cohort(mini):
    two_from_each(mini)
    review(mini)
    box = mini.get_by_label("Output column name for play3", exact=True)
    box.fill("smoke5")  # mini's column name: no clash across cohorts
    box.press("Enter")
    expect(mini.locator("#basket-detail .col-problem")).to_have_count(0)
    box = mini.get_by_label("Output column name for play3", exact=True)
    box.fill("CID")  # mini2's own identifier: a clash
    box.press("Enter")
    expect(mini.locator("#basket-detail .col-problem")).to_contain_text("identifier")


def test_a_cohort_no_longer_searched_keeps_its_selection(mini):
    two_from_each(mini)
    coh(mini, "mini2").click()
    head = cohort_heads(mini, "#sp-list").nth(1)
    expect(head).to_contain_text("Mini2 (2)")
    expect(head).to_contain_text("not being searched")
    review(mini)
    expect(mini.locator("#basket-download")).to_have_text("Download 4 variables from 2 cohorts")


# T037 ─ restored from storage; the bundle download


def test_saved_selections_of_unchosen_cohorts_come_back(page, serve, mini_site):
    url = serve(mini_site)
    page.goto(url + "#mini")
    saved = {
        "mini": [
            {"name": "smoke5", "label": "", "file": "mini_age5", "wave": "5y", "column": "smoke5"}
        ],
        "mini2": [
            {"name": "play3", "label": "", "file": "mini2_age3", "wave": "3y", "column": "play3"},
            {"name": "gone", "label": "", "file": "mini2_age3", "wave": "3y", "column": "gone"},
        ],
    }
    for key, value in saved.items():
        page.evaluate(
            "([k, v]) => localStorage.setItem(k, v)",
            [f"cohort-data-builder:{key}:selection", json.dumps(value)],
        )
    page.reload()  # the same address again would not reload the page
    heads = cohort_heads(page, "#sp-list")
    expect(heads).to_have_count(2)
    expect(heads.nth(1)).to_contain_text("Mini2 (1)")  # "gone" is not in mini2's index
    expect(coh(page, "mini2")).to_have_attribute("aria-pressed", "false")


def test_the_download_is_one_zip_with_a_folder_per_cohort(mini):
    two_from_each(mini)
    review(mini)
    with mini.expect_download() as info:
        mini.locator("#basket-download").click()
    download = info.value
    name = download.suggested_filename
    assert re.fullmatch(r"cohorts-merge-\d{4}-\d{2}-\d{2}\.zip", name), name
    date = name[len("cohorts-merge-") : -len(".zip")]
    root = f"cohorts-merge-{date}/"
    with zipfile.ZipFile(io.BytesIO(open(download.path(), "rb").read())) as z:
        names = z.namelist()
        readme = z.read(f"{root}README.md").decode()
    assert names[0] == f"{root}README.md"
    assert f"{root}mini-merge-{date}/README.md" in names
    assert f"{root}mini2-merge-{date}/README.md" in names
    tops = [n[len(root) :].split("/")[0] for n in names if n != f"{root}README.md"]
    assert list(dict.fromkeys(tops)) == [f"mini-merge-{date}", f"mini2-merge-{date}"]
    assert "4 variables from 2 cohorts" in readme


def test_one_cohort_downloads_exactly_as_before(mini):
    pick(mini, "mini:0:smoke5")
    review(mini)
    expect(mini.locator("#basket-download")).to_have_text("Download R + Python code")
    with mini.expect_download() as info:
        mini.locator("#basket-download").click()
    assert info.value.suggested_filename.startswith("mini-merge-")
