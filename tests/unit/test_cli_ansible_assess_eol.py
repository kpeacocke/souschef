"""Tests for ansible assess and eol command display paths."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from souschef.cli import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


class TestAnsibleAssessDisplayPaths:
    """Test ansible assess display output paths."""

    def test_ansible_assess_with_collections_display(self, runner):
        """Test lines 2089-2095 - collections display."""
        assessment = {
            "current_version": "2.15.0",
            "current_version_full": "ansible [core 2.15.0]",
            "python_version": "3.9.7",
            "installed_collections": [
                "community.general",
                "ansible.posix",
                "community.docker",
            ],
        }

        with (
            patch("souschef.cli._validate_user_path", return_value="/path"),
            patch("souschef.cli.assess_ansible_environment", return_value=assessment),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0
            assert "community.general" in result.output

    def test_ansible_assess_with_many_collections(self, runner):
        """Test lines 2089-2095 - many collections truncation."""
        collections = [f"namespace.collection{i}" for i in range(15)]
        assessment = {
            "current_version": "2.15.0",
            "current_version_full": "ansible [core 2.15.0]",
            "python_version": "3.9.7",
            "installed_collections": collections,
        }

        with (
            patch("souschef.cli._validate_user_path", return_value="/path"),
            patch("souschef.cli.assess_ansible_environment", return_value=assessment),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0
            assert "more" in result.output  # Should show "... and N more"

    def test_ansible_assess_with_eol_date(self, runner):
        """Test lines 2098-2099 - EOL date display."""
        assessment = {
            "current_version": "2.9",
            "current_version_full": "ansible 2.9.27",
            "python_version": "3.6",
            "installed_collections": [],
            "eol_date": "2022-05-23",
        }

        with (
            patch("souschef.cli._validate_user_path", return_value="/path"),
            patch("souschef.cli.assess_ansible_environment", return_value=assessment),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0
            assert "2022-05-23" in result.output

    def test_ansible_assess_with_warnings(self, runner):
        """Test lines 2102-2104 - warnings display."""
        assessment = {
            "current_version": "2.9",
            "current_version_full": "ansible 2.9.27",
            "python_version": "3.6",
            "installed_collections": [],
            "warnings": ["Python 3.6 is EOL", "Ansible 2.9 is EOL"],
        }

        with (
            patch("souschef.cli._validate_user_path", return_value="/path"),
            patch("souschef.cli.assess_ansible_environment", return_value=assessment),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0
            assert "Python 3.6 is EOL" in result.output

    def test_ansible_assess_version_format_error(self, runner):
        """Test line 2116 - version formatting fallback."""
        assessment = {
            "current_version": "invalid-version",
            "current_version_full": "ansible invalid",
            "python_version": "3.9",
            "installed_collections": [],
        }

        with (
            patch("souschef.cli._validate_user_path", return_value="/path"),
            patch("souschef.cli.assess_ansible_environment", return_value=assessment),
            patch("souschef.cli.format_version_display", side_effect=ValueError("Bad")),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0
            assert "invalid-version" in result.output  # Fallback to plain version


class TestAnsibleEolCommandDisplayPaths:
    """Test ansible eol command display paths."""

    def test_ansible_eol_with_eol_version(self, runner):
        """Test lines 2237-2238 - EOL version display."""
        eol_status = {
            "is_eol": True,
            "eol_date": "2022-05-23",
            "support_level": "end-of-life",
        }

        with patch("souschef.cli.get_eol_status", return_value=eol_status):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "2.9"])
            assert result.exit_code == 0
            assert "END OF LIFE" in result.output
            assert "2022-05-23" in result.output

    def test_ansible_eol_with_supported_version(self, runner):
        """Test lines 2252, 2256-2258 - supported version display."""
        eol_status = {
            "is_eol": False,
            "eol_date": "2025-11-01",
            "support_level": "active",
        }

        with patch("souschef.cli.get_eol_status", return_value=eol_status):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "2.17"])
            assert result.exit_code == 0
            assert "SUPPORTED" in result.output
            assert "2025-11-01" in result.output

    def test_ansible_eol_version_format_error(self, runner):
        """Test lines 2245-2247 - version format exception."""
        eol_status = {"is_eol": False, "eol_date": "2025-11-01"}

        with (
            patch("souschef.cli.get_eol_status", return_value=eol_status),
            patch(
                "souschef.cli.format_version_display", side_effect=KeyError("Unknown")
            ),
        ):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "99.99"])
            assert result.exit_code == 0
            # Should fall back to plain version
            assert "99.99" in result.output


class TestAnsiblePlanRemainingPaths:
    """Test remaining ansible plan display paths."""

    def test_ansible_plan_with_phases(self, runner):
        """Test lines 2286, 2290, 2294 - phases display."""
        from souschef import ansible_upgrade

        mock_plan = {
            "upgrade_path": {
                "from_version": "2.9",
                "to_version": "2.17",
                "intermediate_versions": ["2.10", "2.15"],
                "breaking_changes": [],
                "collection_updates_needed": {},
                "estimated_effort_days": 15,
                "phases": [
                    {
                        "phase": 1,
                        "target_version": "2.10",
                        "description": "Minor upgrade",
                        "effort_days": 5,
                    },
                    {
                        "phase": 2,
                        "target_version": "2.15",
                        "description": "Intermediate upgrade",
                        "effort_days": 5,
                    },
                    {
                        "phase": 3,
                        "target_version": "2.17",
                        "description": "Final upgrade",
                        "effort_days": 5,
                    },
                ],
            },
            "pre_upgrade_checklist": [],
            "upgrade_steps": [],
            "testing_plan": {},
            "post_upgrade_validation": [],
            "rollback_plan": {},
            "estimated_downtime_hours": 3.0,
            "risk_assessment": {},
        }

        with patch.object(
            ansible_upgrade, "generate_upgrade_plan", return_value=mock_plan
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "plan",
                    "--current-version",
                    "2.9",
                    "--target-version",
                    "2.17",
                ],
            )
            assert result.exit_code == 0
