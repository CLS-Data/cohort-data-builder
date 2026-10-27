"""R availability for the generated-script tests.

Tests marked `needs_r` skip when Rscript with haven is missing, unless CDB_REQUIRE_R=1
(set in CI), in which case they fail: CI must never pass by skipping them.
"""

import functools
import os
import shutil
import subprocess

import pytest


@functools.cache
def has_r():
    if not shutil.which("Rscript"):
        return False
    done = subprocess.run(
        ["Rscript", "-e", "library(haven)"], capture_output=True, timeout=120, check=False
    )
    return done.returncode == 0


@pytest.fixture(autouse=True)
def _require_r(request):
    if request.node.get_closest_marker("needs_r") is None or has_r():
        return
    message = "Rscript with the haven package is not available"
    if os.environ.get("CDB_REQUIRE_R") == "1":
        pytest.fail(message + " (CDB_REQUIRE_R=1)")
    pytest.skip(message)
