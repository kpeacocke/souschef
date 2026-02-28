"""
Security tests for path containment and validation functions.

This module tests the security-critical path validation functions that
prevent directory traversal attacks (CWE-22) and path manipulation
vulnerabilities.
"""

import os
from pathlib import Path

import pytest

from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
    _safe_join,
    _validate_relative_parts,
    _validated_candidate,
    safe_exists,
    safe_glob,
    safe_is_dir,
    safe_is_file,
    safe_iterdir,
    safe_mkdir,
    safe_read_text,
    safe_write_text,
)


class TestPathContainmentSecurity:
    """Test path containment validation against directory traversal attacks."""

    def test_ensure_within_base_path_basic_valid(self, tmp_path):
        """Test that valid paths within base are accepted."""
        base = tmp_path / "workspace"
        base.mkdir()
        safe_path = base / "cookbook" / "recipe.rb"
        safe_path.parent.mkdir(parents=True)
        safe_path.write_text("# recipe")

        result = _ensure_within_base_path(safe_path, base)

        assert result == safe_path.resolve()
        assert str(result).startswith(str(base.resolve()))

    def test_ensure_within_base_path_traversal_parent(self, tmp_path):
        """Test that path traversal using .. is blocked."""
        base = tmp_path / "workspace"
        base.mkdir()
        attack_path = base / ".." / ".." / "etc" / "passwd"

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _ensure_within_base_path(attack_path, base)

    def test_ensure_within_base_path_traversal_absolute(self, tmp_path):
        """Test that absolute paths outside base are blocked."""
        base = tmp_path / "workspace"
        base.mkdir()
        attack_path = Path("/etc/passwd")

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _ensure_within_base_path(attack_path, base)

    def test_ensure_within_base_path_traversal_complex(self, tmp_path):
        """Test that complex traversal attempts are blocked."""
        base = tmp_path / "workspace"
        base.mkdir()
        # Path that goes into workspace then back out
        attack_path = base / "subdir" / ".." / ".." / ".." / "etc" / "passwd"

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _ensure_within_base_path(attack_path, base)

    def test_ensure_within_base_path_symlink_escape(self, tmp_path):
        """Test that symlinks pointing outside base are blocked."""
        base = tmp_path / "workspace"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        outside_file = outside / "secret.txt"
        outside_file.write_text("secret data")

        # Create symlink inside base pointing outside
        symlink = base / "link_to_outside"
        symlink.symlink_to(outside_file)

        # Symlink should be resolved and detected as outside base
        with pytest.raises(ValueError, match="Path traversal attempt"):
            _ensure_within_base_path(symlink, base)

    def test_ensure_within_base_path_relative_paths(self, tmp_path):
        """Test that relative paths are resolved correctly."""
        base = tmp_path / "workspace"
        base.mkdir()
        subdir = base / "cookbook"
        subdir.mkdir()

        # Should resolve relative to current working directory
        # This test validates that resolution works correctly
        result = _ensure_within_base_path(subdir / "recipe.rb", base)
        assert str(result).startswith(str(base.resolve()))

    def test_ensure_within_base_path_url_encoding_bypass(self, tmp_path):
        """Test that URL-encoded traversal sequences are blocked."""
        base = tmp_path / "workspace"
        base.mkdir()

        # URL encoding doesn't apply to filesystem paths in Python
        # but test that unusual characters don't bypass validation
        unusual_path = base / "%2e%2e" / "etc" / "passwd"

        # Path.resolve() will normalize this
        # If it resolves outside base, should be caught
        try:
            result = _ensure_within_base_path(unusual_path, base)
            # If it doesn't raise, ensure it's still within base
            assert str(result).startswith(str(base.resolve()))
        except ValueError:
            # Also acceptable - path rejected
            pass

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific path handling")
    def test_ensure_within_base_path_backslash_windows_style(self, tmp_path):
        """Test that Windows-style backslash paths are handled safely."""
        base = tmp_path / "workspace"
        base.mkdir()

        # Test with backslashes (Windows path separators)
        # Path() normalizes these automatically on Windows
        safe_path = base / "cookbook" / "recipe.rb"
        result = _ensure_within_base_path(safe_path, base)

        assert str(result).startswith(str(base.resolve()))

    def test_ensure_within_base_path_double_slash(self, tmp_path):
        """Test that double slashes don't bypass validation."""
        base = tmp_path / "workspace"
        base.mkdir()

        # Double slashes should be normalized by Path.resolve()
        attack_path = str(base / "cookbook" / ".." / ".." / "etc" / "passwd").replace(
            "/", "//"
        )
        result_path = Path(attack_path)

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _ensure_within_base_path(result_path, base)

    def test_ensure_within_base_path_empty_path_components(self, tmp_path):
        """Test that empty path components are handled safely."""
        base = tmp_path / "workspace"
        base.mkdir()
        safe_path = base / "" / "cookbook" / "" / "recipe.rb"

        # Path() should normalize empty components
        result = _ensure_within_base_path(safe_path, base)
        assert str(result).startswith(str(base.resolve()))


