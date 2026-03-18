"""Unit tests for souschef/orchestrators/salt.py."""

import json
from unittest.mock import MagicMock, patch


class TestParseSaltSls:
    """Tests for parse_salt_sls."""

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_delegates_correctly(self, mock_parser: MagicMock) -> None:
        """Test delegation to salt parser module."""
        mock_parser.parse_salt_sls.return_value = "parsed sls"

        from souschef.orchestrators.salt import parse_salt_sls

        result = parse_salt_sls("/path/to/state.sls")

        mock_parser.parse_salt_sls.assert_called_once_with("/path/to/state.sls")
        assert result == "parsed sls"


class TestConvertSaltSlsToAnsible:
    """Tests for convert_salt_sls_to_ansible."""

    @patch("souschef.orchestrators.salt.salt_converter")
    def test_delegates_with_defaults(self, mock_converter: MagicMock) -> None:
        """Test delegation with default playbook_name."""
        mock_converter.convert_salt_sls_to_ansible.return_value = "---"

        from souschef.orchestrators.salt import convert_salt_sls_to_ansible

        result = convert_salt_sls_to_ansible("/path/to/state.sls")

        mock_converter.convert_salt_sls_to_ansible.assert_called_once_with(
            "/path/to/state.sls",
            "salt_migration",
        )
        assert result == "---"

    @patch("souschef.orchestrators.salt.salt_converter")
    def test_passes_custom_playbook_name(self, mock_converter: MagicMock) -> None:
        """Test that custom playbook_name is forwarded."""
        mock_converter.convert_salt_sls_to_ansible.return_value = "---"

        from souschef.orchestrators.salt import convert_salt_sls_to_ansible

        convert_salt_sls_to_ansible("/path/to/state.sls", playbook_name="my_playbook")

        mock_converter.convert_salt_sls_to_ansible.assert_called_once_with(
            "/path/to/state.sls",
            "my_playbook",
        )


class TestParseSaltPillar:
    """Tests for parse_salt_pillar."""

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_delegates_correctly(self, mock_parser: MagicMock) -> None:
        """Test delegation to salt parser module."""
        mock_parser.parse_salt_pillar.return_value = "parsed pillar"

        from souschef.orchestrators.salt import parse_salt_pillar

        result = parse_salt_pillar("/path/to/pillar.sls")

        mock_parser.parse_salt_pillar.assert_called_once_with("/path/to/pillar.sls")
        assert result == "parsed pillar"


class TestParseSaltDirectory:
    """Tests for parse_salt_directory."""

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_delegates_correctly(self, mock_parser: MagicMock) -> None:
        """Test delegation to salt parser module."""
        mock_parser.parse_salt_directory.return_value = "parsed directory"

        from souschef.orchestrators.salt import parse_salt_directory

        result = parse_salt_directory("/path/to/salt")

        mock_parser.parse_salt_directory.assert_called_once_with("/path/to/salt")
        assert result == "parsed directory"


class TestAssessSaltComplexity:
    """Tests for assess_salt_complexity."""

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_delegates_correctly(self, mock_parser: MagicMock) -> None:
        """Test delegation to salt parser module."""
        mock_parser.assess_salt_complexity.return_value = '{"complexity_level": "low"}'

        from souschef.orchestrators.salt import assess_salt_complexity

        result = assess_salt_complexity("/path/to/salt")

        mock_parser.assess_salt_complexity.assert_called_once_with("/path/to/salt")
        assert result == '{"complexity_level": "low"}'


class TestConvertSaltDirectoryToRoles:
    """Tests for convert_salt_directory_to_roles."""

    @patch("souschef.orchestrators.salt.salt_converter")
    def test_delegates_correctly(self, mock_converter: MagicMock) -> None:
        """Test delegation to salt converter module."""
        mock_converter.convert_salt_directory_to_roles.return_value = "roles created"

        from souschef.orchestrators.salt import convert_salt_directory_to_roles

        result = convert_salt_directory_to_roles("/salt/dir", "/output/dir")

        mock_converter.convert_salt_directory_to_roles.assert_called_once_with(
            "/salt/dir",
            "/output/dir",
        )
        assert result == "roles created"


