"""Additional parser tests for coverage improvements."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from souschef.parsers import attributes as attributes_parser
from souschef.parsers import habitat as habitat_parser
from souschef.parsers import metadata as metadata_parser
from souschef.parsers import recipe as recipe_parser
from souschef.profiling import _profile_directory_files


def test_read_cookbook_metadata_empty_warning(tmp_path: Path) -> None:
    """Empty metadata should produce a warning string."""
    metadata_file = tmp_path / "metadata.rb"
    metadata_file.write_text("")

    with patch("souschef.parsers.metadata.safe_read_text", return_value=""):
        result = metadata_parser.read_cookbook_metadata(str(metadata_file))

    assert "Warning" in result


def test_read_cookbook_metadata_permission_error(tmp_path: Path) -> None:
    """Permission errors should return formatted error."""
    metadata_file = tmp_path / "metadata.rb"
    metadata_file.write_text("name 'test'")

    with patch("souschef.parsers.metadata.safe_read_text", side_effect=PermissionError):
        result = metadata_parser.read_cookbook_metadata(str(metadata_file))

    assert "permission" in result.lower()


def test_parse_cookbook_metadata_error(tmp_path: Path) -> None:
    """Parsing errors should return error dictionary."""
    metadata_file = tmp_path / "metadata.rb"
    metadata_file.write_text("name 'test'")

    with patch(
        "souschef.parsers.metadata.safe_read_text", side_effect=FileNotFoundError
    ):
        result = metadata_parser.parse_cookbook_metadata(str(metadata_file))

    assert "error" in result


def test_convert_ruby_value_to_yaml_variants() -> None:
    """Ruby values should convert to YAML-friendly formats."""
    assert attributes_parser._convert_ruby_value_to_yaml("%w(nginx apache)")
    assert attributes_parser._convert_ruby_value_to_yaml("[]") == "[]"
    assert attributes_parser._convert_ruby_value_to_yaml("{key: 'value'}")
    # Function returns values as-is if they don't match special patterns
    assert attributes_parser._convert_ruby_value_to_yaml("'plain'") == "'plain'"


def test_convert_ruby_arrays_and_hashes() -> None:
    """Ruby arrays and hashes should convert to YAML lists and mappings."""
    assert attributes_parser._convert_ruby_array("[one, two]")
    assert attributes_parser._convert_ruby_hash("{a: 1, b: 2}")


def test_extract_plan_var_variants() -> None:
    """Extract plan variables for quoted and unquoted values."""
    content = "pkg_name='myapp'\npkg_origin=core\n"
    assert habitat_parser._extract_plan_var(content, "pkg_name") == "myapp"
    assert habitat_parser._extract_plan_var(content, "pkg_origin") == "core"
    assert habitat_parser._extract_plan_var(content, "missing") == ""


def test_extract_plan_array_missing() -> None:
    """Missing plan arrays should return empty list."""
    assert (
        habitat_parser._extract_plan_array("pkg_deps=(core/glibc)", "pkg_build_deps")
        == []
    )


def test_extract_conditionals_large_content() -> None:
    """Large content should short-circuit conditional parsing."""
    content = "x" * 1_000_001
    result = recipe_parser._extract_conditionals(content)
    assert result == []


def test_profile_directory_files_missing(tmp_path: Path) -> None:
    """Missing directory should return None."""
    result = _profile_directory_files(tmp_path / "missing", lambda _path: "", "op")
    assert result is None


def test_profile_directory_files_with_file(tmp_path: Path) -> None:
    """Profiling should aggregate when files exist."""
    (tmp_path / "default.rb").write_text("package 'nginx'")

    result = _profile_directory_files(tmp_path, lambda _path: "ok", "recipe")

    assert result is not None
    assert result.context["avg_per_file"] >= 0
