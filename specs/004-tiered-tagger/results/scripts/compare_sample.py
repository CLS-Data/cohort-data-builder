"""Tag a random sample of real variables several ways and report where the methods agree.

The sample and run folders hold real study metadata (variable names, labels and value
labels; no respondent data). They live in ``adhoc/tiered/big/``, which is git-ignored; the
reports are copied into ``specs/004-tiered-tagger/results/`` by hand. From the repository
root, with ``S=specs/004-tiered-tagger/results/scripts``:

    # once: export each cohort, then draw the sample (10k, seed 2026)
    for c in bcs70 mcs ncds next_steps; do
      .venv/bin/python scripts/topics.py export site/data/$c --out adhoc/tiered/big/export/$c.jsonl
    done
    .venv/bin/python $S/compare_sample.py sample

    # tag: all of DEFAULT_RUNS, or some with --only; --limit N for a pilot. Resumable.
    uv run --project tools/topic-tagger python $S/compare_sample.py run
    uv run --project tools/topic-tagger python $S/compare_sample.py run --only tev-tiered \
      --limit 200

    # report: adhoc/tiered/big/report.html, or --out; --runs and --first to narrow it
    uv run --project tools/topic-tagger python $S/compare_sample.py report

Every run uses the bundled CLOSER scheme and 8 workers. Tiered runs offer ``other`` at tier 1
as an exit. Wall time is summed across every invocation of a run, from ``timing.jsonl``.
"""

from __future__ import annotations

import argparse
import html
import json
import random
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # the repository
BIG = ROOT / "adhoc/tiered/big"  # git-ignored: the export, the sample and the runs
EXPORT = BIG / "export"
SAMPLE = BIG / "variables.jsonl"
RUNS_DIR = BIG / "runs"
SCHEME = ROOT / "tools/topic-tagger/src/topic_tagger/schemes/closer.toml"

WORKERS = "8"  # the same for every run, so wall times compare
COMMON = ["--yes", "--plain", "--group-by", "cohort", "--retries", "2", "--workers", WORKERS]
CLEF_THRESHOLDS = ["--descend-at", "0.3", "--keep-at", "0.3"]
RUNS = {
    "gptoss-flat": ["--model", "gpt-oss:120b-cloud", "--method", "flat"],
    "gptoss-tiered": ["--model", "gpt-oss:120b-cloud", "--method", "tiered"],
    "clef-tiered": ["--provider", "ollama-decision", "--model", "clef:cloud", *CLEF_THRESHOLDS],
    "tev-tiered": ["--provider", "ollama-decision", "--model", "tev1:0.8b", *CLEF_THRESHOLDS],
}
DEFAULT_RUNS = ["gptoss-flat", "gptoss-tiered", "clef-tiered"]


# --- sample and run -----------------------------------------------------------------


def sample(n: int, seed: int) -> None:
    """Draw ``n`` variables at random from every exported cohort, noting each one's cohort."""
    pool = []
    for path in sorted(EXPORT.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                v = json.loads(line)
                v["cohort"] = path.stem
                v["file"] = f"{path.stem}.{v['file']}"  # file names may repeat across cohorts
                pool.append(v)
    picked = random.Random(seed).sample(pool, min(n, len(pool)))
    SAMPLE.write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in picked))
    by_cohort = dict(Counter(v["cohort"] for v in picked))
    print(f"Wrote {len(picked)} of {len(pool)} variables to {SAMPLE} (seed {seed}): {by_cohort}")


