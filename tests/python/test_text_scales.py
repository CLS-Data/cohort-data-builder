"""Text follows the reader's browser settings: no pixel font sizes, and zoom never blocked (US5)."""

import re
from pathlib import Path

SITE = Path(__file__).resolve().parents[2] / "site"
STYLES = [SITE / "styles.css", SITE / "tutorial" / "tutorial.css"]
PAGES = [SITE / "index.html", SITE / "tutorial" / "index.html"]


def test_font_sizes_are_relative_so_browser_text_size_applies():
    for path in STYLES:
        found = re.findall(r"(?:font-size|line-height):\s*[\d.]+px", path.read_text())
        assert found == [], f"{path.name}: {found[:5]}"


def test_pages_never_stop_the_reader_zooming():
    for path in PAGES:
        meta = re.search(r'<meta name="viewport" content="([^"]+)"', path.read_text()).group(1)
        assert "user-scalable" not in meta and "maximum-scale" not in meta, path