class TestPlanSaltMigration:
    """Tests for plan_salt_migration (contains logic — test branches)."""

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_returns_plan_for_valid_complexity_data(
        self, mock_parser: MagicMock
    ) -> None:
        """Test plan generation with valid parsed complexity JSON."""
        complexity_data = {
            "summary": {
                "complexity_level": "medium",
                "total_files": 10,
                "total_states": 50,
                "estimated_effort_days": 5,
                "estimated_effort_days_with_souschef": 2,
                "high_complexity_files": ["file1.sls"],
                "module_breakdown": {"pkg.installed": 20, "service.running": 15},
            }
        }
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir")

        assert "SaltStack to Ansible Migration Plan" in result
        assert "MEDIUM" in result
        assert "10" in result
        assert "50" in result

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_returns_error_when_complexity_has_error_key(
        self, mock_parser: MagicMock
    ) -> None:
        """Test that error in complexity data surfaces an error string."""
        complexity_data = {"error": "Salt directory not found"}
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir")

        assert result == "Salt directory not found"

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_returns_raw_json_on_decode_error(self, mock_parser: MagicMock) -> None:
        """Test that invalid JSON is returned as-is."""
        mock_parser.assess_salt_complexity.return_value = "not valid json"

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir")

        assert result == "not valid json"

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_generates_aap_platform_guidance(self, mock_parser: MagicMock) -> None:
        """Test AAP platform guidance is included in plan."""
        complexity_data = {"summary": {"complexity_level": "low"}}
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir", target_platform="aap")

        assert "Ansible Automation Platform (AAP)" in result

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_generates_awx_platform_guidance(self, mock_parser: MagicMock) -> None:
        """Test AWX platform guidance is included in plan."""
        complexity_data = {"summary": {"complexity_level": "low"}}
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir", target_platform="awx")

        assert "AWX (Open Source)" in result

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_generates_ansible_core_platform_guidance(
        self, mock_parser: MagicMock
    ) -> None:
        """Test Ansible Core platform guidance is included in plan."""
        complexity_data = {"summary": {"complexity_level": "low"}}
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir", target_platform="ansible_core")

        assert "Ansible Core (CLI)" in result

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_generates_unknown_platform_guidance(self, mock_parser: MagicMock) -> None:
        """Test unknown target_platform falls back to generic guidance."""
        complexity_data = {"summary": {"complexity_level": "low"}}
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir", target_platform="custom_platform")

        assert "custom_platform" in result

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_custom_timeline_weeks(self, mock_parser: MagicMock) -> None:
        """Test that custom timeline_weeks affects phase calculation."""
        complexity_data = {"summary": {"complexity_level": "high"}}
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir", timeline_weeks=4)

        assert "4 weeks" in result

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_no_modules_detected_message(self, mock_parser: MagicMock) -> None:
        """Test fallback message when module_breakdown is empty."""
        complexity_data = {"summary": {"module_breakdown": {}}}
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir")

        assert "No modules detected" in result

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_no_high_complexity_files_message(self, mock_parser: MagicMock) -> None:
        """Test fallback message when high_complexity_files is empty."""
        complexity_data = {"summary": {"high_complexity_files": []}}
        mock_parser.assess_salt_complexity.return_value = json.dumps(complexity_data)

        from souschef.orchestrators.salt import plan_salt_migration

        result = plan_salt_migration("/salt/dir")

        assert "None identified" in result


class TestGenerateSaltInventory:
    """Tests for generate_salt_inventory (contains logic — test branches)."""

    @patch("souschef.orchestrators.salt.salt_converter")
    @patch("souschef.orchestrators.salt.salt_parser")
    def test_returns_inventory_for_valid_top(
        self,
        mock_parser: MagicMock,
        mock_converter: MagicMock,
    ) -> None:
        """Test inventory generation with valid top.sls data."""
        top_data = {"environments": {"base": {"*": ["webserver", "common"]}}}
        mock_parser.parse_salt_top.return_value = json.dumps(top_data)
        mock_converter._top_to_ansible_inventory.return_value = (
            "[base]\nwebserver1\nwebserver2\n"
        )

        from souschef.orchestrators.salt import generate_salt_inventory

        result_str = generate_salt_inventory("/path/to/top.sls")
        result = json.loads(result_str)

        assert "inventory" in result
        assert "groups" in result
        assert "hosts" in result

    @patch("souschef.orchestrators.salt.salt_parser")
    def test_returns_error_on_json_decode_error(self, mock_parser: MagicMock) -> None:
        """Test that invalid JSON from parse_salt_top returns an error."""
        mock_parser.parse_salt_top.return_value = "not valid json"

        from souschef.orchestrators.salt import generate_salt_inventory

        result_str = generate_salt_inventory("/path/to/top.sls")
        result = json.loads(result_str)

        assert "error" in result

    @patch("souschef.orchestrators.salt.salt_converter")
    @patch("souschef.orchestrators.salt.salt_parser")
    def test_returns_error_when_top_json_has_error(
        self,
        mock_parser: MagicMock,
        mock_converter: MagicMock,
    ) -> None:
        """Test that error string in top_json returns an error JSON."""
        # The raw JSON does NOT contain "environments" — triggers error path
        mock_parser.parse_salt_top.return_value = "Error: file not found"

        from souschef.orchestrators.salt import generate_salt_inventory

        result_str = generate_salt_inventory("/path/to/top.sls")
        result = json.loads(result_str)

        assert "error" in result