def run(names: list[str], limit: int | None = None) -> None:
    """Tag the sample each way; each run carries on from what its folder already has."""
    for name in names:
        out = RUNS_DIR / name
        argv = [sys.executable, "-m", "topic_tagger", "tag", str(SAMPLE), "--out", str(out)]
        argv += ["--scheme", str(SCHEME), *RUNS[name], *COMMON]
        if limit:
            argv += ["--limit", str(limit)]
        print(f"\n=== {name}: {' '.join(argv[3:])}", flush=True)
        out.mkdir(parents=True, exist_ok=True)
        start = time.time()
        try:
            code = subprocess.call(argv)
        except KeyboardInterrupt:
            code = 130
        end = time.time()
        tagged = 0
        if (out / "run.json").exists():
            tagged = json.loads((out / "run.json").read_text())["counts"]["tagged"]
        timing = {"start": start, "end": end, "tagged": tagged, "exit": code}
        with (out / "timing.jsonl").open("a") as f:
            f.write(json.dumps(timing) + "\n")
        print(f"=== {name}: exit {code}, {end - start:.0f} s", flush=True)
        if code == 130:
            sys.exit("Stopped. Run the same command again to carry on.")


# --- loading ------------------------------------------------------------------------


@dataclass
class Run:
    """One finished run folder.

    Attributes:
        name: The folder's name.
        settings: ``run.json`` settings of its last invocation.
        counts: ``run.json`` counts of its last invocation.
        records: ``{file/variable: tags.jsonl record}``.
        wall: Seconds, summed over every invocation.
        timeline: ``[seconds, variables]`` of the last invocation.
    """

    name: str
    settings: dict
    counts: dict
    records: dict[str, dict]
    wall: float
    timeline: list

    @property
    def tiered(self) -> bool:
        """Whether the run tagged tiered."""
        return self.settings.get("method") == "tiered"


def load_run(folder: Path) -> Run:
    """Read a run folder: its last ``run.json``, its records and its summed wall time."""
    meta = json.loads((folder / "run.json").read_text())
    records = {}
    for r in _jsonl(folder / "tags.jsonl"):
        records[f"{r['file']}/{r['variable']}"] = r
    timing = _jsonl(folder / "timing.jsonl") if (folder / "timing.jsonl").exists() else []
    wall = sum(t["end"] - t["start"] for t in timing) or _seconds(meta["started"], meta["ended"])
    return Run(
        folder.name, meta["settings"], meta["counts"], records, wall, meta.get("timeline", [])
    )


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _seconds(start: str, end: str) -> float:
    def parse(x: str) -> datetime:
        return datetime.fromisoformat(x.replace("Z", "+00:00"))

    return (parse(end) - parse(start)).total_seconds()


@dataclass
class Labels:
    """The scheme's areas and topics, for grouping and display."""

    area_of: dict[str, str]  # topic id -> area id
    area: dict[str, str]  # area id -> label
    topic: dict[str, str]  # topic id -> label


def load_labels() -> Labels:
    """The bundled scheme's areas and topics, read with the tagger's own loader."""
    sys.path.insert(0, str(SCHEME.parents[2]))
    from topic_tagger.scheme import load_scheme

    s = load_scheme(SCHEME)
    return Labels(
        {t.id: d.id for d in s.domains for t in d.topics},
        {d.id: d.label for d in s.domains},
        {t.id: t.label for t in s.topics},
    )


# --- measures -----------------------------------------------------------------------


def top(rec: dict | None) -> str | None:
    """A record's strongest topic."""
    return rec["topics"][0][0] if rec and rec["topics"] else None


def topics(rec: dict) -> set[str]:
    """A record's topics."""
    return {t for t, _ in rec["topics"]}


def areas(rec: dict | None, area_of: dict) -> set[str]:
    """The areas of a record's topics (the same measure for every method)."""
    return {area_of.get(t) for t, _ in rec["topics"]} if rec else set()


def jaccard(a: set, b: set) -> float:
    """Shared over combined; 1 when both are empty."""
    return len(a & b) / len(a | b) if a | b else 1.0


def share(flags: Iterable[bool]) -> float:
    """The share of true values; 0 when there are none."""
    flags = list(flags)
    return sum(flags) / len(flags) if flags else 0.0


def common(a: Run, b: Run, keys: list[str]) -> list[str]:
    """Keys both runs tagged."""
    return [k for k in keys if k in a.records and k in b.records]


