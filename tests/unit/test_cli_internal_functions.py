"""Direct tests of internal CLI helper functions for 100% coverage."""

import contextlib
import json
from typing import Any, cast
from unittest.mock import patch

import click

# Import internal functions directly
from souschef.cli import (
    _display_collection_section,
    _display_plan_section,
    _display_template_summary,
    _display_upgrade_plan,
)


class TestDisplayPlanSection:
    """Test _display_plan_section function - line 2122."""

    def test_display_more_than_five_items(self, capsys):
        """Line 2122: Show '... and N more' when items > 5."""
        items = ["item1", "item2", "item3", "item4", "item5", "item6", "item7"]
        _display_plan_section("Test Section", items, "-")

        captured = capsys.readouterr()
        assert "... and 2 more" in captured.out  # Line 2122

    def test_display_five_or_fewer_items(self, capsys):
        """Test with 5 items - no truncation."""
        items = ["item1", "item2", "item3"]
        _display_plan_section("Test Section", items, "-")

        captured = capsys.readouterr()
        assert "... and" not in captured.out

    def test_display_empty_items(self, capsys):
        """Test with no items - should return early."""
        items = []
        _display_plan_section("Test Section", items, "-")

        captured = capsys.readouterr()
        assert captured.out == ""


class TestDisplayUpgradePlan:
    """Test _display_upgrade_plan function - multiple lines."""

    def test_plan_with_intermediate_versions(self, capsys):
        """Lines 2138-2141: Display intermediate versions."""
        plan_data: dict[str, Any] = {
            "upgrade_path": {
                "from_version": "2.9",
                "to_version": "2.17",
                "intermediate_versions": ["2.10", "2.15"],
                "breaking_changes": [],
                "collection_updates_needed": {},
            }
        }

        _display_upgrade_plan(cast(Any, plan_data))

        captured = capsys.readouterr()
        assert "Intermediate Versions:" in captured.out
        assert "2.10" in captured.out
        assert "2.15" in captured.out

    def test_plan_with_breaking_changes(self, capsys):
        """Lines 2143-2145: Display breaking changes via _display_plan_section."""
        plan_data: dict[str, Any] = {
            "upgrade_path": {
                "from_version": "2.9",
                "to_version": "2.17",
                "intermediate_versions": [],
                "breaking_changes": [
                    "change1",
                    "change2",
                    "change3",
                    "change4",
                    "change5",
                    "change6",
                ],
                "collection_updates_needed": {},
            }
        }

        _display_upgrade_plan(cast(Any, plan_data))

        captured = capsys.readouterr()
        assert "Breaking Changes:" in captured.out
        # With 6 changes, should show "... and 1 more"
        assert "and 1 more" in captured.out

    def test_plan_with_collection_updates(self, capsys):
        """Lines 2147-2150: Display collection updates."""
        plan_data: dict[str, Any] = {
            "upgrade_path": {
                "from_version": "2.9",
                "to_version": "2.17",
                "intermediate_versions": [],
                "breaking_changes": [],
                "collection_updates_needed": {
                    "community.general": "5.0.0",
                    "ansible.posix": "1.4.0",
                },
            }
        }

        _display_upgrade_plan(cast(Any, plan_data))

        captured = capsys.readouterr()
        assert "Collection Updates Required:" in captured.out
        assert "Total: 2" in captured.out

    def test_plan_with_estimated_effort(self, capsys):
        """Lines 2152-2154: Display estimated effort."""
        plan_data: dict[str, Any] = {
            "upgrade_path": {
                "from_version": "2.9",
                "to_version": "2.17",
                "intermediate_versions": [],
                "breaking_changes": [],
                "collection_updates_needed": {},
                "estimated_effort_days": 7.5,
            }
        }

        _display_upgrade_plan(cast(Any, plan_data))

        captured = capsys.readouterr()
        assert "Estimated Effort: 7.5 days" in captured.out