class TestNormalizePathSecurity:
    """Test path normalization against null byte injection and invalid paths."""

    def test_workspace_root_env_missing_path(self, tmp_path, monkeypatch):
        """Test workspace root rejects missing paths."""
        missing_path = tmp_path / "missing"
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(missing_path))

        with pytest.raises(ValueError, match="Workspace root does not exist"):
            _get_workspace_root()

    def test_workspace_root_env_not_directory(self, tmp_path, monkeypatch):
        """Test workspace root rejects non-directory paths."""
        file_path = tmp_path / "workspace.txt"
        file_path.write_text("content")
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(file_path))

        with pytest.raises(ValueError, match="Workspace root is not a directory"):
            _get_workspace_root()

    def test_validate_relative_parts_detects_absolute_result(self, monkeypatch):
        """Test relative parts validation catches absolute results."""

        def fake_is_absolute(self):
            return "/" in str(self)

        monkeypatch.setattr(Path, "is_absolute", fake_is_absolute)

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _validate_relative_parts(("safe", "path"))

    def test_normalize_path_null_byte_injection(self):
        """Test that null bytes in paths are rejected (CWE-158)."""
        attack_path = "cookbook/recipe.rb\x00.txt"

        with pytest.raises(ValueError, match="null bytes"):
            _normalize_path(attack_path)

    def test_normalize_path_null_byte_middle(self):
        """Test that null bytes in middle of path are rejected."""
        attack_path = "cookbook\x00/recipe.rb"

        with pytest.raises(ValueError, match="null bytes"):
            _normalize_path(attack_path)

    def test_normalize_path_valid_string(self, tmp_path):
        """Test that valid string paths are normalized correctly."""
        path_str = str(tmp_path / "cookbook" / "recipe.rb")
        result = _normalize_path(path_str)

        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_normalize_path_valid_path_object(self, tmp_path):
        """Test that valid Path objects are normalized correctly."""
        path_obj = tmp_path / "cookbook" / "recipe.rb"
        result = _normalize_path(path_obj)

        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_normalize_path_invalid_type(self):
        """Test that invalid types are rejected."""
        with pytest.raises(ValueError, match="must be a string or Path"):
            _normalize_path(123)

    def test_normalize_path_home_directory_expansion(self):
        """Test that home directory paths are expanded correctly."""
        path_with_tilde = "~/cookbook/recipe.rb"
        result = _normalize_path(path_with_tilde)

        assert isinstance(result, Path)
        assert "~" not in str(result)
        assert result.is_absolute()


class TestSafeJoinSecurity:
    """Test safe path joining against traversal attacks."""

    def test_safe_join_valid_paths(self, tmp_path):
        """Test that valid path components are joined correctly."""
        base = tmp_path / "workspace"
        base.mkdir()

        result = _safe_join(base, "cookbook", "recipe.rb")

        assert str(result).startswith(str(base.resolve()))
        assert result.name == "recipe.rb"

    def test_safe_join_traversal_attempt(self, tmp_path):
        """Test that traversal attempts in components are blocked."""
        base = tmp_path / "workspace"
        base.mkdir()

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _safe_join(base, "..", "..", "etc", "passwd")

    def test_safe_join_absolute_component(self, tmp_path):
        """Test that absolute path components don't escape base."""
        base = tmp_path / "workspace"
        base.mkdir()

        # Joining with absolute path - depends on Path.joinpath() behavior
        # Path().joinpath() with absolute path replaces base, then resolve() detects escape
        with pytest.raises(ValueError, match="Path traversal attempt"):
            _safe_join(base, "/etc/passwd")

    def test_safe_join_mixed_traversal(self, tmp_path):
        """Test that mixed valid/invalid components are blocked."""
        base = tmp_path / "workspace"
        base.mkdir()

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _safe_join(base, "cookbook", "..", "..", "etc", "passwd")

    def test_safe_join_empty_components(self, tmp_path):
        """Test that empty components are handled safely."""
        base = tmp_path / "workspace"
        base.mkdir()

        result = _safe_join(base, "cookbook", "", "recipe.rb")

        assert str(result).startswith(str(base.resolve()))


