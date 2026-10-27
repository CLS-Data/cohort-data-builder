"""Watching a run: a live view in a terminal, or plain progress lines when there is none.

``RunView`` is fed the runner's events and works out the figures; ``live`` and ``plain``
show them while the run goes on.
"""

from __future__ import annotations

import threading
from collections import Counter, deque
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TextIO

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from topic_tagger.scheme import Scheme

WINDOW = 60  # seconds the speed is measured over
PLAIN_EVERY = 10  # seconds between plain progress lines
TOP_DOMAINS, TOP_TOPICS = 5, 10


def _hms(seconds: float | None) -> str:
    if seconds is None:
        return "--:--:--"
    s = round(seconds)
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}"


class RunView:
    """The figures of a run in progress, updated from the runner's events.

    Args:
        total: Variables in the input.
        todo: Variables this run will tag.
        scheme: The topic scheme, for labels and topic areas.
        clock: The clock the elapsed time and speed are measured with.
    """

    def __init__(self, total: int, todo: int, scheme: Scheme, clock):
        self.total = total
        self.todo = todo
        self.scheme = scheme
        self.clock = clock
        self.started = clock.now()
        self.tagged = 0
        self.failed = 0
        self.retries = 0
        self.domains: Counter[str] = Counter()
        self.topics: Counter[str] = Counter()
        self._recent: deque[tuple[float, int]] = deque()
        self._last_line = self.started
        # Events arrive in the main thread; the live view renders from its own.
        self._lock = threading.Lock()

    def on_event(self, kind: str, data: dict) -> None:
        """Take one of the runner's events: ``batch_done``, ``failed`` or ``retry``."""
        with self._lock:
            if kind == "batch_done":
                self.tagged += data["n"]
                self._recent.append((self.clock.now(), data["n"]))
                for tags in data["tags"]:
                    ids = [t for t, _ in tags]
                    self.topics.update(ids)
                    self.domains.update({self.scheme.domain_of(t).id for t in ids})
            elif kind == "failed":
                self.failed += 1
                self._recent.append((self.clock.now(), 1))
            elif kind == "retry":
                self.retries += 1

    def snapshot(self) -> dict:
        """The figures now: progress, times, speed, problems and the leading topics.

        Returns:
            ``done``, ``left``, ``percent``, ``elapsed`` and ``eta`` (seconds, None while
            there is no speed), ``per_minute`` (over the last minute), ``failed``,
            ``retries``, and ``top_domains`` and ``top_topics`` as ``(id, variables)``.
        """
        with self._lock:
            now = self.clock.now()
            while self._recent and self._recent[0][0] <= now - WINDOW:
                self._recent.popleft()
            elapsed = now - self.started
            done = self.tagged + self.failed
            left = max(self.todo - done, 0)
            span = min(WINDOW, elapsed)
            per_minute = sum(n for _, n in self._recent) * 60 / span if span > 0 else 0
            order = {t: i for i, t in enumerate(self.scheme.topic_ids)}
            # Ties in scheme order, so the view does not shuffle between refreshes.
            topics = sorted(self.topics.items(), key=lambda x: (-x[1], order[x[0]]))
            domain_order = {d.id: i for i, d in enumerate(self.scheme.domains)}
            domains = sorted(self.domains.items(), key=lambda x: (-x[1], domain_order[x[0]]))
            return {
                "done": done,
                "left": left,
                "percent": round(100 * done / self.todo) if self.todo else 100,
                "elapsed": elapsed,
                "eta": left * 60 / per_minute if per_minute else None,
                "per_minute": round(per_minute),
                "failed": self.failed,
                "retries": self.retries,
                "top_domains": domains[:TOP_DOMAINS],
                "top_topics": topics[:TOP_TOPICS],
            }

    def plain_line(self) -> str:
        """One line of progress, for logs and terminals without a live view."""
        s = self.snapshot()
        return (
            f"[{_hms(s['elapsed'])}] {s['done']}/{self.todo} ({s['percent']}%) "
            f"{s['per_minute']}/min eta {_hms(s['eta'])} "
            f"failed {s['failed']} retries {s['retries']}"
        )

    def tick(self, stream: TextIO) -> None:
        """Write a plain line if the last one was at least 10 seconds ago."""
        now = self.clock.now()
        if now - self._last_line >= PLAIN_EVERY:
            self._last_line = now
            print(self.plain_line(), file=stream, flush=True)

    def render(self) -> RenderableType:
        """The live view.

        A progress bar with times and speed, the leading topic areas and topics, and the
        failed and retried counts.
        """
        s = self.snapshot()
        bar = Table.grid(padding=(0, 2))
        bar.add_row(
            ProgressBar(total=self.todo or 1, completed=s["done"], width=40),
            f"{s['percent']}%",
            f"{s['done']}/{self.todo}",
            f"elapsed {_hms(s['elapsed'])}",
            f"remaining {_hms(s['eta'])}",
            f"{s['per_minute']}/min",
        )
        domains = Table(title="Leading topic areas", title_justify="left", expand=True)
        domains.add_column("Topic area")
        domains.add_column("Variables", justify="right")
        labels = {d.id: d.label for d in self.scheme.domains}
        for d, n in s["top_domains"]:
            domains.add_row(labels[d], str(n))
        topics = Table(title="Leading topics", title_justify="left", expand=True)
        topics.add_column("Topic")
        topics.add_column("Variables", justify="right")
        topic_labels = {t.id: t.label for t in self.scheme.topics}
        for t, n in s["top_topics"]:
            topics.add_row(topic_labels[t], str(n))
        tables = Table.grid(expand=True, padding=(0, 2))
        tables.add_row(domains, topics)
        style = "red" if s["failed"] else "dim"
        footer = Text(f"Failed {s['failed']}   Retried {s['retries']}", style=style)
        return Group(bar, tables, footer)

    def live(self, console: Console) -> Live:
        """A live view that redraws four times a second; use it as a context manager."""
        return Live(get_renderable=self.render, console=console, refresh_per_second=4)

    @contextmanager
    def plain(self, stream: TextIO) -> Iterator[None]:
        """Write a plain line every 10 seconds while the block runs, and one at the end."""
        stop = threading.Event()

        def loop() -> None:
            while not stop.wait(1):
                self.tick(stream)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join()
            print(self.plain_line(), file=stream, flush=True)
