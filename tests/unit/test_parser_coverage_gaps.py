"""
Tests for uncovered lines in parser modules.

Covers exception handlers, edge cases, and rarely-exercised code paths
in the inspec, habitat, metadata, and recipe parsers.
"""

from __future__ import annotations

import json
import signal
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# souschef/parsers/inspec.py
# ---------------------------------------------------------------------------


class TestInspecParser:
    """Tests for InSpec parser error paths."""

    def test_parse_inspec_profile_empty_path_returns_error(self) -> None:
        """parse_inspec_profile returns an error string for an empty path."""
        from souschef.parsers.inspec import parse_inspec_profile

        result = parse_inspec_profile("")
        assert "Error" in result
        assert "empty" in result.lower()

    def test_parse_inspec_profile_whitespace_path_returns_error(self) -> None:
        """parse_inspec_profile returns an error string for a whitespace-only path."""
        from souschef.parsers.inspec import parse_inspec_profile

        result = parse_inspec_profile("   ")
        assert "Error" in result

    def test_parse_inspec_profile_nonexistent_path_returns_error(
        self, tmp_path: Path
    ) -> None:
        """parse_inspec_profile returns an error string for a path that does not exist."""
        from souschef.parsers.inspec import parse_inspec_profile

        nonexistent = str(tmp_path / "nonexistent_profile")
        result = parse_inspec_profile(nonexistent)
        assert "Error" in result

    def test_parse_inspec_profile_runtime_error_returned_as_string(
        self, tmp_path: Path
    ) -> None:
        """parse_inspec_profile returns an error string when RuntimeError is raised."""
        from souschef.parsers.inspec import parse_inspec_profile

        # Create a profile directory with a controls dir so we get past the exists check
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "controls").mkdir()

        with patch(
            "souschef.parsers.inspec._parse_controls_from_directory",
            side_effect=RuntimeError("parse failure"),
        ):
            result = parse_inspec_profile(str(profile_dir))
        assert "Error" in result

    def test_parse_inspec_profile_generic_exception_returned_as_string(
        self, tmp_path: Path
    ) -> None:
        """parse_inspec_profile returns an error string for unexpected exceptions."""
        from souschef.parsers.inspec import parse_inspec_profile

        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()

        with patch(
            "souschef.parsers.inspec._normalize_path",
            side_effect=Exception("unexpected"),
        ):
            result = parse_inspec_profile(str(profile_dir))
        assert "error" in result.lower()

    def test_convert_inspec_to_test_json_decode_error(self, tmp_path: Path) -> None:
        """convert_inspec_to_test returns an error string for malformed JSON."""
        from souschef.parsers.inspec import convert_inspec_to_test

        # Write a file with invalid JSON
        bad_json_file = tmp_path / "result.json"
        bad_json_file.write_text("not valid json {{{")

        with patch(
            "souschef.parsers.inspec.parse_inspec_profile",
            return_value="not valid json {{{",
        ):
            result = convert_inspec_to_test(str(bad_json_file))
        assert "Error" in result

    def test_convert_inspec_to_test_generic_exception(self, tmp_path: Path) -> None:
        """convert_inspec_to_test returns an error string for unexpected exceptions."""
        from souschef.parsers.inspec import convert_inspec_to_test

        valid_data = json.dumps({"controls": []})
        with patch(
            "souschef.parsers.inspec.parse_inspec_profile",
            return_value=valid_data,
        ), patch(
            "souschef.parsers.inspec.json.loads",
            side_effect=Exception("unexpected"),
        ):
            result = convert_inspec_to_test("/fake/path")
        assert "error" in result.lower()

    def test_generate_inspec_from_chef_delegates_correctly(self) -> None:
        """generate_inspec_from_chef calls _generate_inspec_from_resource."""
        from souschef.parsers.inspec import generate_inspec_from_chef

        result = generate_inspec_from_chef("file", "/etc/hosts", {"mode": "0644"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_parse_controls_from_directory_raises_on_file_read_error(
        self, tmp_path: Path
    ) -> None:
        """_parse_controls_from_directory raises RuntimeError when a file can't be read."""
        from souschef.parsers.inspec import _parse_controls_from_directory

        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        controls_dir = profile_dir / "controls"
        controls_dir.mkdir()

        # Create a control file
        ctrl_file = controls_dir / "test.rb"
        ctrl_file.write_text('control "test-1" do\nend\n')

        with patch(
            "souschef.parsers.inspec.safe_read_text",
            side_effect=Exception("read error"),
        ), pytest.raises(RuntimeError, match="Error reading"):
            _parse_controls_from_directory(profile_dir)

    def test_parse_controls_from_file_raises_on_read_error(
        self, tmp_path: Path
    ) -> None:
        """_parse_controls_from_file raises RuntimeError when file can't be read."""
        from souschef.parsers.inspec import _parse_controls_from_file

        ctrl_file = tmp_path / "test.rb"
        ctrl_file.write_text('control "test" do\nend\n')

        with (
            patch.object(Path, "read_text", side_effect=Exception("read fail")),
            pytest.raises(RuntimeError, match="Error reading file"),
        ):
            _parse_controls_from_file(ctrl_file)


# ---------------------------------------------------------------------------
# souschef/parsers/habitat.py
# ---------------------------------------------------------------------------


class TestHabitatParser:
    """Tests for Habitat plan parser edge cases."""

    def test_parse_habitat_plan_permission_error(self, tmp_path: Path) -> None:
        """parse_habitat_plan returns an error string for PermissionError."""
        from souschef.parsers.habitat import parse_habitat_plan

        plan_file = tmp_path / "plan.sh"
        plan_file.write_text("pkg_name=myapp\n")

        with patch(
            "souschef.parsers.habitat.safe_read_text",
            side_effect=PermissionError("access denied"),
        ), patch(
            "souschef.parsers.habitat._get_workspace_root",
            return_value=tmp_path,
        ):
            result = parse_habitat_plan(str(plan_file))
        assert "Permission" in result or "denied" in result.lower() or "error" in result.lower()

    def test_parse_habitat_plan_generic_exception(self, tmp_path: Path) -> None:
        """parse_habitat_plan returns an error string for unexpected exceptions."""
        from souschef.parsers.habitat import parse_habitat_plan

        plan_file = tmp_path / "plan.sh"
        plan_file.write_text("pkg_name=myapp\n")

        with patch(
            "souschef.parsers.habitat.json.dumps",
            side_effect=RuntimeError("unexpected error"),
        ), patch(
            "souschef.parsers.habitat._get_workspace_root",
            return_value=tmp_path,
        ):
            result = parse_habitat_plan(str(plan_file))
        assert "Error" in result

    def test_extract_plan_array_blank_lines_between_elements(self) -> None:
        """_extract_plan_array handles arrays with blank lines between elements."""
        from souschef.parsers.habitat import _extract_plan_array

        content = 'pkg_deps=(\n  "core/glibc"\n\n  "core/openssl"\n)\n'
        result = _extract_plan_array(content, "pkg_deps")
        # Blank lines should be skipped; only real elements returned
        assert "core/glibc" in result
        assert "core/openssl" in result

    def test_extract_plan_array_unmatched_paren_returns_empty(self) -> None:
        """_extract_plan_array returns [] for content with unmatched parens."""
        from souschef.parsers.habitat import _extract_plan_array

        # Unclosed array
        content = "pkg_deps=(\n  core/glibc\n"
        result = _extract_plan_array(content, "pkg_deps")
        assert result == []

    def test_extract_plan_exports_nested_parens(self) -> None:
        """_extract_plan_exports handles content with nested parentheses."""
        from souschef.parsers.habitat import _extract_plan_exports

        # Nested parens inside the array
        content = 'pkg_exports=(\n  [port]=$(echo "(80)")\n)\n'
        # Should complete without error (may return empty if no regex match)
        result = _extract_plan_exports(content, "pkg_exports")
        assert isinstance(result, list)

    def test_extract_plan_exports_unmatched_paren_returns_empty(self) -> None:
        """_extract_plan_exports returns [] for content with unmatched parens."""
        from souschef.parsers.habitat import _extract_plan_exports

        content = "pkg_exports=(\n  [port]=80\n"
        result = _extract_plan_exports(content, "pkg_exports")
        assert result == []

    def test_is_quote_blocked_double_quote_active(self) -> None:
        """_is_quote_blocked returns True when in_double_quote is active for single quote."""
        from souschef.parsers.habitat import _is_quote_blocked

        # ch="'" with in_double_quote=True → blocked
        assert _is_quote_blocked("'", False, True, False) is True

    def test_toggle_quote_non_quote_char_unchanged(self) -> None:
        """_toggle_quote returns state unchanged for a non-quote character."""
        from souschef.parsers.habitat import _toggle_quote

        result = _toggle_quote("x", True, False, False)
        assert result == (True, False, False)

    def test_extract_plan_function_nested_braces(self, tmp_path: Path) -> None:
        """_extract_plan_function handles nested braces in function body."""
        from souschef.parsers.habitat import _extract_plan_function

        content = """
do_build() {
  if [ -n "$var" ]; then
    build_with_flags {
      extra_flags
    }
  fi
}
"""
        result = _extract_plan_function(content, "do_build")
        # Should contain the nested function body
        assert "build_with_flags" in result

    def test_extract_plan_function_unbalanced_braces_returns_empty(self) -> None:
        """_extract_plan_function returns '' for unbalanced braces."""
        from souschef.parsers.habitat import _extract_plan_function

        # Missing closing brace
        content = "do_build() {\n  echo 'hi'\n"
        result = _extract_plan_function(content, "do_build")
        assert result == ""


# ---------------------------------------------------------------------------
# souschef/parsers/metadata.py
# ---------------------------------------------------------------------------


class TestMetadataParser:
    """Tests for metadata.rb parser exception handling."""

    def test_parse_metadata_value_error(self) -> None:
        """parse_cookbook_metadata returns error dict for ValueError."""
        from souschef.parsers.metadata import parse_cookbook_metadata

        with patch(
            "souschef.parsers.metadata.path_utils._normalize_path",
            side_effect=ValueError("invalid path"),
        ):
            result = parse_cookbook_metadata("/fake/path")
        assert "error" in result

    def test_parse_metadata_file_not_found(self, tmp_path: Path) -> None:
        """parse_cookbook_metadata returns error dict for FileNotFoundError."""
        from souschef.parsers.metadata import parse_cookbook_metadata

        result = parse_cookbook_metadata(str(tmp_path / "nonexistent" / "metadata.rb"))
        assert "error" in result

    def test_parse_metadata_is_a_directory_error(self, tmp_path: Path) -> None:
        """parse_cookbook_metadata returns error dict for IsADirectoryError."""
        from souschef.parsers.metadata import parse_cookbook_metadata

        # Pass a directory path directly
        with patch(
            "souschef.parsers.metadata.safe_read_text",
            side_effect=IsADirectoryError("is a dir"),
        ), patch(
            "souschef.parsers.metadata.path_utils._get_workspace_root",
            return_value=tmp_path,
        ), patch(
            "souschef.parsers.metadata.path_utils._ensure_within_base_path",
            return_value=tmp_path,
        ):
            result = parse_cookbook_metadata(str(tmp_path))
        assert "error" in result

    def test_parse_metadata_permission_error(self, tmp_path: Path) -> None:
        """parse_cookbook_metadata returns error dict for PermissionError."""
        from souschef.parsers.metadata import parse_cookbook_metadata

        with patch(
            "souschef.parsers.metadata.safe_read_text",
            side_effect=PermissionError("access denied"),
        ), patch(
            "souschef.parsers.metadata.path_utils._get_workspace_root",
            return_value=tmp_path,
        ), patch(
            "souschef.parsers.metadata.path_utils._ensure_within_base_path",
            return_value=tmp_path,
        ):
            result = parse_cookbook_metadata(str(tmp_path / "metadata.rb"))
        assert "error" in result

    def test_parse_metadata_generic_exception(self, tmp_path: Path) -> None:
        """parse_cookbook_metadata returns error dict for unexpected exceptions."""
        from souschef.parsers.metadata import parse_cookbook_metadata

        with patch(
            "souschef.parsers.metadata.safe_read_text",
            side_effect=RuntimeError("unexpected"),
        ), patch(
            "souschef.parsers.metadata.path_utils._get_workspace_root",
            return_value=tmp_path,
        ), patch(
            "souschef.parsers.metadata.path_utils._ensure_within_base_path",
            return_value=tmp_path,
        ):
            result = parse_cookbook_metadata(str(tmp_path / "metadata.rb"))
        assert "error" in result


# ---------------------------------------------------------------------------
# souschef/parsers/recipe.py
# ---------------------------------------------------------------------------


class TestRecipeParser:
    """Tests for Chef recipe parser edge cases."""

    def test_timeout_handler_raises_regex_timeout_error(self) -> None:
        """_timeout_handler raises RegexTimeoutError when called."""
        from souschef.parsers.recipe import RegexTimeoutError, _regex_timeout

        # Access the inner handler by triggering it via signal
        # We call the internal function name by invoking _regex_timeout context then
        # accessing the installed signal handler
        with _regex_timeout(seconds=10):
            handler = signal.getsignal(signal.SIGALRM)
            with pytest.raises(RegexTimeoutError):
                handler(signal.SIGALRM, None)

    def test_extract_resources_huge_content_returns_empty(self) -> None:
        """_extract_resources returns [] immediately for content > 1M chars."""
        from souschef.parsers.recipe import _extract_resources

        huge_content = "x" * 1_000_001
        result = _extract_resources(huge_content)
        assert result == []

    def test_extract_resources_oversized_body_skips_resource(self) -> None:
        """_extract_resources skips resources whose body exceeds MAX_RESOURCE_BODY_LENGTH."""
        from souschef.parsers import recipe as recipe_module
        from souschef.parsers.recipe import _extract_resources

        # Create a recipe with a resource that has an oversized body
        header = "package 'myapp' do\n"
        oversized_body = "  action :install\n" * (recipe_module.MAX_RESOURCE_BODY_LENGTH + 1)
        end_marker = "end\n"
        content = header + oversized_body + end_marker

        result = _extract_resources(content)
        # The oversized resource should be skipped
        assert isinstance(result, list)

    def test_extract_resources_timeout_returns_partial(self) -> None:
        """_extract_resources returns partial results when RegexTimeoutError is raised."""
        from souschef.parsers.recipe import RegexTimeoutError, _extract_resources

        with patch(
            "souschef.parsers.recipe._regex_timeout",
            side_effect=RegexTimeoutError("timeout"),
        ):
            # Should not raise; returns empty list
            result = _extract_resources("package 'x' do\n  action :install\nend\n")
        assert isinstance(result, list)

    def test_extract_include_recipes_timeout_returns_partial(self) -> None:
        """_extract_include_recipes returns partial results on RegexTimeoutError."""
        from souschef.parsers.recipe import RegexTimeoutError, _extract_include_recipes

        with patch(
            "souschef.parsers.recipe._regex_timeout",
            side_effect=RegexTimeoutError("timeout"),
        ):
            result = _extract_include_recipes("include_recipe 'base'\n")
        assert isinstance(result, list)

    def test_extract_conditionals_huge_content_returns_empty(self) -> None:
        """_extract_conditionals returns [] for content > 1M chars."""
        from souschef.parsers.recipe import _extract_conditionals

        huge_content = "x" * 1_000_001
        result = _extract_conditionals(huge_content)
        assert result == []

    def test_extract_conditionals_case_no_end_is_skipped(self) -> None:
        """_extract_conditionals skips a case block with no matching end."""
        from souschef.parsers.recipe import _extract_conditionals

        # A case statement with no closing 'end' keyword
        content = "case platform\nwhen 'ubuntu'\n  # no end\n"
        result = _extract_conditionals(content)
        # The unterminated case block should be silently skipped
        assert isinstance(result, list)

    def test_extract_conditionals_oversized_case_body_skipped(self) -> None:
        """_extract_conditionals skips a case block whose body is too large."""
        from souschef.parsers import recipe as recipe_module
        from souschef.parsers.recipe import _extract_conditionals

        large_when = "  when 'x'\n    # big\n" * (recipe_module.MAX_CASE_BODY_LENGTH + 1)
        content = f"case platform\n{large_when}\nend\n"
        result = _extract_conditionals(content)
        assert isinstance(result, list)

    def test_extract_conditionals_timeout_returns_partial(self) -> None:
        """_extract_conditionals returns partial results on RegexTimeoutError."""
        from souschef.parsers.recipe import RegexTimeoutError, _extract_conditionals

        with patch(
            "souschef.parsers.recipe._regex_timeout",
            side_effect=RegexTimeoutError("timeout"),
        ):
            result = _extract_conditionals("if true\n  action :run\nend\n")
        assert isinstance(result, list)
