"""Small SVG charts for the report: bars, a histogram, a heat grid and a line.

Each returns an ``<svg>`` string with a ``<title>``, a ``<title>`` tooltip on every mark
(the report has no scripts) and the values as text. Colours come only from CSS variables
the report defines for light and dark: ``--series-1`` for marks, ``--seq-0`` to ``--seq-5``
for the grid, and ``--text-*`` and ``--grid`` for text and axes.
"""

from __future__ import annotations

from html import escape

ROW = 24  # height of a bar's band
THICK = 16  # bar thickness; the rest of the band is air
RADIUS = 4  # rounded data end
LABEL_W = 220  # room for category labels
PLOT_W = 360
FONT = 'font-family="inherit" font-size="12"'


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def _svg(width: int, height: int, title: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" role="img" class="chart"><title>{escape(title)}</title>{body}</svg>'
    )


def _no_data(title: str) -> str:
    text = f'<text x="8" y="24" {FONT} fill="var(--text-muted)">No data</text>'
    return _svg(LABEL_W + PLOT_W, 40, title, text)


def _text(x: float, y: float, s: str, *, anchor: str = "start", role: str = "secondary") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" {FONT} text-anchor="{anchor}" '
        f'fill="var(--text-{role})">{escape(s)}</text>'
    )


def _clip(s: str, n: int = 32) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _hbar(x: float, y: float, w: float, h: float, tip: str) -> str:
    """A horizontal bar, square at the baseline and rounded at its data end."""
    r = min(RADIUS, w, h / 2)
    d = (
        f"M{x:.1f},{y:.1f} h{w - r:.1f} a{r},{r} 0 0 1 {r},{r} v{h - 2 * r:.1f} "
        f"a{r},{r} 0 0 1 {-r},{r} h{-(w - r):.1f} z"
    )
    return f'<path class="mark" d="{d}" fill="var(--series-1)"><title>{escape(tip)}</title></path>'


def _vbar(x: float, base: float, w: float, h: float, tip: str) -> str:
    """A column, square at the baseline and rounded at its top."""
    r = min(RADIUS, h, w / 2)
    d = (
        f"M{x:.1f},{base:.1f} v{-(h - r):.1f} a{r},{r} 0 0 1 {r},{-r} h{w - 2 * r:.1f} "
        f"a{r},{r} 0 0 1 {r},{r} v{h - r:.1f} z"
    )
    return f'<path class="mark" d="{d}" fill="var(--series-1)"><title>{escape(tip)}</title></path>'


def bars(items: list[tuple[str, float]], title: str) -> str:
    """Horizontal bars, one per item, longest scale first as given.

    Args:
        items: ``(label, value)`` pairs, in the order to draw them.
        title: The chart's accessible title.

    Returns:
        The SVG.
    """
    if not items:
        return _no_data(title)
    top = max(v for _, v in items) or 1
    body = []
    for i, (label, v) in enumerate(items):
        y = i * ROW
        mid = y + ROW / 2 + 4
        body.append(_text(LABEL_W - 8, mid, _clip(label), anchor="end"))
        w = PLOT_W * v / top
        if w > 0:
            body.append(_hbar(LABEL_W, y + (ROW - THICK) / 2, w, THICK, f"{label}: {_num(v)}"))
        else:
            # A zero still gets a (hidden) mark so every item has its tooltip.
            body.append(
                f'<path class="mark" d="M{LABEL_W},{y} h0" fill="var(--series-1)">'
                f"<title>{escape(label)}: 0</title></path>"
            )
        body.append(_text(LABEL_W + w + 6, mid, _num(v), role="primary"))
    width = LABEL_W + PLOT_W + 48
    return _svg(width, len(items) * ROW, title, "".join(body))


