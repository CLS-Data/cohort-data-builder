import io

from rich.console import Console

from topic_tagger.display import RunView


def busy_view(small_scheme, clock):
    """600 to do; 120 done after 100 s, 72 of them in the last minute; one retry."""
    view = RunView(total=600, todo=600, scheme=small_scheme, clock=clock)
    clock.advance(40)
    view.on_event("batch_done", {"n": 48, "tags": [[("smoking", 0.9), ("alcohol", 0.5)]] * 48})
    view.on_event("retry", {})
    clock.advance(60)
    view.on_event("batch_done", {"n": 72, "tags": [[("age", 0.8)]] * 72})
    return view


def test_snapshot_has_every_figure(small_scheme, clock):
    s = busy_view(small_scheme, clock).snapshot()
    assert (s["done"], s["left"], s["percent"]) == (120, 480, 20)
    assert s["elapsed"] == 100
    assert s["per_minute"] == 72  # only the last 60 s count
    assert s["eta"] == 400  # 480 left at 72 a minute
    assert (s["failed"], s["retries"]) == (0, 1)
    assert s["top_domains"] == [("demographics", 72), ("health", 48)]
    assert s["top_topics"] == [("age", 72), ("smoking", 48), ("alcohol", 48)]


def test_a_variable_counts_once_per_domain(small_scheme, clock):
    view = RunView(total=1, todo=1, scheme=small_scheme, clock=clock)
    view.on_event("batch_done", {"n": 1, "tags": [[("smoking", 0.9), ("alcohol", 0.8)]]})
    assert view.snapshot()["top_domains"] == [("health", 1)]


def test_failures_count_as_done(small_scheme, clock):
    view = RunView(total=10, todo=10, scheme=small_scheme, clock=clock)
    view.on_event("failed", {"key": "f/v"})
    s = view.snapshot()
    assert (s["done"], s["left"], s["failed"]) == (1, 9, 1)


def test_no_speed_means_no_eta(small_scheme, clock):
    view = RunView(total=10, todo=10, scheme=small_scheme, clock=clock)
    assert view.snapshot()["eta"] is None
    assert "eta --:--:--" in view.plain_line()


def test_the_leading_topics_are_capped(small_scheme, clock):
    view = RunView(total=8, todo=8, scheme=small_scheme, clock=clock)
    tags = [[(t, 0.9)] for t in small_scheme.topic_ids]
    view.on_event("batch_done", {"n": len(tags), "tags": tags})
    s = view.snapshot()
    assert len(s["top_topics"]) == min(10, len(small_scheme.topic_ids))
    assert len(s["top_domains"]) <= 5


def test_the_live_view_shows_each_figure(small_scheme, clock):
    view = busy_view(small_scheme, clock)
    console = Console(record=True, width=100)
    console.print(view.render())
    text = console.export_text()
    for part in ("120/600", "20%", "72/min", "00:06:40", "00:01:40", "Demographics", "Age"):
        assert part in text, text
    assert "Failed 0" in text and "Retried 1" in text


def test_the_live_view_refreshes_four_times_a_second(small_scheme, clock):
    view = busy_view(small_scheme, clock)
    live = view.live(Console(file=io.StringIO()))
    assert live.refresh_per_second == 4


def test_plain_mode_writes_a_line_every_10_seconds(small_scheme, clock):
    view = RunView(total=600, todo=600, scheme=small_scheme, clock=clock)
    out = io.StringIO()
    for _ in range(4):
        clock.advance(5)
        view.tick(out)
    assert len(out.getvalue().splitlines()) == 2


def test_the_plain_line_format(small_scheme, clock):
    view = busy_view(small_scheme, clock)
    assert view.plain_line() == "[00:01:40] 120/600 (20%) 72/min eta 00:06:40 failed 0 retries 1"


def test_the_timeline_counts_variables_per_10_seconds(small_scheme, clock):
    view = busy_view(small_scheme, clock)
    assert view.timeline() == [[t, 0] for t in range(0, 40, 10)] + [
        [40, 48],
        [50, 0],
        [60, 0],
        [70, 0],
        [80, 0],
        [90, 0],
        [100, 72],
    ]
