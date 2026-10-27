"""Shared pytest fixtures: serving a copy of the site over HTTP, with any data folder."""

import functools
import http.server
import shutil
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
FIXTURE_DATA = ROOT / "tests" / "fixtures" / "data"


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/python/e2e/" in item.path.as_posix():
            item.add_marker(pytest.mark.e2e)


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Serves `directory` under a URL prefix, as GitHub Pages serves a project site."""

    def __init__(self, *args, prefix="", **kwargs):
        self.prefix = prefix
        super().__init__(*args, **kwargs)

    def translate_path(self, path):
        if self.prefix:
            if not path.startswith(self.prefix + "/"):
                return str(Path(self.directory) / "__outside_prefix__")
            path = path[len(self.prefix) :]
        return super().translate_path(path)

    def log_message(self, *args):
        pass


@pytest.fixture
def serve():
    servers = []

    def start(root, prefix=""):
        handler = functools.partial(_Handler, directory=str(root), prefix=prefix.rstrip("/"))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_port}{prefix.rstrip('/')}/"

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


@pytest.fixture
def site_with_data(tmp_path):
    def build(data_dir):
        site = tmp_path / "site"
        shutil.copytree(SITE, site, ignore=shutil.ignore_patterns("data"))
        if data_dir is not None:
            shutil.copytree(data_dir, site / "data")
        return site

    return build


@pytest.fixture
def mini_site(site_with_data):
    return site_with_data(FIXTURE_DATA)