class TestSafeFilesystemOperations:
    """Test safe filesystem wrappers enforce containment."""

    def test_safe_exists_within_base(self, tmp_path):
        """Test that safe_exists works for paths within base."""
        base = tmp_path / "workspace"
        base.mkdir()
        test_file = base / "test.txt"
        test_file.write_text("test")

        assert safe_exists(test_file, base) is True
        assert safe_exists(base / "nonexistent.txt", base) is False

    def test_safe_exists_outside_base(self, tmp_path):
        """Test that safe_exists rejects paths outside base."""
        base = tmp_path / "workspace"
        base.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("outside")

        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_exists(outside, base)

    def test_safe_is_dir_within_base(self, tmp_path):
        """Test that safe_is_dir works for paths within base."""
        base = tmp_path / "workspace"
        base.mkdir()
        subdir = base / "subdir"
        subdir.mkdir()

        assert safe_is_dir(subdir, base) is True
        assert safe_is_dir(base / "nonexistent", base) is False

    def test_safe_is_file_within_base(self, tmp_path):
        """Test that safe_is_file works for paths within base."""
        base = tmp_path / "workspace"
        base.mkdir()
        test_file = base / "test.txt"
        test_file.write_text("test")

        assert safe_is_file(test_file, base) is True
        assert safe_is_file(base / "nonexistent.txt", base) is False

    def test_safe_mkdir_within_base(self, tmp_path):
        """Test that safe_mkdir creates directories within base."""
        base = tmp_path / "workspace"
        base.mkdir()
        new_dir = base / "new_dir"

        safe_mkdir(new_dir, base)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_safe_mkdir_outside_base(self, tmp_path):
        """Test that safe_mkdir rejects paths outside base."""
        base = tmp_path / "workspace"
        base.mkdir()
        outside = tmp_path / "outside"

        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_mkdir(outside, base)

    def test_safe_read_text_within_base(self, tmp_path):
        """Test that safe_read_text reads files within base."""
        base = tmp_path / "workspace"
        base.mkdir()
        test_file = base / "test.txt"
        test_content = "test content"
        test_file.write_text(test_content)

        result = safe_read_text(test_file, base)

        assert result == test_content

    def test_safe_read_text_outside_base(self, tmp_path):
        """Test that safe_read_text rejects paths outside base."""
        base = tmp_path / "workspace"
        base.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("outside")

        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_read_text(outside, base)

    def test_safe_write_text_within_base(self, tmp_path):
        """Test that safe_write_text writes files within base."""
        base = tmp_path / "workspace"
        base.mkdir()
        test_file = base / "test.txt"
        test_content = "test content"

        safe_write_text(test_file, base, test_content)

        assert test_file.read_text() == test_content

    def test_safe_write_text_outside_base(self, tmp_path):
        """Test that safe_write_text rejects paths outside base."""
        base = tmp_path / "workspace"
        base.mkdir()
        outside = tmp_path / "outside.txt"

        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_write_text(outside, base, "content")

    def test_safe_iterdir_within_base(self, tmp_path):
        """Test that safe_iterdir lists directory contents within base."""
        base = tmp_path / "workspace"
        base.mkdir()
        (base / "file1.txt").write_text("1")
        (base / "file2.txt").write_text("2")
        subdir = base / "subdir"
        subdir.mkdir()

        results = safe_iterdir(base, base)

        assert len(results) == 3
        assert all(str(r).startswith(str(base.resolve())) for r in results)

    def test_safe_iterdir_outside_base(self, tmp_path):
        """Test that safe_iterdir rejects paths outside base."""
        base = tmp_path / "workspace"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_iterdir(outside, base)

    def test_safe_glob_valid_pattern(self, tmp_path):
        """Test that safe_glob finds files with valid patterns."""
        base = tmp_path / "workspace"
        base.mkdir()
        (base / "file1.txt").write_text("1")
        (base / "file2.txt").write_text("2")
        (base / "file.rb").write_text("ruby")

        results = safe_glob(base, "*.txt", base)

        assert len(results) == 2
        assert all(p.suffix == ".txt" for p in results)
        assert all(str(r).startswith(str(base.resolve())) for r in results)

    def test_safe_glob_traversal_pattern(self, tmp_path):
        """Test that safe_glob rejects patterns with traversal sequences."""
        base = tmp_path / "workspace"
        base.mkdir()

        with pytest.raises(ValueError, match="Unsafe glob pattern"):
            safe_glob(base, "../*.txt", base)

    def test_safe_glob_absolute_pattern(self, tmp_path):
        """Test that safe_glob rejects absolute patterns."""
        base = tmp_path / "workspace"
        base.mkdir()

        with pytest.raises(ValueError, match="Absolute glob patterns"):
            safe_glob(base, "/etc/*.conf", base)


