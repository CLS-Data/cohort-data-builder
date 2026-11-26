"""Speed on the largest cohort (BCS70, 37,562 variables) over a throttled connection.

SC-007: the first view is usable within 3 s on typical broadband (about 20 Mbps, 20 ms).
SC-002: results update within 0.5 s of typing. The local server sends JSON uncompressed,
so this is harder than GitHub Pages, which compresses the index about six-fold.
"""

import json
import re
import time
from pathlib import Path

from playwright.sync_api import expect

SITE = Path(__file__).resolve().parents[3] / "site"
MBPS = 20


def throttle(page):
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send(
        "Network.emulateNetworkConditions",
        {
            "offline": False,
            "latency": 20,
            "downloadThroughput": MBPS * 1_000_000 / 8,
            "uploadThroughput": MBPS * 1_000_000 / 8,
        },
    )


def test_bcs70_is_usable_within_3s_and_search_answers_within_half_a_second(page, serve):
    url = serve(SITE) + "#bcs70"
    throttle(page)
    start = time.perf_counter()
    page.goto(url)
    expect(page.locator("#result-count")).to_have_text("37,562 variables", timeout=10_000)
    loaded = time.perf_counter() - start
    assert loaded < 3, f"first view took {loaded:.2f} s"

    start = time.perf_counter()
    page.get_by_label("Search variables").fill("smok")
    expect(page.locator("#result-count")).not_to_have_text("37,562 variables", timeout=5_000)
    answered = time.perf_counter() - start
    assert answered < 0.5, f"search took {answered:.2f} s"


def ready(page, key):
    """A cohort's count in the result count, shown once its variables are searched. (Its
    group heading may be below the rows drawn so far.)"""
    return page.locator(f'#result-count [data-goto="{key}"]')


def test_every_cohort_together_searches_within_1s_and_each_added_one_within_3s(page, serve):
    """SC-002, SC-003 (feature 007): every real cohort chosen, about 115,000 variables."""
    url = serve(SITE)
    keys = [d["key"] for d in json.loads((SITE / "data/datasets.json").read_text())["datasets"]]
    page.goto(url + "#" + keys[0])
    expect(page.locator("#result-count")).to_have_text(re.compile("variables$"), timeout=10_000)
    for key in keys[1:]:
        start = time.perf_counter()
        page.locator(f'.cohorts button[data-cohort="{key}"]').click()
        expect(ready(page, key)).to_be_visible(timeout=10_000)
        added = time.perf_counter() - start
        assert added < 3, f"adding {key} took {added:.2f} s"

    before = page.locator("#result-count").inner_text()
    start = time.perf_counter()
    page.get_by_label("Search variables").fill("smok")
    expect(page.locator("#result-count")).not_to_have_text(before, timeout=5_000)
    answered = time.perf_counter() - start
    assert answered < 1, f"search across {len(keys)} cohorts took {answered:.2f} s"