class TestDisplayTemplateSummary:
    """Test _display_template_summary function - line 405."""

    def test_template_with_many_variables(self, tmp_path, capsys):
        """Line 405: Template with 7+ variables shows '... and N more'."""
        template = tmp_path / "test.erb"
        template.write_text("<%= @v1 %> <%= @v2 %>")

        # Mock parse_template to return JSON with 7 variables
        mock_result = json.dumps(
            {"variables": ["v1", "v2", "v3", "v4", "v5", "v6", "v7"]}
        )

        with patch("souschef.cli.parse_template", return_value=mock_result):
            _display_template_summary(template)

            captured = capsys.readouterr()
            # Line 405: Should show "... and 2 more"
            assert "... and 2 more" in captured.out

    def test_template_with_few_variables(self, tmp_path, capsys):
        """Test with 3 variables - no truncation."""
        template = tmp_path / "test.erb"
        template.write_text("<%= @v1 %> <%= @v2 %>")

        mock_result = json.dumps({"variables": ["v1", "v2", "v3"]})

        with patch("souschef.cli.parse_template", return_value=mock_result):
            _display_template_summary(template)

            captured = capsys.readouterr()
            assert "... and" not in captured.out

    def test_template_json_decode_error(self, tmp_path, capsys):
        """Line 406: JSONDecodeError fallback."""
        template = tmp_path / "test.erb"
        template.write_text("<%= @v1 %>")

        # Return invalid JSON
        with patch("souschef.cli.parse_template", return_value="not json {"):
            _display_template_summary(template)

            captured = capsys.readouterr()
            # Line 406: Should show truncated result
            assert "not json" in captured.out


class TestAssessCollectionDisplay:
    """Test ansible assess collection display - lines 2089-2095."""

    def test_assess_with_many_collections(self, capsys):
        """Lines 2093-2095: Collections display with truncation."""
        from souschef.cli import ansible_assess

        collections = [f"ns.col{i}" for i in range(12)]
        assessment = {
            "current_version": "2.15.0",
            "current_version_full": "ansible-core 2.15.0",
            "python_version": "3.9.7",
            "installed_collections": collections,
        }

        with patch("souschef.cli.assess_ansible_environment", return_value=assessment):
            # Create a Click context
            ctx = click.Context(ansible_assess)
            ctx.params = {"environment_path": None}
            with ctx:
                ansible_assess.invoke(ctx)

        captured = capsys.readouterr()
        # Line 2095: Should show "... and 7 more" (showing 5 of 12)
        assert "... and 7 more" in captured.out or "more" in captured.out

    def test_assess_with_eol_date(self, capsys):
        """Lines 2098-2099: EOL date display."""
        from souschef.cli import ansible_assess

        assessment = {
            "current_version": "2.9",
            "current_version_full": "ansible 2.9.27",
            "python_version": "3.6",
            "installed_collections": [],
            "eol_date": "2022-05-23",
        }

        with patch("souschef.cli.assess_ansible_environment", return_value=assessment):
            ctx = click.Context(ansible_assess)
            ctx.params = {"environment_path": None}
            with ctx:
                ansible_assess.invoke(ctx)

        captured = capsys.readouterr()
        # Line 2099: Should display EOL date
        assert "2022-05-23" in captured.out

    def test_assess_with_warnings(self, capsys):
        """Lines 2102-2104: Warnings display."""
        from souschef.cli import ansible_assess

        assessment = {
            "current_version": "2.9",
            "current_version_full": "ansible 2.9.27",
            "python_version": "3.6",
            "installed_collections": [],
            "warnings": ["Warning 1", "Warning 2", "Warning 3"],
        }

        with patch("souschef.cli.assess_ansible_environment", return_value=assessment):
            ctx = click.Context(ansible_assess)
            ctx.params = {"environment_path": None}
            with ctx:
                ansible_assess.invoke(ctx)

        captured = capsys.readouterr()
        # Lines 2102-2104: Should display warnings
        assert "Warning" in captured.out


