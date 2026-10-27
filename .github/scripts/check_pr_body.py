"""Check that a pull request description has a filled-in "How to review" section.

The constitution requires every pull request to carry clear, numbered review steps. This
script is the `pr-description` status check: it reads the pull request body from the
`PR_BODY` environment variable, prints each problem found, and exits 1 if there are any.

Standard library only, so the workflow needs no setup beyond a checkout.
"""

from __future__ import annotations

import os
import re
import sys

HEADING = re.compile(r"^##\s+How to review\s*$", re.IGNORECASE | re.MULTILINE)
NEXT_HEADING = re.compile(r"^##\s", re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
NUMBERED_STEP = re.compile(r"^\s*\d+\.\s+\S", re.MULTILINE)

# Text from the template's skeleton that means the section was not filled in. Kept in step
# with .github/pull_request_template.md; a test reads the template to make sure it fails.
PLACEHOLDERS = (
    "~N min",
    "<branch>",
    "<test command>",
    "<expected result>",
    "<serve command>",
    "<URL>",
    "<what to click>",
    "<what you should see>",
    "<files that carry the logic>",
    "<wiring, fixtures>",
    "<what this PR deliberately does not do>",
)


def section(body: str) -> str | None:
    """Return the text of the "How to review" section, or None if it has no heading.

    The section runs from its heading to the next level-two heading or the end of the body.

    Args:
        body: The whole pull request description.

    Returns:
        The section's text without its heading, or None when the heading is missing.
    """
    found = HEADING.search(body)
    if not found:
        return None
    rest = body[found.end() :]
    following = NEXT_HEADING.search(rest)
    return rest[: following.start()] if following else rest


def problems(body: str | None) -> list[str]:
    """List what is wrong with a pull request's "How to review" section.

    Only the first problem is reported: each later check assumes the earlier ones passed,
    so one fix at a time gives the clearest message.

    Args:
        body: The pull request description; None (GitHub's value for an empty
            description) is treated as an empty string.

    Returns:
        Human-readable problems, empty when the section is acceptable.
    """
    text = section(body or "")
    if text is None:
        return ['Add a "## How to review" section (see .github/pull_request_template.md).']

    visible = COMMENT.sub("", text).strip()
    if not visible:
        return ['The "How to review" section is empty: add numbered steps a reviewer can follow.']

    left = [p for p in PLACEHOLDERS if p in visible]
    if left:
        return [
            'The "How to review" section still has template placeholders: '
            + ", ".join(left)
            + ". Replace them with real commands, URLs and expected results."
        ]

    if not NUMBERED_STEP.search(visible):
        return ['The "How to review" section needs numbered steps ("1. ...").']

    return []


def main() -> int:
    """Check the body in the PR_BODY environment variable and report the result.

    Returns:
        0 when the section is acceptable, 1 otherwise.
    """
    found = problems(os.environ.get("PR_BODY"))
    for problem in found:
        print(problem)
    if found:
        return 1
    print("How to review: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