def pair_stats(a: Run, b: Run, keys: list[str], area_of: dict) -> dict:
    """How far two runs agree on the variables both tagged."""
    both = common(a, b, keys)
    A, B = a.records, b.records
    return {
        "n": len(both),
        "top1": share(top(A[k]) == top(B[k]) for k in both),
        "top1_in_other": share(
            top(A[k]) in topics(B[k]) or top(B[k]) in topics(A[k]) for k in both
        ),
        "overlap": share(bool(topics(A[k]) & topics(B[k])) for k in both),
        "jaccard": statistics.mean([jaccard(topics(A[k]), topics(B[k])) for k in both] or [0]),
        "area_top": share(area_of.get(top(A[k])) == area_of.get(top(B[k])) for k in both),
        "area_jaccard": statistics.mean(
            [jaccard(areas(A[k], area_of), areas(B[k], area_of)) for k in both] or [0]
        ),
    }


def distribution(values: list[float], bins: int = 10) -> list[float]:
    """Shares of ``values`` (0 to 1) in equal bins; 1.0 falls in the last."""
    counts = [0] * bins
    for v in values:
        counts[min(int(v * bins), bins - 1)] += 1
    total = sum(counts) or 1
    return [c / total for c in counts]


# --- html pieces --------------------------------------------------------------------

COLOURS = ["#3b6ea8", "#c0763a", "#5a9a5a", "#8a5aa8", "#a84a4a"]
TENTHS = [f"{i / 10:.1f}" for i in range(10)]

CSS = """
:root{--paper:#fbfaf7;--ink:#1d1d1b;--muted:#6b6a65;--line:#e2dfd7;--accent:#3b6ea8}
@media (prefers-color-scheme:dark){
  :root{--paper:#171716;--ink:#ecebe6;--muted:#a3a29c;--line:#34332f}}
body{background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,sans-serif;
  margin:0 auto;max-width:1100px;padding:24px 16px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:18px;margin:36px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
h3{font-size:15px;margin:20px 0 6px}
.muted{color:var(--muted)}
table{border-collapse:collapse;font-size:13px;margin:8px 0}
th,td{padding:4px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.chart{width:100%;max-width:720px;height:auto;display:block}
.grid{stroke:var(--line)}
.tick{font-size:10px;fill:var(--muted)}
.legend{font-size:12px;margin:4px 0}
.key{margin-right:14px}
.key i{display:inline-block;width:10px;height:10px;margin-right:4px;vertical-align:-1px}
.heat{font-size:11px}
.heat td.h{background:color-mix(in srgb,var(--accent) calc(var(--s)*100%),transparent);
  text-align:right;min-width:26px}
.heat td.diag{outline:1px solid var(--ink)}
.heat th.rot{height:120px;white-space:nowrap;vertical-align:bottom}
.heat th.rot span{writing-mode:vertical-rl;transform:rotate(180deg)}
.wrap{overflow-x:auto}
.tags{font-family:ui-monospace,monospace;font-size:12px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
code{font-size:12px}
"""


def esc(x: object) -> str:
    """HTML-escape any value."""
    return html.escape(str(x))


def table(head: list[str], rows: Iterable[list], numeric_from: int = 1) -> str:
    """An HTML table; columns from ``numeric_from`` on are right-aligned numbers.

    Cells are inserted as given (already escaped or formatted).
    """

    def cells(values, tag):
        return "".join(
            f"<{tag}{' class=num' if i >= numeric_from else ''}>{v}</{tag}>"
            for i, v in enumerate(values)
        )

    body = "".join(f"<tr>{cells(r, 'td')}</tr>" for r in rows)
    return f"<table><tr>{cells(head, 'th')}</tr>{body}</table>"


def _legend(names: list[str]) -> str:
    keys = "".join(
        f'<span class="key"><i style="background:{COLOURS[j % len(COLOURS)]}"></i>{esc(n)}</span>'
        for j, n in enumerate(names)
    )
    return f'<div class="legend">{keys}</div>'


