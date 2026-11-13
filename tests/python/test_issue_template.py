"""The tag-suggestion issue form has the fields the builder's link fills in (US4)."""

import re
from pathlib import Path

FORM = Path(__file__).resolve().parents[2] / ".github" / "ISSUE_TEMPLATE" / "tag-suggestion.yml"


def fields(text):
    """Each body field as (id, type, required), in order."""
    out = []
    for block in re.split(r"\n  - type: ", text)[1:]:
        kind = block.split("\n", 1)[0].strip()
        found = re.search(r"\n    id: (\S+)", block)
        if found:
            required = re.search(r"\n      required: true", block) is not None
            out.append((found.group(1), kind, required))
    return out


def test_the_form_is_labelled_and_titled():
    text = FORM.read_text()
    assert re.search(r'^labels: \["tag-suggestion"\]$', text, re.M)
    assert re.search(r'^title: "Tag suggestion: "$', text, re.M)
    assert re.search(r"^name: Tag suggestion$", text, re.M)


def test_the_form_has_the_fields_the_link_fills():
    assert fields(FORM.read_text()) == [
        ("cohort", "input", True),
        ("variable", "input", True),
        ("file", "input", True),
        ("label", "textarea", False),
        ("current", "textarea", False),
        ("suggested", "textarea", True),
        ("why", "textarea", False),
    ]
