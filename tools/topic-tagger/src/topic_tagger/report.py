"""The run report: one self-contained HTML file with the run's statistics and charts.

It makes no requests and runs no scripts, so it opens offline and can be shared as a
file. It follows the reader's light or dark preference. Sections are listed in
docs/formats.md (``report.html``).
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from topic_tagger import svg
from topic_tagger.scheme import Scheme

CSS = """
:root {
  color-scheme: light;
  --surface: #fcfcfb; --surface-2: #f3f2ef; --border: #e4e3df; --grid: #d6d5d0;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #6f6e69;
  --text-on-strong: #ffffff; --series-1: #2a78d6;
  --seq-0: #f0efec; --seq-1: #cde2fb; --seq-2: #86b6ef;
  --seq-3: #2a78d6; --seq-4: #1c5cab; --seq-5: #104281;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --surface: #1a1a19; --surface-2: #232321; --border: #383835; --grid: #4a4a46;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #9a9890;
    --text-on-strong: #0b0b0b; --series-1: #3987e5;
    --seq-0: #2a2a28; --seq-1: #104281; --seq-2: #1c5cab;
    --seq-3: #3987e5; --seq-4: #6da7ec; --seq-5: #9ec5f4;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface); color: var(--text-primary);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 32px 16px 64px; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 40px 0 8px; }
h3 { font-size: 14px; margin: 20px 0 6px; color: var(--text-secondary); }
p, dd, li, td, th, summary { color: var(--text-secondary); }
.sub { color: var(--text-muted); margin: 0 0 16px; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 2px 16px; margin: 0; }
dt { color: var(--text-muted); }
dd { margin: 0; overflow-wrap: anywhere; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }
.tile { background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px; }
.tile .label { color: var(--text-secondary); font-size: 13px; }
.tile .value { font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; }
svg.chart { display: block; max-width: 100%; height: auto; margin: 8px 0; }
table { border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 2px 16px 2px 0; border-bottom: 1px solid var(--border); }
td.n, th.n { text-align: right; }
details { margin: 4px 0 8px; }
summary { cursor: pointer; font-size: 13px; }
ul.failed { columns: 2; padding-left: 18px; }
"""


def _hms(seconds: float) -> str:
    s = round(seconds)
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}"


def _seconds(run: dict) -> float:
    def parse(t: str) -> datetime:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))

    return (parse(run["ended"]) - parse(run["started"])).total_seconds()


def _table(head: list[str], rows: list[list], numeric_from: int = 1) -> str:
    def cells(row: list, tag: str) -> str:
        out = []
        for i, c in enumerate(row):
            cls = ' class="n"' if i >= numeric_from else ""
            out.append(f"<{tag}{cls}>{escape(str(c))}</{tag}>")
        return "".join(out)

    body = "".join(f"<tr>{cells(r, 'td')}</tr>" for r in rows)
    return f"<table><thead><tr>{cells(head, 'th')}</tr></thead><tbody>{body}</tbody></table>"


def _as_table(head: list[str], rows: list[list]) -> str:
    return f"<details><summary>Show as a table</summary>{_table(head, rows)}</details>"


def _section(id_: str, title: str, body: str) -> str:
    return f'<section id="{id_}"><h2>{escape(title)}</h2>{body}</section>'


def render_report(run: dict, stats: dict, scheme: Scheme) -> str:
    """Build the report.

    Args:
        run: The run, as saved in ``run.json`` (without ``stats``).
        stats: The run's statistics, from ``compute_stats``.
        scheme: The scheme the tags were made with.

    Returns:
        The whole HTML document.
    """
    settings = run.get("settings", {})
    domain_label = {d.id: d.label for d in scheme.domains}
    topic_label = {t.id: t.label for t in scheme.topics}
    tagged = sum(f["tagged"] for f in stats["per_file"].values())
    failed = run.get("failed", [])
    model = ":".join(str(settings[k]) for k in ("provider", "model") if settings.get(k))

    # 1. The run.
    facts = [
        ("Started", run["started"].replace("T", " ").replace("Z", " UTC")),
        ("Status", run.get("status", "")),
        ("Model", model),
        ("Scheme", f"{scheme.name}, version {scheme.version} (hash {scheme.hash})"),
    ]
    shown = ("batch_size", "workers", "timeout", "retries", "files", "limit", "retag")
    shown_as = {None: "all", True: "yes", False: "no"}
    facts += [
        (k.replace("_", " ").capitalize(), shown_as.get(settings[k], settings[k]))
        for k in shown
        if k in settings
    ]
    facts += [("Grouped by", stats["group_by"])]
    run_html = (
        "<dl>"
        + "".join(f"<dt>{escape(str(k))}</dt><dd>{escape(str(v))}</dd>" for k, v in facts)
        + "</dl>"
    )

    # 2. Summary tiles.
    tiles = [
        ("Variables tagged", tagged),
        ("Failed", len(failed)),
        ("Run time", _hms(_seconds(run))),
        ("Speed", f"{stats['speed']:g}/min"),
        ("Mean topics per variable", f"{stats['mean_topics']:.1f}"),
        ("Only below 50%", f"{stats['below_default']:.0%}"),
    ]
    tiles_html = (
        '<div class="tiles">'
        + "".join(
            f'<div class="tile"><div class="label">{escape(k)}</div>'
            f'<div class="value">{escape(str(v))}</div></div>'
            for k, v in tiles
        )
        + "</div>"
    )

    # 3. Topic areas.
    areas = sorted(stats["per_domain"].items(), key=lambda x: -x[1])
    area_items = [(domain_label[d], n) for d, n in areas]
    areas_html = (
        "<p>Variables with at least one topic in each area. A variable can be in several.</p>"
        + svg.bars(area_items, "Variables per topic area")
        + _as_table(["Topic area", "Variables"], [list(x) for x in area_items])
    )

    # 4. Topics within each area, and the unused ones.
    parts = []
    parts.append(
        "<p>Variables per topic, in each area that has any. Unused topics are listed below.</p>"
    )
    for d in scheme.domains:
        used = [(t.label, stats["per_topic"][t.id]) for t in d.topics if stats["per_topic"][t.id]]
        if not used:
            continue
        items = sorted(used, key=lambda x: -x[1])
        parts.append(
            f"<h3>{escape(d.label)}</h3>" + svg.bars(items, f"Variables per topic: {d.label}")
        )
    unused = [topic_label[t] for t in stats["unused"]]
    parts.append(
        f"<h3>Never used ({len(unused)} of {len(topic_label)})</h3>"
        + (f"<p>{escape(', '.join(unused))}</p>" if unused else "<p>None.</p>")
    )
    topics_html = "".join(parts)

    # 5. Confidence.
    bins = stats["confidence_histogram"]
    conf_html = (
        f"<p>Every tag's confidence. {stats['below_default']:.0%} of tagged variables have "
        "no tag at 50% or above, so the site hides them by default.</p>"
        + svg.histogram(bins, "Tags by confidence")
        + _as_table(
            ["Confidence", "Tags"],
            [[f"{i / 10:.1f}–{(i + 1) / 10:.1f}", c] for i, c in enumerate(bins)],
        )
    )

    # 6. Topic areas by the grouping field.
    groups = stats["domain_by_group"]
    groups_html = ""
    if groups:
        cols = list(groups)
        rows = [d.id for d in scheme.domains]
        values = [[groups[g][d] for g in cols] for d in rows]
        groups_html = (
            f"<p>Variables per topic area, for each value of <code>{escape(stats['group_by'])}"
            "</code>.</p>"
            + svg.heat_grid([domain_label[d] for d in rows], cols, values, "Topic areas by group")
            + _as_table(
                ["Topic area", *cols],
                [[domain_label[d], *v] for d, v in zip(rows, values, strict=True)],
            )
        )

    # 7. Speed over the run.
    timeline = run.get("timeline", [])
    step = timeline[1][0] - timeline[0][0] if len(timeline) > 1 else 10
    # Each step's speed is held from its start to its end, so the line starts at 0:00.
    points = [(t, n * 60 / step) for t, n in timeline]
    if points:
        points.append((points[-1][0] + step, points[-1][1]))
    speed_html = (
        f"<p>Variables per minute, in steps of {step} seconds. Mean {stats['speed']:g}/min.</p>"
        + svg.line(points, "Variables per minute over the run")
    )

    # 8. Files and failures.
    file_rows = [[f, c["tagged"], c["failed"]] for f, c in stats["per_file"].items()]
    failed_html = (
        '<ul class="failed">' + "".join(f"<li>{escape(k)}</li>" for k in failed) + "</ul>"
        if failed
        else "<p>None.</p>"
    )
    files_html = (
        _table(["Data file", "Tagged", "Failed"], file_rows)
        + f"<h3>Could not be tagged ({len(failed)})</h3>"
        + failed_html
    )

    sections = [
        _section("run", "Run", run_html),
        _section("summary", "Summary", tiles_html),
        _section("areas", "Topic areas", areas_html),
        _section("topics", "Topics", topics_html),
        _section("confidence", "Confidence", conf_html),
        _section("groups", f"Topic areas by {stats['group_by']}", groups_html) if groups else "",
        _section("speed", "Speed", speed_html),
        _section("files", "Data files", files_html),
    ]
    title = f"Topic tagging report: {scheme.name}, {run['started'][:10]}"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{CSS}</style></head><body><main>"
        f'<h1>Topic tagging report</h1><p class="sub">{escape(scheme.name)} · '
        f"{escape(model)} · {escape(run['started'][:10])}</p>"
        + "".join(sections)
        + "</main></body></html>\n"
    )