def _gridline(x1: float, x2: float, y: float) -> str:
    return f'<line x1="{x1}" x2="{x2}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'


def _tick(x: float, y: float, text: str, anchor: str = "middle", extra: str = "") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" class="tick" text-anchor="{anchor}"{extra}>'
        f"{esc(text)}</text>"
    )


def bars_svg(
    series: dict[str, list[float]],
    labels: list[str],
    width: int = 640,
    height: int = 200,
    pct: bool = True,
) -> str:
    """A grouped bar chart: ``series`` maps each name to one value per label."""
    names = list(series)
    peak = max((v for vs in series.values() for v in vs), default=1) or 1
    left, bottom, top_pad = 40, 34, 10
    plot_w, plot_h = width - left - 10, height - bottom - top_pad
    group = plot_w / max(len(labels), 1)
    bar = group * 0.8 / max(len(names), 1)
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for g in range(5):
        y = top_pad + plot_h - plot_h * g / 4
        value = peak * g / 4
        parts.append(_gridline(left, width - 10, y))
        parts.append(_tick(left - 4, y + 3, f"{value:.0%}" if pct else f"{value:.0f}", "end"))
    for i, label in enumerate(labels):
        x0 = left + i * group + group * 0.1
        for j, name in enumerate(names):
            v = series[name][i]
            h = plot_h * v / peak
            tip = f"{name} · {label}: {v:.1%}" if pct else f"{name} · {label}: {v:g}"
            parts.append(
                f'<rect x="{x0 + j * bar:.1f}" y="{top_pad + plot_h - h:.1f}" '
                f'width="{max(bar - 1, 1):.1f}" height="{h:.1f}" '
                f'fill="{COLOURS[j % len(COLOURS)]}"><title>{esc(tip)}</title></rect>'
            )
        parts.append(_tick(left + i * group + group / 2, height - bottom + 14, label))
    parts.append("</svg>")
    return _legend(names) + "".join(parts)


def lines_svg(
    series: dict[str, list[tuple[float, float]]],
    width: int = 640,
    height: int = 200,
    xlab: str = "",
    ylab: str = "",
) -> str:
    """A line chart: ``series`` maps each name to its ``(x, y)`` points."""
    names = list(series)
    xmax = max((x for s in series.values() for x, _ in s), default=1) or 1
    ymax = max((y for s in series.values() for _, y in s), default=1) or 1
    left, bottom, top_pad = 50, 34, 10
    plot_w, plot_h = width - left - 10, height - bottom - top_pad
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for g in range(5):
        y = top_pad + plot_h - plot_h * g / 4
        parts.append(_gridline(left, width - 10, y))
        parts.append(_tick(left - 4, y + 3, f"{ymax * g / 4:,.0f}", "end"))
        parts.append(_tick(left + plot_w * g / 4, height - bottom + 14, f"{xmax * g / 4:,.0f}"))
    for j, name in enumerate(names):
        points = " ".join(
            f"{left + plot_w * x / xmax:.1f},{top_pad + plot_h - plot_h * y / ymax:.1f}"
            for x, y in series[name]
        )
        colour = COLOURS[j % len(COLOURS)]
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="2"/>'
        )
    mid = top_pad + plot_h / 2
    parts.append(_tick(left + plot_w / 2, height - 4, xlab))
    parts.append(_tick(12, mid, ylab, extra=f' transform="rotate(-90 12 {mid})"'))
    parts.append("</svg>")
    return _legend(names) + "".join(parts)


def heat_table(
    ids: list[str], count: Callable[[str, str], int], label: Callable[[str], str], corner: str
) -> str:
    """A square confusion table, each cell shaded by its share of the row."""
    out = [f'<table class="heat"><tr><th>{esc(corner)}</th>']
    out += [f'<th class="rot"><span>{esc(label(c))}</span></th>' for c in ids]
    out.append("<th>n</th></tr>")
    for r in ids:
        total = sum(count(r, c) for c in ids) or 1
        out.append(f"<tr><th>{esc(label(r))}</th>")
        for c in ids:
            v = count(r, c)
            diag = " diag" if r == c else ""
            out.append(
                f'<td class="h{diag}" style="--s:{v / total:.3f}" title="{v} ({v / total:.0%})">'
                f"{v or ''}</td>"
            )
        out.append(f"<td class=n>{total}</td></tr>")
    out.append("</table>")
    return "".join(out)


