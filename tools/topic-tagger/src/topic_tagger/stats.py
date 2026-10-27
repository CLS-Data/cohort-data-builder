"""The statistics of a run's tags, for the summary, ``run.json`` and the report.

They are worked out from the stored records, so every number agrees with ``tags.jsonl``.
The fields are listed in docs/formats.md (*Run statistics*).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime

from topic_tagger.scheme import Scheme
from topic_tagger.variables import Variable

DEFAULT_THRESHOLD = 0.5  # the site shows tags at or above this by default


def _seconds(start: str, end: str) -> float:
    def parse(t: str) -> datetime:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))

    return (parse(end) - parse(start)).total_seconds()


def compute_stats(
    records: Iterable[dict],
    variables: list[Variable],
    scheme: Scheme,
    run: dict,
    group_by: str = "sweep",
) -> dict:
    """Work out the statistics of the tags for the given variables.

    Only records made with this scheme, for variables in the input, count.

    Args:
        records: Tag records, as stored in ``tags.jsonl``.
        variables: The input variables, in input order.
        scheme: The scheme the tags were made with.
        run: The run, with ``started``, ``ended``, ``counts.tagged`` and ``failed``.
        group_by: The input field to group by.

    Returns:
        The statistics, with the fields documented in *Run statistics*.
    """
    position = {v.key.lower(): i for i, v in enumerate(variables)}
    found: list[tuple[int, list]] = []
    for r in records:
        i = position.get(f"{r['file']}/{r['variable']}".lower())
        if i is not None and r.get("scheme") == scheme.hash:
            found.append((i, r["topics"]))
    # In input order, so groups appear in the order the input has them.
    tagged = [(variables[i], topics) for i, topics in sorted(found, key=lambda x: x[0])]

    per_topic = dict.fromkeys(scheme.topic_ids, 0)
    per_domain = {d.id: 0 for d in scheme.domains}
    histogram = [0] * 10
    below = n_tags = 0
    per_file = {v.file: {"tagged": 0, "failed": 0} for v in variables}
    per_group: Counter[str] = Counter()
    domain_by_group: dict[str, dict[str, int]] = {}

    for v, topics in tagged:
        domains = {scheme.domain_of(t).id for t, _ in topics}
        for t, conf in topics:
            per_topic[t] += 1
            # Rounded to whole percent first, so 0.7 lands in [0.7, 0.8) despite floats.
            histogram[min(round(conf * 100) // 10, 9)] += 1
        for d in domains:
            per_domain[d] += 1
        n_tags += len(topics)
        if max(c for _, c in topics) < DEFAULT_THRESHOLD:
            below += 1
        per_file[v.file]["tagged"] += 1
        if group_by in v.extra and v.extra[group_by] is not None:
            g = str(v.extra[group_by])
            per_group[g] += 1
            row = domain_by_group.setdefault(g, {d.id: 0 for d in scheme.domains})
            for d in domains:
                row[d] += 1

    failed = set(run.get("failed", []))
    for v in variables:
        if v.key in failed:
            per_file[v.file]["failed"] += 1

    seconds = _seconds(run["started"], run["ended"])
    done = run["counts"]["tagged"]
    n = len(tagged)
    return {
        "per_topic": per_topic,
        "per_domain": per_domain,
        "unused": [t for t, c in per_topic.items() if c == 0],
        "confidence_histogram": histogram,
        "below_default": round(below / n, 4) if n else 0,
        "mean_topics": round(n_tags / n, 2) if n else 0,
        "per_file": per_file,
        "group_by": group_by,
        "per_group": dict(per_group),
        "domain_by_group": domain_by_group,
        "speed": round(done * 60 / seconds, 1) if seconds > 0 else 0,
    }
