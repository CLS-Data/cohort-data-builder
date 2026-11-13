"""R and Stata availability for the generated-script tests.

Tests marked `needs_r` skip when Rscript with haven is missing, unless CDB_REQUIRE_R=1
(set in CI), in which case they fail: CI must never pass by skipping them.

Tests marked `needs_stata` skip when no Stata is found. Stata is licensed and cannot be
installed on CI runners, so there is no flag to require it (constitution I, licensed-tools
exception): a reviewer runs these locally.
"""

import functools
import glob
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


@functools.cache
def stata_binary():
    """The Stata executable: CDB_STATA, else stata-mp/-se/stata on PATH, else a macOS app.

    Returns:
        The path as a string, or None when no Stata is found.
    """
    if os.environ.get("CDB_STATA"):
        return os.environ["CDB_STATA"]
    for name in ("stata-mp", "stata-se", "stata"):
        if found := shutil.which(name):
            return found
    apps = sorted(glob.glob("/Applications/Stata*/Stata*.app/Contents/MacOS/stata-*"))
    return next((a for a in apps if not a.endswith(".dylib")), None)


@pytest.fixture(autouse=True)
def _require_stata(request):
    if request.node.get_closest_marker("needs_stata") is None or stata_binary():
        return
    pytest.skip("Stata is not available (set CDB_STATA to its executable)")
