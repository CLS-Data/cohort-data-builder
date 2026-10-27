import datetime
import re
import zipfile

import pytest
from playwright.sync_api import expect


@pytest.fixture
def mini(page, serve, mini_site):
    page.goto(serve(mini_site))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    return page


def pick(page, name, nth=0):
    page.locator("#results .vrow").filter(
        has=page.locator(".v-name", has_text=re.compile(f"^{name}$"))
    ).nth(nth).locator(".vrow-btn").click()


def review(page):
    page.get_by_role("button", name=re.compile("^Selection")).click()
    return page.locator("#basket-detail")


def column(page, name):
    return page.get_by_label(f"Output column name for {name}", exact=True)


def download_button(page):
    return page.locator("#basket-download")


def test_review_lists_identifier_then_columns_and_files_needed(mini):
    for name in ("smoke5", "alc10"):
        pick(mini, name)
    detail = review(mini)
    rows = detail.locator(".cols .col-row")
    expect(rows).to_have_count(3)
    expect(rows.nth(0)).to_contain_text("PID")
    expect(rows.nth(0)).to_contain_text("always included")
    expect(rows.nth(1)).to_contain_text("Does the mother smoke")
    expect(rows.nth(1)).to_contain_text("mini_age5")
    expect(column(mini, "smoke5")).to_have_value("smoke5")
    files = detail.locator(".linklist li")
    expect(files).to_have_count(2)
    expect(files.nth(0)).to_contain_text("Age 5 interview")
    expect(detail.get_by_role("link", name="UK Data Service")).to_have_attribute(
        "href", "https://example.org/mini"
    )


def test_clashing_names_get_the_sweep(mini):
    pick(mini, "sex")
    pick(mini, "sex", nth=1)
    review(mini)
    inputs = mini.locator("#basket-detail .col-input")
    expect(inputs.nth(0)).to_have_value("sex")
    expect(inputs.nth(1)).to_have_value("sex_10y")


def test_rename_on_enter_and_blur_and_problems_block_download(mini):
    pick(mini, "smoke5")
    pick(mini, "tenure5")
    review(mini)
    smoke = column(mini, "smoke5")
    smoke.fill("smoking")
    smoke.press("Enter")
    expect(column(mini, "smoke5")).to_have_value("smoking")
    column(mini, "tenure5").fill("1bad")
    column(mini, "smoke5").focus()  # blur commits
    bad = column(mini, "tenure5")
    expect(bad).to_have_attribute("aria-invalid", "true")
    expect(mini.locator("#basket-detail .col-problem")).to_contain_text("Must start with a letter")
    expect(download_button(mini)).to_be_disabled()

    bad.fill("SMOKING")
    bad.press("Enter")
    expect(mini.locator("#basket-detail .col-problem")).to_have_count(2)
    expect(mini.locator("#basket-detail .col-problem").first).to_contain_text(
        "Two columns would both be called"
    )
    column(mini, "tenure5").fill("pid")
    column(mini, "tenure5").press("Enter")
    expect(mini.locator("#basket-detail .col-problem")).to_contain_text("the identifier's name")
    column(mini, "tenure5").fill("tenure")
    column(mini, "tenure5").press("Enter")
    expect(download_button(mini)).to_be_enabled()


def test_stata_offers_to_replace_dots(mini):
    pick(mini, "smoke5")
    review(mini)
    column(mini, "smoke5").fill("smoke.at.5")
    column(mini, "smoke5").press("Enter")
    expect(download_button(mini)).to_be_enabled()
    mini.get_by_label("Stata (.dta)").check()
    expect(download_button(mini)).to_be_disabled()
    mini.get_by_role("button", name="Replace every . with _").click()
    expect(column(mini, "smoke5")).to_have_value("smoke_at_5")
    expect(download_button(mini)).to_be_enabled()


def test_options_persist_and_no_language_disables_download(mini):
    pick(mini, "smoke5")
    review(mini)
    mini.get_by_label("R", exact=True).uncheck()
    mini.get_by_label("SPSS (.sav)").check()
    mini.get_by_label("Convert to NA").check()
    mini.reload()
    expect(mini.locator("#result-count")).to_have_text("16 variables")
    review(mini)
    expect(mini.get_by_label("R", exact=True)).not_to_be_checked()
    expect(mini.get_by_label("Python", exact=True)).to_be_checked()
    expect(mini.get_by_label("SPSS (.sav)")).to_be_checked()
    expect(mini.get_by_label("Convert to NA")).to_be_checked()
    mini.get_by_label("Python", exact=True).uncheck()
    expect(download_button(mini)).to_be_disabled()


def test_download_produces_the_project_zip(mini, tmp_path):
    for name in ("smoke5", "quote5", "hhrel"):
        pick(mini, name)
    review(mini)
    with mini.expect_download() as info:
        download_button(mini).click()
    download = info.value
    today = datetime.date.today().isoformat()
    project = f"mini-merge-{today}"
    assert download.suggested_filename == f"{project}.zip"
    path = tmp_path / download.suggested_filename
    download.save_as(path)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names = sorted(n[len(project) + 1 :] for n in z.namelist())
        merge = z.read(f"{project}/R/merge.R").decode()
    assert names == sorted(
        [
            "README.md",
            "codebook.csv",
            "data/README.md",
            f"{project}.Rproj",
            "R/load_data.R",
            "R/merge.R",
            "python/load_data.py",
            "python/merge.py",
            "python/requirements.txt",
        ]
    )
    assert '"quote5" = "quote5"' in merge
    expect(mini.locator("#basket-status")).to_contain_text(re.compile(r"\d+ KB"))


def test_data_file_link_filters_the_variables_view(mini):
    pick(mini, "hhrel")
    detail = review(mini)
    detail.locator(".linklist button").first.click()
    expect(mini.locator("#result-count")).to_have_text("2 variables")
    expect(mini.locator("#active-filters .chip")).to_contain_text("mini_grid")


def test_selection_list_removes_and_divider_resizes(mini):
    pick(mini, "smoke5")
    pick(mini, "alc10")
    review(mini)
    mini.get_by_role("button", name="Remove smoke5").first.click()
    expect(mini.locator("#basket-list li")).to_have_count(1)
    grip = mini.get_by_role("separator", name="Resize the list")
    before = int(grip.get_attribute("aria-valuenow") or 0)
    grip.focus()
    grip.press("ArrowRight")
    after = int(grip.get_attribute("aria-valuenow"))
    assert after > before
    mini.reload()
    expect(mini.locator("#result-count")).to_have_text("16 variables")
    review(mini)
    assert int(mini.get_by_role("separator").get_attribute("aria-valuenow")) == after
