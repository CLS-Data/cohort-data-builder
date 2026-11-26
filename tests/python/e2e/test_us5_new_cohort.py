import json
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def site_plus_mini(site_with_data, tmp_path):
    """The real cohorts plus the fixture cohort, added the way a maintainer would: its folder
    and one entry in datasets.json, nothing outside data/."""
    data = tmp_path / "data"
    shutil.copytree(ROOT / "site" / "data", data)
    shutil.copytree(ROOT / "tests" / "fixtures" / "data" / "mini", data / "mini")
    catalogue = json.loads((data / "datasets.json").read_text(encoding="utf-8"))
    mini = json.loads((ROOT / "tests" / "fixtures" / "data" / "datasets.json").read_text())
    catalogue["datasets"].append(mini["datasets"][0])
    (data / "datasets.json").write_text(json.dumps(catalogue), encoding="utf-8")
    return site_with_data(data)


def test_an_added_cohort_appears_and_is_searchable(page, serve, site_plus_mini):
    page.goto(serve(site_plus_mini))
    picker = page.get_by_role("group", name="Cohorts")
    expect(picker.get_by_role("button")).to_have_text(
        ["NCDS", "BCS70", "Next Steps", "MCS", "Mini"]
    )
    first = picker.get_by_role("button").first.get_attribute("data-cohort")
    picker.locator('button[data-cohort="mini"]').click()
    picker.locator(f'button[data-cohort="{first}"]').click()
    expect(page.locator("#result-count")).to_have_text("16 variables")
    expect(page).to_have_url(page.url.split("#")[0] + "#mini")
    page.get_by_label("Search variables").fill("tenure")
    expect(page.locator("#result-count")).to_have_text("2 variables")
