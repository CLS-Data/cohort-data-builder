"""Speed on the largest cohort (BCS70, 32,452 variables) over a throttled connection.

SC-007: the first view is usable within 3 s on typical broadband (about 20 Mbps, 20 ms).
SC-002: results update within 0.5 s of typing. The local server sends JSON uncompressed,
so this is harder than GitHub Pages, which compresses the index about six-fold.
"""

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
    expect(page.locator("#result-count")).to_have_text("32,452 variables", timeout=10_000)
    loaded = time.perf_counter() - start
    assert loaded < 3, f"first view took {loaded:.2f} s"

    page.get_by_label("Search variables").fill("smok")
    start = time.perf_counter()
    expect(page.locator("#result-count")).not_to_have_text("32,452 variables", timeout=5_000)
    answered = time.perf_counter() - start
    assert answered < 0.5, f"search took {answered:.2f} s"
