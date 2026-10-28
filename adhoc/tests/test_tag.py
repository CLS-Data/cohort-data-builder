from tag import tag_cohort


def fake(codes, counts):
    """A tagger run returning ``codes`` in turn, and a tag count returning ``counts``."""
    codes, counts = iter(codes), iter(counts)
    return (lambda: next(codes)), (lambda: next(counts))


def test_finished_first_time():
    run, tagged = fake([0], [0, 10])
    assert tag_cohort(run, tagged, tries=3, wait=0, sleep=lambda s: None) == 0


def test_restarts_after_a_crash_until_finished():
    # A traceback (e.g. a reply that is not JSON) exits 1 with variables left to do.
    run, tagged = fake([1, 1, 0], [0, 5, 9, 10])
    waits = []
    assert tag_cohort(run, tagged, tries=3, wait=30, sleep=waits.append) == 0
    assert waits == [30, 30]


def test_gives_up_after_tries_without_progress():
    run, tagged = fake([1, 1, 1, 1], [5, 5, 5, 5, 5])
    assert tag_cohort(run, tagged, tries=3, wait=0, sleep=lambda s: None) == 1


def test_progress_resets_the_count():
    run, tagged = fake([1, 1, 1, 1, 0], [0, 0, 0, 4, 4, 9])
    assert tag_cohort(run, tagged, tries=2, wait=0, sleep=lambda s: None) == 0


def test_stops_at_once_on_ctrl_c_bad_input_or_lock():
    for code in (130, 2, 4):
        run, tagged = fake([code], [0, 3])
        assert tag_cohort(run, tagged, tries=3, wait=0, sleep=lambda s: None) == code