class TestValidatedCandidate:
    """Test the _validated_candidate helper function."""

    def test_validated_candidate_within_base(self, tmp_path):
        """Test that paths within base are validated correctly."""
        base = tmp_path / "workspace"
        base.mkdir()
        safe_path = base / "cookbook"

        result = _validated_candidate(safe_path, base)

        assert str(result).startswith(str(base.resolve()))

    def test_validated_candidate_traversal_attempt(self, tmp_path):
        """Test that traversal attempts are rejected."""
        base = tmp_path / "workspace"
        base.mkdir()
        attack_path = base / ".." / "etc" / "passwd"

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _validated_candidate(attack_path, base)

    def test_validated_candidate_absolute_outside(self, tmp_path):
        """Test that absolute paths outside base are rejected."""
        base = tmp_path / "workspace"
        base.mkdir()

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _validated_candidate(Path("/etc/passwd"), base)


class TestPathSecurityIntegration:
    """Integration tests combining multiple security functions."""

    def test_workflow_safe_directory_creation_and_file_write(self, tmp_path):
        """Test complete workflow with safe operations."""
        base = tmp_path / "workspace"
        base.mkdir()

        # Create nested directory safely
        new_dir = base / "cookbooks" / "apache"
        safe_mkdir(new_dir, base, parents=True, exist_ok=True)

        # Write file safely
        recipe_file = new_dir / "default.rb"
        safe_write_text(recipe_file, base, "# Apache recipe")

        # Read it back safely
        content = safe_read_text(recipe_file, base)

        assert content == "# Apache recipe"
        assert safe_exists(recipe_file, base)
        assert safe_is_file(recipe_file, base)

    def test_workflow_prevents_directory_escape(self, tmp_path):
        """Test that complete workflow prevents directory escape."""
        base = tmp_path / "workspace"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        # Try to create directory outside base
        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_mkdir(outside / "escaped", base)

        # Try to write file outside base
        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_write_text(outside / "escaped.txt", base, "data")

        # Verify outside directory is untouched
        assert not (outside / "escaped").exists()
        assert not (outside / "escaped.txt").exists()

    def test_workflow_symlink_attack_prevention(self, tmp_path):
        """Test that workflow prevents symlink-based attacks."""
        base = tmp_path / "workspace"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        target = outside / "target.txt"
        target.write_text("secret")

        # Create symlink inside base pointing outside
        link = base / "link"
        link.symlink_to(target)

        # Attempts to use symlink should be blocked
        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_read_text(link, base)

        with pytest.raises(ValueError, match="Path traversal attempt"):
            safe_write_text(link, base, "new content")

    def test_workflow_recursive_glob_stays_contained(self, tmp_path):
        """Test that recursive glob operations stay contained."""
        base = tmp_path / "workspace"
        base.mkdir()
        (base / "cookbook1").mkdir()
        (base / "cookbook1" / "recipe.rb").write_text("recipe1")
        (base / "cookbook2").mkdir()
        (base / "cookbook2" / "recipe.rb").write_text("recipe2")

        # Recursive glob should find both but stay in base
        results = safe_glob(base, "*/recipe.rb", base)

        assert len(results) == 2
        assert all(str(r).startswith(str(base.resolve())) for r in results)
        assert all(r.name == "recipe.rb" for r in results)