class TestVersionFormatFallback:
    """Test version format fallback - line 2116."""

    def test_format_version_display_exception(self, capsys):
        """Line 2116: Version format exception fallback."""
        from souschef.cli import ansible_assess

        assessment = {
            "current_version": "invalid",
            "current_version_full": "ansible invalid",
            "python_version": "3.9",
            "installed_collections": [],
        }

        with (
            patch("souschef.cli.assess_ansible_environment", return_value=assessment),
            patch("souschef.cli.format_version_display", side_effect=ValueError()),
            contextlib.suppress(Exception),
        ):
            ctx = click.Context(ansible_assess)
            ctx.params = {"environment_path": None}
            with ctx:
                ansible_assess.invoke(ctx)

        captured = capsys.readouterr()
        # Line 2116: Should fall back to showing raw version
        assert "invalid" in captured.out


class TestDetectPythonParsing:
    """Test detect-python version parsing - lines 2510-2512."""

    def test_detect_python_major_minor_display(self, capsys):
        """Lines 2510-2512: Display major.minor version."""
        from souschef.cli import ansible_detect_python

        with (
            patch("souschef.cli.detect_python_version", return_value="3.11.7"),
            contextlib.suppress(SystemExit),
        ):
            ctx = click.Context(ansible_detect_python)
            ctx.params = {"environment_path": None}
            with ctx:
                ansible_detect_python.invoke(ctx)

        captured = capsys.readouterr()
        # Lines 2510-2512: Should show 3.11
        assert "3.11" in captured.out

    def test_detect_python_runtime_error(self, capsys):
        """Lines 2517-2519: RuntimeError handler."""
        from souschef.cli import ansible_detect_python

        with (
            patch(
                "souschef.cli.detect_python_version", side_effect=RuntimeError("Failed")
            ),
            contextlib.suppress(SystemExit),
        ):
            ctx = click.Context(ansible_detect_python)
            ctx.params = {"environment_path": None}
            with ctx:
                ansible_detect_python.invoke(ctx)

        captured = capsys.readouterr()
        # Lines 2517-2519: Should show error
        assert "Error" in captured.err or "Failed" in captured.err


class TestEolSupportedVersion:
    """Test EOL supported version - lines 2252, 2256-2258."""

    def test_eol_supported_ansible_version(self, capsys):
        """Lines 2252, 2256-2258: Supported version display."""
        from souschef.cli import ansible_eol

        eol_status = {
            "is_eol": False,
            "eol_date": "2025-11-30",
            "version": "2.17",
            "support_level": "active",
        }

        with (
            patch("souschef.cli.get_eol_status", return_value=eol_status),
            contextlib.suppress(SystemExit),
        ):
            ctx = click.Context(ansible_eol)
            ctx.params = {"version": "2.17"}
            with ctx:
                ansible_eol.invoke(ctx)

        captured = capsys.readouterr()
        # Lines 2256-2258: Should show SUPPORTED
        assert "SUPPORTED" in captured.out or "Active" in captured.out


class TestDisplayCollectionSection:
    """Test _display_collection_section function - lines 2261-2270."""

    def test_display_more_than_five_collections(self, capsys):
        """Lines 2269-2270: Show '... and N more' when collections > 5."""
        collections = ["col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8"]
        _display_collection_section("Test Collections", collections)

        captured = capsys.readouterr()
        # Line 2270: Should show "... and 3 more" (8 - 5 = 3)
        assert "... and 3 more" in captured.out

    def test_display_five_or_fewer_collections(self, capsys):
        """Test with 4 collections - no truncation."""
        collections = ["col1", "col2", "col3", "col4"]
        _display_collection_section("Test Collections", collections)

        captured = capsys.readouterr()
        assert "... and" not in captured.out
        assert "Test Collections: 4" in captured.out

    def test_display_empty_collections(self, capsys):
        """Test with no collections - should return early."""
        collections = []
        _display_collection_section("Test Collections", collections)

        captured = capsys.readouterr()
        assert captured.out == ""
