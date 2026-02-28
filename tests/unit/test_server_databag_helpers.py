"""Tests for databag usage and structure helpers in server module."""

from pathlib import Path
from unittest.mock import patch

from souschef import server
from souschef.server import (
    _analyse_databag_structure,
    _analyse_usage_patterns,
    _find_databag_patterns_in_content,
)


def test_find_databag_patterns_in_content() -> None:
    """Detect databag usage patterns in content."""
    content = """
    data_bag('users')
    data_bag_item('users', 'admin')
    encrypted_data_bag_item('secrets', 'db')
    search(:node, 'data_bag:users')
    """

    patterns = _find_databag_patterns_in_content(content, "recipe.rb")

    assert len(patterns) == 5
    databag_names = [pattern.get("databag_name") for pattern in patterns]
    item_names = [pattern.get("item_name") for pattern in patterns]
    types = [pattern.get("type", "") for pattern in patterns]

    assert "users" in databag_names
    assert "secrets" in databag_names
    assert "admin" in item_names
    assert any(pattern_type.startswith("search") for pattern_type in types)


def test_analyse_usage_patterns_empty() -> None:
    """No recommendations when there are no usage patterns."""
    assert _analyse_usage_patterns([]) == []


def test_analyse_usage_patterns_generates_recommendations() -> None:
    """Recommendations include encrypted and search patterns."""
    usage_patterns = [
        {"type": "data_bag()", "databag_name": "users"},
        {"type": "encrypted_data_bag_item()", "databag_name": "secrets"},
        {"type": "search() with data_bag", "databag_name": "users"},
    ]

    recommendations = _analyse_usage_patterns(usage_patterns)

    assert any("encrypted" in rec for rec in recommendations)
    assert any("search" in rec for rec in recommendations)


def test_analyse_databag_structure(tmp_path: Path) -> None:
    """Analyse databag structure with encrypted items."""
    databags_dir = tmp_path / "data_bags"
    databags_dir.mkdir()

    (databags_dir / "README.txt").write_text("not a directory")

    app_bag = databags_dir / "app"
    app_bag.mkdir()
    (app_bag / "config.json").write_text('{"key": "value"}')

    secrets_bag = databags_dir / "secrets"
    secrets_bag.mkdir()
    (secrets_bag / "secret.json").write_text('{"encrypted_data": "value"}')

    with patch("souschef.server._detect_encrypted_databag", side_effect=[False, True]):
        structure = _analyse_databag_structure(databags_dir)

    assert structure["total_databags"] == 2
    assert structure["total_items"] == 2
    assert structure["encrypted_items"] == 1
    assert "app" in structure["databags"]
    assert "secrets" in structure["databags"]


def test_analyse_databag_structure_handles_read_error(tmp_path: Path) -> None:
    """Databag structure captures read errors per item."""
    databags_dir = tmp_path / "data_bags"
    databags_dir.mkdir()

    app_bag = databags_dir / "app"
    app_bag.mkdir()
    item_path = app_bag / "config.json"
    item_path.write_text('{"key": "value"}')

    with patch("souschef.server.safe_read_text", side_effect=OSError("read failed")):
        structure = _analyse_databag_structure(databags_dir)

    assert structure["total_databags"] == 1
    assert structure["total_items"] == 1
    assert structure["databags"]["app"]["items"][0]["error"]


def test_generate_ansible_vault_skips_non_dirs(tmp_path: Path) -> None:
    """Non-directory entries are skipped during vault generation."""
    databags_dir = tmp_path / "data_bags"
    databags_dir.mkdir()
    (databags_dir / "note.txt").write_text("ignore")

    bag_dir = databags_dir / "app"
    bag_dir.mkdir()
    (bag_dir / "default.json").write_text('{"id": "default", "token": "abc"}')

    result = server.generate_ansible_vault_from_databags(str(databags_dir))

    assert "Summary" in result or "data bag" in result