def histogram(bins: list[int], title: str) -> str:
    """Columns for the 10 confidence bins, [0, 0.1) to [0.9, 1.0].

    Args:
        bins: The count in each bin.
        title: The chart's accessible title.

    Returns:
        The SVG.
    """
    if not any(bins):
        return _no_data(title)
    n = len(bins)
    slot, col, height, base = 44, 24, 160, 180
    top = max(bins)
    body = [f'<line x1="0" x2="{n * slot}" y1="{base}" y2="{base}" stroke="var(--grid)"/>']
    for i, c in enumerate(bins):
        x = i * slot + (slot - col) / 2
        lo, hi = i / n, (i + 1) / n
        tip = f"{lo:.1f}–{hi:.1f}: {c}"
        h = height * c / top
        if h > 0:
            body.append(_vbar(x, base, col, h, tip))
        else:
            body.append(
                f'<path class="mark" d="M{x:.1f},{base} h0" fill="var(--series-1)">'
                f"<title>{escape(tip)}</title></path>"
            )
        body.append(_text(x + col / 2, base - h - 6, str(c), anchor="middle", role="primary"))
        body.append(_text(x + col / 2, base + 16, f"{lo:.1f}", anchor="middle"))
    return _svg(n * slot, base + 24, title, "".join(body))


def heat_grid(rows: list[str], cols: list[str], values: list[list[int]], title: str) -> str:
    """A grid of counts, darker for more, with each count written in its cell.

    Args:
        rows: Row labels.
        cols: Column labels.
        values: ``values[row][col]``.
        title: The chart's accessible title.

    Returns:
        The SVG.
    """
    if not rows or not cols:
        return _no_data(title)
    cell_w, cell_h, gap, head = 56, ROW, 2, 24
    top = max(max(r) for r in values) or 1
    body = [
        _text(LABEL_W + j * cell_w + cell_w / 2, 16, _clip(c, 8), anchor="middle")
        for j, c in enumerate(cols)
    ]
    for i, label in enumerate(rows):
        y = head + i * cell_h
        body.append(_text(LABEL_W - 8, y + cell_h / 2 + 4, _clip(label), anchor="end"))
        for j, v in enumerate(values[i]):
            step = 0 if v == 0 else 1 + round(4 * v / top)
            x = LABEL_W + j * cell_w
            tip = f"{label}, {cols[j]}: {v}"
            body.append(
                f'<rect class="mark" x="{x + gap / 2}" y="{y + gap / 2}" width="{cell_w - gap}" '
                f'height="{cell_h - gap}" rx="2" fill="var(--seq-{step})">'
                f"<title>{escape(tip)}</title></rect>"
            )
            ink = "on-strong" if step >= 3 else "primary"
            body.append(
                _text(x + cell_w / 2, y + cell_h / 2 + 4, str(v), anchor="middle", role=ink)
            )
    return _svg(LABEL_W + len(cols) * cell_w, head + len(rows) * cell_h, title, "".join(body))


def _clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}" if s < 3600 else f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}"


def line(points: list[tuple[float, float]], title: str) -> str:
    """A line over time, labelled with its last value.

    Args:
        points: ``(seconds, value)`` pairs, in time order.
        title: The chart's accessible title.

    Returns:
        The SVG.
    """
    if not points:
        return _no_data(title)
    width, height, left, base = LABEL_W + PLOT_W, 160, 8, 140
    plot_w = width - left - 48
    t_end = points[-1][0] or 1
    top = max(v for _, v in points) or 1

    def xy(t: float, v: float) -> tuple[float, float]:
        return left + plot_w * t / t_end, base - (base - 16) * v / top

    path = " ".join(
        f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}"
        for i, (x, y) in enumerate(xy(t, v) for t, v in points)
    )
    last_x, last_y = xy(*points[-1])
    peak = max(points, key=lambda p: p[1])
    tip = f"Peak {_num(peak[1])} at {_clock(peak[0])}; last {_num(points[-1][1])}"
    body = [
        f'<line x1="{left}" x2="{left + plot_w}" y1="{base}" y2="{base}" stroke="var(--grid)"/>',
        f'<path class="mark" d="{path}" fill="none" stroke="var(--series-1)" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"><title>{escape(tip)}</title></path>',
        _text(last_x + 6, last_y + 4, _num(points[-1][1]), role="primary"),
        _text(left, base + 16, "0:00"),
        _text(left + plot_w, base + 16, _clock(t_end), anchor="end"),
    ]
    return _svg(width, height, title, "".join(body))
