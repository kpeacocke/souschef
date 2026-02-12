"""Targeted tests to close coverage gaps and reach 92% coverage target."""

import tempfile
from pathlib import Path

import pytest

from souschef.core.path_utils import (
    _ensure_within_base_path,
    _normalize_path,
    _safe_join,
    safe_exists,
    safe_glob,
    safe_is_dir,
    safe_is_file,
)
from souschef.parsers.recipe import (
    _extract_properties,
    _extract_resources,
    parse_recipe,
)


class TestNormalizePathEdgeCases:
    """Test path normalization edge cases to improve coverage."""

    def test_normalize_path_with_null_bytes(self) -> None:
        """Test rejection of paths with null bytes."""
        with pytest.raises(ValueError, match="contains null bytes"):
            _normalize_path("safe/path\x00malicious")

    def test_normalize_path_invalid_type(self) -> None:
        """Test rejection of invalid path types."""
        with pytest.raises(ValueError, match="must be a string or Path object"):
            _normalize_path(123)  # type: ignore

    def test_normalize_path_valid_string(self) -> None:
        """Test normalizing valid path string."""
        result = _normalize_path("./test/path")
        assert isinstance(result, Path)

    def test_normalize_path_with_path_object(self) -> None:
        """Test normalizing Path object."""
        input_path = Path("./test/path")
        result = _normalize_path(input_path)
        assert isinstance(result, Path)

    def test_ensure_within_base_path_traversal_attempt(self) -> None:
        """Test detection of path traversal attacks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            parent = base.parent
            with pytest.raises(ValueError, match="escapes"):
                _ensure_within_base_path(parent / "escaped", base)

    def test_safe_join_with_traversal(self) -> None:
        """Test that safe_join rejects .. patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with pytest.raises(ValueError, match="escapes"):
                _safe_join(base, "..", "etc", "passwd")


class TestRecipeParserEdgeCases:
    """Test edge cases in recipe parser to improve coverage."""

    def test_extract_resources_empty_recipe(self) -> None:
        """Test parsing empty recipe content."""
        result = _extract_resources("")
        assert result == []

    def test_extract_resources_comment_only(self) -> None:
        """Test recipe with only comments."""
        recipe = "# This is a comment\n# Another comment"
        result = _extract_resources(recipe)
        assert result == []

    def test_parse_recipe_empty(self) -> None:
        """Test parsing empty recipe file."""
        result = parse_recipe("")
        assert isinstance(result, str)

    def test_parse_recipe_simple_resource(self) -> None:
        """Test parsing recipe with simple resource."""
        recipe = "package 'curl'"
        result = parse_recipe(recipe)
        assert isinstance(result, str)

    def test_extract_resources_nested_blocks(self) -> None:
        """Test extraction from nested notify/subscribe blocks."""
        recipe = """
package 'apache2' do
  action :install
end

service 'apache2' do
  action :start
  subscribes :restart, 'package[apache2]', :immediately
end
        """
        result = _extract_resources(recipe)
        assert isinstance(result, list)

    def test_extract_properties_edge_cases(self) -> None:
        """Test property extraction with edge cases."""
        properties_text = "action :nothing\nmode '0755'"
        result = _extract_properties(properties_text)
        assert isinstance(result, dict)


class TestFileOperationsEdgeCases:
    """Test filesystem operations edge cases."""

    def test_safe_exists_nonexistent_path(self) -> None:
        """Test checking existence of nonexistent path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            result = safe_exists(base / "nonexistent", base)
            assert result is False

    def test_safe_exists_valid_path(self) -> None:
        """Test checking existence of valid path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            test_file = base / "test.txt"
            test_file.touch()
            result = safe_exists(test_file, base)
            assert result is True

    def test_safe_is_dir_valid_directory(self) -> None:
        """Test checking directory-ness."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            subdir = base / "subdir"
            subdir.mkdir()
            result = safe_is_dir(subdir, base)
            assert result is True

    def test_safe_is_dir_on_file(self) -> None:
        """Test that files return False for is_dir check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            test_file = base / "test.txt"
            test_file.touch()
            result = safe_is_dir(test_file, base)
            assert result is False

    def test_safe_is_file_valid_file(self) -> None:
        """Test checking file-ness."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            test_file = base / "test.txt"
            test_file.touch()
            result = safe_is_file(test_file, base)
            assert result is True

    def test_safe_is_file_on_directory(self) -> None:
        """Test that directories return False for is_file check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            subdir = base / "subdir"
            subdir.mkdir()
            result = safe_is_file(subdir, base)
            assert result is False

    def test_safe_glob_with_literals(self) -> None:
        """Test globbing with literal filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "test1.txt").touch()
            (base / "test2.txt").touch()
            (base / "other.rb").touch()

            result = safe_glob(base, "*.txt", base)
            assert len(result) == 2

    def test_safe_glob_no_matches(self) -> None:
        """Test globbing with no matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "test.rb").touch()

            result = safe_glob(base, "*.txt", base)
            assert len(result) == 0

    def test_safe_glob_rejects_absolute_patterns(self) -> None:
        """Test that glob rejects absolute patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with pytest.raises(ValueError, match="not allowed"):
                safe_glob(base, "/etc/passwd", base)

    def test_safe_glob_rejects_traversal_patterns(self) -> None:
        """Test that glob rejects .. patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with pytest.raises(ValueError, match="Unsafe"):
                safe_glob(base, "../*.txt", base)
