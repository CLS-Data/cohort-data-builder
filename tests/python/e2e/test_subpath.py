"""The site works from a project subpath, as GitHub Pages serves it, and holds no study data."""

import re
from pathlib import Path

from playwright.sync_api import expect

SITE = Path(__file__).resolve().parents[3] / "site"
PREFIX = "/cohort-data-builder/"

# A root-relative URL ("/x") in markup, a fetch or a stylesheet; "//host" is allowed.
ABSOLUTE = re.compile(
    r"""(?:href|src|action)\s*=\s*["']/(?!/)"""
    r"""|fetch\(\s*["'`]/(?!/)"""
    r"""|url\(\s*["']?/(?!/)"""
)


def test_the_site_works_under_a_subpath(page, serve, mini_site):
    failed = []
    page.on("requestfailed", lambda r: failed.append(r.url))
    page.on("response", lambda r: r.status >= 400 and failed.append(f"{r.status} {r.url}"))
    page.goto(serve(mini_site, prefix=PREFIX))
    expect(page.locator("#result-count")).to_have_text("16 variables")
    page.get_by_label("Search variables").fill("smoke")
    expect(page.locator("#result-count")).to_have_text("1 variable")
    page.get_by_role("button", name="Show details for smoke5").click()
    expect(page.locator(".vm-meta")).to_be_visible()
    page.locator("#results .vrow-btn").first.click()
    page.get_by_role("button", name="Selection").first.click()
    with page.expect_download() as info:
        page.locator("#basket-download").click()
    assert info.value.suggested_filename.startswith("mini-merge-")
    assert failed == []


def test_no_file_uses_a_root_relative_url():
    found = []
    for path in SITE.rglob("*"):
        if path.suffix not in (".html", ".css", ".js") or "data" in path.relative_to(SITE).parts:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if ABSOLUTE.search(line):
                found.append(f"{path.relative_to(SITE)}:{n}: {line.strip()}")
    assert found == []


def test_the_site_holds_no_data_files():
    data_files = [
        str(p.relative_to(SITE))
        for p in SITE.rglob("*")
        if p.suffix.lower() in (".tab", ".dta", ".sav", ".csv")
    ]
    assert data_files == []
