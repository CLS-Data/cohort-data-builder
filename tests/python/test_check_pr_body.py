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


def only(found):
    """The single problem reported; the checker reports one at a time."""
    assert len(found) == 1, found
    return found[0]


@pytest.mark.parametrize("body", [None, "", "## Summary\n\nAdds search.\n"])
def test_a_missing_section_asks_for_one(check, body):
    assert 'Add a "## How to review" section' in only(check.problems(body))


def test_an_empty_section_says_it_is_empty(check):
    body = "## How to review\n\n## Checklist\n\n- [x] CI green\n"
    assert "is empty" in only(check.problems(body))


def test_a_section_with_only_html_comments_counts_as_empty(check):
    body = "## How to review\n\n<!-- steps go here -->\n\n## Checklist\n"
    assert "is empty" in only(check.problems(body))


@pytest.mark.parametrize(
    ("placeholder", "replaces"), [("~N min", "~10 min"), ("<branch>", "001-us1-search")]
)
def test_a_template_placeholder_is_named(check, placeholder, replaces):
    problem = only(check.problems(FILLED.replace(replaces, placeholder)))
    assert "placeholders" in problem and placeholder in problem


def test_a_section_without_numbered_steps_asks_for_them(check):
    body = "## How to review\n\nJust look at it.\n\n## Checklist\n"
    assert "numbered steps" in only(check.problems(body))


def test_a_numbered_step_under_a_later_heading_does_not_count(check):
    body = "## How to review\n\nLook at it.\n\n## Checklist\n\n1. CI green\n"
    assert "numbered steps" in only(check.problems(body))


def test_windows_line_endings_are_accepted(check):
    assert check.problems(FILLED.replace("\n", "\r\n")) == []


def test_unedited_template_fails(check):
    assert check.problems(TEMPLATE.read_text(encoding="utf-8"))


def test_main_exits_1_and_lists_problems(check, monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", "## Summary\n")
    assert check.main() == 1
    assert "How to review" in capsys.readouterr().out


def test_main_reports_ok(check, monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", FILLED)
    assert check.main() == 0
    assert "How to review: OK" in capsys.readouterr().out


ROOT = Path(__file__).resolve().parents[2]


def test_dependabot_pull_requests_skip_the_description_check():
    """A bot cannot write review steps, so its pull requests skip the check."""
    workflow = (ROOT / ".github" / "workflows" / "pr-description.yml").read_text()
    assert "if: github.event.pull_request.user.login != 'dependabot[bot]'" in workflow
