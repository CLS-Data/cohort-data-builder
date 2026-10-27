"""The tool is general: every topic, description and instruction comes from the scheme file.

The bundled scheme happens to be based on the CLOSER topics, but nothing in the code may
depend on it or describe itself in its terms; the only mention allowed is its file name.
"""

import re
from pathlib import Path

SRC = Path(__file__).parents[1] / "src" / "topic_tagger"
SPECIFIC = re.compile(r"closer|cessda|mesh|elsst", re.IGNORECASE)


def test_the_code_mentions_no_particular_scheme():
    found = []
    for path in SRC.rglob("*.py"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if SPECIFIC.search(line.replace("closer.toml", "")):
                found.append(f"{path.relative_to(SRC)}:{n}: {line.strip()}")
    assert found == []


def test_the_code_names_no_topic_from_the_bundled_scheme(bundled_scheme_path):
    from topic_tagger.scheme import load_scheme

    bundled = load_scheme(bundled_scheme_path)
    ids = {t.id for t in bundled.topics} | {d.id for d in bundled.domains}
    code = "\n".join(p.read_text(encoding="utf-8") for p in SRC.rglob("*.py"))
    assert [i for i in sorted(ids) if re.search(rf"['\"]{i}['\"]", code)] == []