def tags_cell(rec: dict | None, topic_label: dict) -> str:
    """A record's tags, with the areas it came through when tiered."""
    if rec is None:
        return '<span class="muted">failed</span>'
    text = ", ".join(f"{esc(topic_label.get(t, t))} {c:.2f}" for t, c in rec["topics"])
    if rec.get("path"):
        via = ", ".join(f"{esc(a)} {c:.2f}" for a, c in rec["path"])
        text += f'<br><span class="muted">via {via}</span>'
    return text


def _hms(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


# --- report sections ----------------------------------------------------------------


def section_runs(runs: list[Run], keys: list[str]) -> list[str]:
    """Runs, requests and latency, and the tagging timeline."""
    head = ["Run", "Model", "Method", "Tagged", "Failed", "Requests", "Req/var", "Wall time"]
    head += ["Var/min", "Workers", "≈ s/request", "≈ s/var (1 worker)"]
    rows = []
    for r in runs:
        tagged = sum(k in r.records for k in keys)
        requests = r.counts.get("requests", 0)
        workers = r.settings.get("workers", 1)
        rows.append([
            esc(r.name),
            f"{esc(r.settings['provider'])}:{esc(r.settings['model'])}",
            esc(r.settings.get("method", "flat")),
            f"{tagged:,}",
            f"{len(keys) - tagged:,}",
            f"{requests:,}",
            f"{requests / max(r.counts.get('todo', 1), 1):.2f}",
            _hms(r.wall),
            f"{r.counts.get('tagged', 0) / r.wall * 60 if r.wall else 0:,.0f}",
            workers,
            f"{r.wall * workers / requests if requests else 0:.1f}",
            f"{r.wall * workers / max(len(r.records), 1):.2f}",
        ])  # fmt: skip
    out = ["<h2>Runs, requests and latency</h2>", table(head, rows, numeric_from=3)]
    out.append(
        "<p class=muted>Requests and req/var are from the last invocation of each run (a "
        "resumed run counts only what it did). Wall time is summed over every invocation. "
        "≈ s/request = wall time × workers ÷ requests: the mean time one request held a "
        "worker. ≈ s/var uses every variable the run has tagged.</p>"
    )
    by_tier = [
        f"{esc(r.name)}: "
        + ", ".join(f"{i}: {n:,}" for i, n in enumerate(r.counts.get("requests_by_tier") or [], 1))
        for r in runs
    ]
    out.append("<p>Requests by tier: " + "; ".join(by_tier) + "</p>")
    timelines = {}
    for r in runs:
        done, points = 0, [(0.0, 0)]
        for seconds, n in r.timeline:
            done += n
            points.append((seconds / 60, done))
        if len(points) > 1:
            timelines[r.name] = points
    if timelines:
        out.append("<h3>Variables tagged over time (last invocation)</h3>")
        out.append(lines_svg(timelines, xlab="minutes", ylab="variables"))
    return out


def section_agreement(runs: list[Run], keys: list[str], labels: Labels) -> list[str]:
    """Pairwise agreement, agreement by area, area confusion and variables per area."""
    area_of, area_ids = labels.area_of, list(labels.area)
    short = [labels.area[a][:12] for a in area_ids]
    pairs = list(combinations(runs, 2))
    head = ["Pair", "Both tagged", "Same top topic", "Top topic in other's tags"]
    head += ["Any topic shared", "Topic Jaccard", "Same top area", "Area Jaccard"]
    rows = []
    for a, b in pairs:
        p = pair_stats(a, b, keys, area_of)
        rows.append([
            f"{esc(a.name)} vs {esc(b.name)}", f"{p['n']:,}", f"{p['top1']:.1%}",
            f"{p['top1_in_other']:.1%}", f"{p['overlap']:.1%}", f"{p['jaccard']:.2f}",
            f"{p['area_top']:.1%}", f"{p['area_jaccard']:.2f}",
        ])  # fmt: skip
    out = ["<h2>Agreement between methods</h2>", table(head, rows)]

    if len(runs) >= 3:
        everyone = [k for k in keys if all(k in r.records for r in runs)]
        distinct_tops = [len({top(r.records[k]) for r in runs}) for k in everyone]
        distinct_areas = [len({area_of.get(top(r.records[k])) for r in runs}) for k in everyone]
        n = len(everyone) or 1
        out.append(
            f"<p>Of {len(everyone):,} variables tagged by all {len(runs)}: "
            f"<b>{distinct_tops.count(1) / n:.1%}</b> share the same top topic, "
            f"{distinct_tops.count(2) / n:.1%} have two different top topics, "
            f"{distinct_tops.count(3) / n:.1%} three. Same top area in all: "
            f"<b>{distinct_areas.count(1) / n:.1%}</b>.</p>"
        )

    out.append("<h3>Same top topic, by the first run's top area</h3>")
    series = {}
    for a, b in pairs:
        both = common(a, b, keys)
        series[f"{a.name} vs {b.name}"] = [
            share(
                top(a.records[k]) == top(b.records[k])
                for k in both
                if area_of.get(top(a.records[k])) == area
            )
            for area in area_ids
        ]
    out.append(f"<div class=wrap>{bars_svg(series, short, width=1000, height=240)}</div>")

    out.append("<h3>Top area: how one method's choice maps to another's</h3>")
    for a, b in pairs:
        pairs_count = Counter(
            (area_of.get(top(a.records[k])), area_of.get(top(b.records[k])))
            for k in common(a, b, keys)
        )
        out.append(
            f"<p class=muted>{esc(a.name)} (rows) vs {esc(b.name)} (columns). Shading is the "
            "share of the row; the diagonal is outlined.</p>"
        )
        heat = heat_table(
            area_ids,
            lambda r, c, counted=pairs_count: counted.get((r, c), 0),
            labels.area.__getitem__,
            f"{a.name} ↓ / {b.name} →",
        )
        out.append(f"<div class=wrap>{heat}</div>")

    out.append("<h3>Variables per area, by run</h3>")
    series = {}
    for r in runs:
        tagged = [r.records[k] for k in keys if k in r.records]
        per_area = Counter(area for rec in tagged for area in areas(rec, area_of))
        series[r.name] = [per_area[a] / (len(tagged) or 1) for a in area_ids]
    out.append(f"<div class=wrap>{bars_svg(series, short, width=1000, height=240)}</div>")
    return out


def section_distributions(runs: list[Run], keys: list[str], labels: Labels) -> list[str]:
    """Confidence distributions, tags and areas per variable, and confidence vs agreement."""
    tagged = {r.name: [r.records[k] for k in keys if k in r.records] for r in runs}
    top_conf = {n: [rec["topics"][0][1] for rec in recs] for n, recs in tagged.items()}
    all_conf = {n: [c for rec in recs for _, c in rec["topics"]] for n, recs in tagged.items()}

    def panel(title: str, chart: str) -> str:
        return f"<div><h3>{title}</h3>{chart}</div>"

    panels = [
        panel("Top topic's confidence", bars_svg(_dists(top_conf), TENTHS, width=480)),
        panel("Every stored tag's confidence", bars_svg(_dists(all_conf), TENTHS, width=480)),
    ]
    tiered = [r for r in runs if r.tiered]
    if tiered:
        strongest_area = {
            r.name: [max(c for _, c in rec["path"]) for rec in tagged[r.name] if rec.get("path")]
            for r in tiered
        }
        panels.append(
            panel(
                "Strongest area's confidence (tier 1)",
                bars_svg(_dists(strongest_area), TENTHS, width=480),
            )
        )
        followed = {r.name: [len(rec.get("path", [])) for rec in tagged[r.name]] for r in tiered}
        panels.append(panel("Areas followed per variable", _count_chart(followed, cap=3)))
    tag_counts = {n: [len(rec["topics"]) for rec in recs] for n, recs in tagged.items()}
    panels.append(panel("Tags per variable", _count_chart(tag_counts, cap=8)))
    out = ["<h2>Confidence and probability distributions</h2>"]
    out.append('<div class="grid2">' + "".join(panels) + "</div>")

    head = ["Run", "Median top conf.", "Mean top conf.", "Top &lt; 0.5", "Mean tags"]
    head += ["2+ topics", "Topics from 2+ areas", "Fallback 'other' as top"]
    rows = []
    for r in runs:
        recs, conf = tagged[r.name], top_conf[r.name] or [0]
        rows.append([
            esc(r.name),
            f"{statistics.median(conf):.2f}",
            f"{statistics.mean(conf):.2f}",
            f"{share(c < 0.5 for c in conf):.1%}",
            f"{statistics.mean([len(x['topics']) for x in recs] or [0]):.2f}",
            f"{share(len(x['topics']) > 1 for x in recs):.1%}",
            f"{share(len(areas(x, labels.area_of)) > 1 for x in recs):.1%}",
            f"{share(top(x) == 'other' for x in recs):.1%}",
        ])  # fmt: skip
    out.append(table(head, rows))

    out.append(
        "<h3>Does confidence predict agreement?</h3><p class=muted>Share of variables where "
        "the pair agrees on the top topic, by the first run's top confidence.</p>"
    )
    series = {}
    for a, b in combinations(runs, 2):
        by_bin = defaultdict(list)
        for k in common(a, b, keys):
            conf = a.records[k]["topics"][0][1]
            by_bin[min(int(conf * 10), 9)].append(top(a.records[k]) == top(b.records[k]))
        series[f"{a.name} vs {b.name}"] = [share(by_bin[i]) for i in range(10)]
    out.append(bars_svg(series, TENTHS))
    return out


def _dists(values: dict[str, list[float]]) -> dict[str, list[float]]:
    return {name: distribution(v) for name, v in values.items()}


def _count_chart(counts: dict[str, list[int]], cap: int) -> str:
    """Shares of 1, 2, … ``cap``-or-more, per run."""
    top_bin = min(max((max(v) for v in counts.values() if v), default=1), cap)
    labels = [str(i) if i < top_bin else f"{i}+" for i in range(1, top_bin + 1)]

    def shares(values: list[int]) -> list[float]:
        return [share(min(v, top_bin) == i for v in values) for i in range(1, top_bin + 1)]

    return bars_svg({name: shares(v) for name, v in counts.items()}, labels, width=480)


def section_disagreements(
    runs: list[Run], keys: list[str], meta: dict, labels: Labels, examples: int
) -> list[str]:
    """The commonest top-topic swaps per pair, and random examples with every run's tags."""
    out = ["<h2>Where the methods disagree</h2>"]
    for a, b in combinations(runs, 2):
        swaps = Counter(
            (top(a.records[k]), top(b.records[k]))
            for k in common(a, b, keys)
            if top(a.records[k]) != top(b.records[k])
        )
        rows = [
            [esc(labels.topic.get(x, x)), esc(labels.topic.get(y, y)), f"{n:,}"]
            for (x, y), n in swaps.most_common(15)
        ]
        out.append(f"<h3>Most common top-topic swaps: {esc(a.name)} → {esc(b.name)}</h3>")
        out.append(table([esc(a.name), esc(b.name), "Variables"], rows, numeric_from=2))

    differ = [
        k
        for k in keys
        if all(k in r.records for r in runs) and len({top(r.records[k]) for r in runs}) > 1
    ]
    picked = random.Random(7).sample(differ, min(examples, len(differ)))
    out.append(
        f"<h3>{len(picked)} random examples, of {len(differ):,} where the top topics differ</h3>"
    )
    rows = []
    for k in sorted(picked, key=lambda k: (meta[k]["cohort"], k)):
        v = meta[k]
        values = v.get("values") or []
        shown = "; ".join(f"{esc(code)} {esc(text)}" for code, text in values[:6])
        if len(values) > 6:
            shown += f" … +{len(values) - 6}"
        where = f"{esc(v['cohort'])} · {esc(v['file'].split('.', 1)[-1])}"
        rows.append([
            f"<code>{esc(v['variable'])}</code><br><span class=muted>{where}</span>",
            f"{esc(v.get('label') or '')}<br><span class=muted>{shown}</span>",
            *(f"<span class=tags>{tags_cell(r.records.get(k), labels.topic)}</span>" for r in runs),
        ])  # fmt: skip
    head = ["Variable", "Label and values", *(esc(r.name) for r in runs)]
    out.append(f"<div class=wrap>{table(head, rows, numeric_from=len(head))}</div>")
    return out


def report(out_path: Path, examples: int, only: list[str] | None = None, first: int = 0) -> None:
    """Write the comparison report for the chosen runs over the sample (or its first N)."""
    labels = load_labels()
    variables = _jsonl(SAMPLE)
    if first:
        variables = variables[:first]
    meta = {f"{v['file']}/{v['variable']}": v for v in variables}
    keys = list(meta)
    runs = [load_run(RUNS_DIR / n) for n in only or DEFAULT_RUNS if (RUNS_DIR / n).is_dir()]
    if not runs:
        sys.exit(f"No finished runs in {RUNS_DIR}")
    cohorts = Counter(v["cohort"] for v in variables)
    page = [
        "<!doctype html><html lang=en><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        f"<title>Tagger method comparison</title><style>{CSS}</style><body>",
        "<h1>Tagger method comparison</h1>",
        f"<p class=muted>{len(keys):,} variables sampled at random from "
        + ", ".join(f"{esc(c)} {n:,}" for c, n in sorted(cohorts.items()))
        + f". Scheme: bundled CLOSER ({len(labels.area)} areas, {len(labels.topic)} topics). "
        f"Generated {time.strftime('%Y-%m-%d %H:%M')}.</p>",
        *section_runs(runs, keys),
        *section_agreement(runs, keys, labels),
        *section_distributions(runs, keys, labels),
        *section_disagreements(runs, keys, meta, labels, examples),
        "</body></html>",
    ]
    out_path.write_text("\n".join(page))
    print(f"Wrote {out_path}")


def main() -> None:
    """Parse the command line and run ``sample``, ``run`` or ``report``."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="draw the sample from the exported cohorts")
    s.add_argument("--n", type=int, default=10_000)
    s.add_argument("--seed", type=int, default=2026)
    r = sub.add_parser("run", help="tag the sample, carrying on from earlier runs")
    r.add_argument("--only", help="comma-separated: " + ", ".join(RUNS))
    r.add_argument("--limit", type=int, help="tag at most this many more variables (a pilot)")
    rep = sub.add_parser("report", help="write the comparison report")
    rep.add_argument("--out", type=Path, default=BIG / "report.html")
    rep.add_argument("--examples", type=int, default=150)
    rep.add_argument("--runs", help="comma-separated runs to compare (default: the main three)")
    rep.add_argument("--first", type=int, default=0, help="only the sample's first N variables")
    args = parser.parse_args()
    if args.cmd == "sample":
        sample(args.n, args.seed)
    elif args.cmd == "run":
        names = args.only.split(",") if args.only else DEFAULT_RUNS
        unknown = set(names) - set(RUNS)
        if unknown:
            sys.exit(f"unknown runs: {', '.join(sorted(unknown))}")
        run(names, args.limit)
    else:
        only = args.runs.split(",") if args.runs else None
        report(args.out, args.examples, only, args.first)


if __name__ == "__main__":
    main()
