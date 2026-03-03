"""Server wrapper error handling tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from souschef import server


@pytest.mark.parametrize(
    "func,args",
    [
        (server.parse_template, ("/bad/path",)),
        (server.parse_custom_resource, ("/bad/path",)),
        (server.list_directory, ("/bad/path",)),
        (server.read_file, ("/bad/path",)),
        (server.read_cookbook_metadata, ("/bad/path",)),
        (server.parse_recipe, ("/bad/path",)),
        (server.parse_attributes, ("/bad/path",)),
        (server.parse_inspec_profile, ("/bad/path",)),
        (server.convert_inspec_to_test, ("/bad/path",)),
    ],
)
def test_wrapper_invalid_path_returns_error(func, args) -> None:
    """Wrapper functions should return formatted errors on invalid paths."""
    with patch(
        "souschef.server._normalise_workspace_path", side_effect=ValueError("bad")
    ):
        result = func(*args)

    assert "Error" in str(result)


def test_parse_cookbook_metadata_invalid_path() -> None:
    """Parse cookbook metadata should return error dict on invalid path."""
    with patch(
        "souschef.server._normalise_workspace_path", side_effect=ValueError("bad")
    ):
        result = server.parse_cookbook_metadata("/bad/path")

    assert "error" in result
