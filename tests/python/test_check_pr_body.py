"""Tests for .github/scripts/check_pr_body.py, the pr-description check."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "check_pr_body.py"
TEMPLATE = Path(__file__).resolve().parents[2] / ".github" / "pull_request_template.md"


@pytest.fixture(scope="module")
def check():
    spec = importlib.util.spec_from_file_location("check_pr_body", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FILLED = """## Summary

Adds search.

## How to review

**Time needed:** ~10 min

1. Check out: `git fetch && git switch 001-us1-search`
2. Run: `npm test` → all pass

**Out of scope:** topics.

## Checklist

- [x] CI green
"""


def test_filled_section_passes(check):
    assert check.problems(FILLED) == []


def test_missing_heading_is_one_problem(check):
    body = "## Summary\n\nAdds search.\n"
    assert len(check.problems(body)) == 1


def test_none_is_treated_as_empty_body(check):
    assert len(check.problems(None)) == 1


def test_empty_section_is_one_problem(check):
    body = "## How to review\n\n## Checklist\n\n- [x] CI green\n"
    assert len(check.problems(body)) == 1


def test_section_with_only_html_comments_is_one_problem(check):
    body = "## How to review\n\n<!-- steps go here -->\n\n## Checklist\n"
    assert len(check.problems(body)) == 1


@pytest.mark.parametrize("placeholder", ["~N min", "<branch>"])
def test_template_placeholder_is_one_problem(check, placeholder):
    body = (
        FILLED.replace("~10 min", placeholder)
        if placeholder == "~N min"
        else FILLED.replace("001-us1-search", placeholder)
    )
    assert len(check.problems(body)) == 1


def test_section_without_numbered_step_is_one_problem(check):
    body = "## How to review\n\nJust look at it.\n\n## Checklist\n"
    assert len(check.problems(body)) == 1


def test_section_ends_at_next_heading(check):
    # A numbered step under a later heading does not count for How to review.
    body = "## How to review\n\nLook at it.\n\n## Checklist\n\n1. CI green\n"
    assert len(check.problems(body)) == 1


def test_unedited_template_fails(check):
    assert check.problems(TEMPLATE.read_text(encoding="utf-8"))


def test_main_exits_1_and_lists_problems(check, monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", "## Summary\n")
    assert check.main() == 1
    assert capsys.readouterr().out.strip()


def test_main_reports_ok(check, monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", FILLED)
    assert check.main() == 0
    assert "How to review: OK" in capsys.readouterr().out
