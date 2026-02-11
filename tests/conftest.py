"""Pytest configuration and fixtures for SousChef tests."""

import os

import pytest


@pytest.fixture(autouse=True)
def setup_workspace_root(request):
    """
    Configure workspace root for tests.

    For test_server.py and class-based tests, set workspace root to "/"
    to allow any path. For snapshot tests, don't override to preserve
    path-relative behaviour needed by snapshot tests.
    """
    # Skip this fixture for snapshot tests
    if "snapshots" in request.node.fspath.strpath:
        yield
        return

    old_root = os.environ.get("SOUSCHEF_WORKSPACE_ROOT")
    os.environ["SOUSCHEF_WORKSPACE_ROOT"] = "/"
    yield
    # Clean up
    if old_root is None:
        os.environ.pop("SOUSCHEF_WORKSPACE_ROOT", None)
    else:
        os.environ["SOUSCHEF_WORKSPACE_ROOT"] = old_root
