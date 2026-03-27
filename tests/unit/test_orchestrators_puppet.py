"""Unit tests for souschef/orchestrators/puppet.py."""

from unittest.mock import MagicMock, patch


class TestParsePuppetManifest:
    """Tests for parse_puppet_manifest."""

    @patch("souschef.orchestrators.puppet.puppet_parser")
    def test_delegates_correctly(self, mock_parser: MagicMock) -> None:
        """Test delegation to puppet parser module."""
        mock_parser.parse_puppet_manifest.return_value = "parsed manifest"

        from souschef.orchestrators.puppet import parse_puppet_manifest

        result = parse_puppet_manifest("/path/to/manifest.pp")

        mock_parser.parse_puppet_manifest.assert_called_once_with(
            "/path/to/manifest.pp"
        )
        assert result == "parsed manifest"


class TestParsePuppetModule:
    """Tests for parse_puppet_module."""

    @patch("souschef.orchestrators.puppet.puppet_parser")
    def test_delegates_correctly(self, mock_parser: MagicMock) -> None:
        """Test delegation to puppet parser module."""
        mock_parser.parse_puppet_module.return_value = "parsed module"

        from souschef.orchestrators.puppet import parse_puppet_module

        result = parse_puppet_module("/path/to/module")

        mock_parser.parse_puppet_module.assert_called_once_with("/path/to/module")
        assert result == "parsed module"


class TestConvertPuppetManifestToAnsible:
    """Tests for convert_puppet_manifest_to_ansible."""

    @patch("souschef.orchestrators.puppet.puppet_to_ansible")
    def test_delegates_correctly(self, mock_converter: MagicMock) -> None:
        """Test delegation to puppet_to_ansible converter."""
        mock_converter.convert_puppet_manifest_to_ansible.return_value = (
            "---\n- hosts: all"
        )

        from souschef.orchestrators.puppet import convert_puppet_manifest_to_ansible

        result = convert_puppet_manifest_to_ansible("/path/to/manifest.pp")

        mock_converter.convert_puppet_manifest_to_ansible.assert_called_once_with(
            "/path/to/manifest.pp"
        )
        assert result == "---\n- hosts: all"


class TestConvertPuppetModuleToAnsible:
    """Tests for convert_puppet_module_to_ansible."""

    @patch("souschef.orchestrators.puppet.puppet_to_ansible")
    def test_delegates_correctly(self, mock_converter: MagicMock) -> None:
        """Test delegation to puppet_to_ansible converter."""
        mock_converter.convert_puppet_module_to_ansible.return_value = (
            "---\n- hosts: all"
        )

        from souschef.orchestrators.puppet import convert_puppet_module_to_ansible

        result = convert_puppet_module_to_ansible("/path/to/module")

        mock_converter.convert_puppet_module_to_ansible.assert_called_once_with(
            "/path/to/module"
        )
        assert result == "---\n- hosts: all"


class TestConvertPuppetManifestToAnsibleWithAi:
    """Tests for convert_puppet_manifest_to_ansible_with_ai."""

    @patch("souschef.orchestrators.puppet.puppet_to_ansible")
    def test_delegates_with_defaults(self, mock_converter: MagicMock) -> None:
        """Test delegation with default AI parameters."""
        mock_converter.convert_puppet_manifest_to_ansible_with_ai.return_value = "---"

        from souschef.orchestrators.puppet import (
            convert_puppet_manifest_to_ansible_with_ai,
        )

        result = convert_puppet_manifest_to_ansible_with_ai("/path/to/manifest.pp")

        mock_converter.convert_puppet_manifest_to_ansible_with_ai.assert_called_once_with(
            "/path/to/manifest.pp",
            ai_provider="anthropic",
            api_key="",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
            max_tokens=4000,
            project_id="",
            base_url="",
        )
        assert result == "---"

    @patch("souschef.orchestrators.puppet.puppet_to_ansible")
    def test_passes_custom_ai_params(self, mock_converter: MagicMock) -> None:
        """Test that custom AI parameters are forwarded."""
        mock_converter.convert_puppet_manifest_to_ansible_with_ai.return_value = "---"

        from souschef.orchestrators.puppet import (
            convert_puppet_manifest_to_ansible_with_ai,
        )

        convert_puppet_manifest_to_ansible_with_ai(
            "/path/to/manifest.pp",
            ai_provider="openai",
            api_key="sk-key",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000,
            project_id="proj1",
            base_url="https://api.example.com",
        )

        mock_converter.convert_puppet_manifest_to_ansible_with_ai.assert_called_once_with(
            "/path/to/manifest.pp",
            ai_provider="openai",
            api_key="sk-key",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000,
            project_id="proj1",
            base_url="https://api.example.com",
        )


class TestConvertPuppetModuleToAnsibleWithAi:
    """Tests for convert_puppet_module_to_ansible_with_ai."""

    @patch("souschef.orchestrators.puppet.puppet_to_ansible")
    def test_delegates_with_defaults(self, mock_converter: MagicMock) -> None:
        """Test delegation with default AI parameters."""
        mock_converter.convert_puppet_module_to_ansible_with_ai.return_value = "---"

        from souschef.orchestrators.puppet import (
            convert_puppet_module_to_ansible_with_ai,
        )

        result = convert_puppet_module_to_ansible_with_ai("/path/to/module")

        mock_converter.convert_puppet_module_to_ansible_with_ai.assert_called_once_with(
            "/path/to/module",
            ai_provider="anthropic",
            api_key="",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
            max_tokens=4000,
            project_id="",
            base_url="",
        )
        assert result == "---"

    @patch("souschef.orchestrators.puppet.puppet_to_ansible")
    def test_passes_custom_ai_params(self, mock_converter: MagicMock) -> None:
        """Test that custom AI parameters are forwarded."""
        mock_converter.convert_puppet_module_to_ansible_with_ai.return_value = "---"

        from souschef.orchestrators.puppet import (
            convert_puppet_module_to_ansible_with_ai,
        )

        convert_puppet_module_to_ansible_with_ai(
            "/path/to/module",
            ai_provider="openai",
            api_key="sk-key",
            model="gpt-4",
            temperature=0.1,
            max_tokens=1000,
            project_id="proj2",
            base_url="https://custom.api.com",
        )

        mock_converter.convert_puppet_module_to_ansible_with_ai.assert_called_once_with(
            "/path/to/module",
            ai_provider="openai",
            api_key="sk-key",
            model="gpt-4",
            temperature=0.1,
            max_tokens=1000,
            project_id="proj2",
            base_url="https://custom.api.com",
        )


class TestGetPuppetAnsibleModuleMap:
    """Tests for get_puppet_ansible_module_map."""

    @patch("souschef.orchestrators.puppet.puppet_to_ansible")
    def test_delegates_correctly(self, mock_converter: MagicMock) -> None:
        """Test delegation to puppet_to_ansible converter."""
        expected = {
            "package": "ansible.builtin.package",
            "service": "ansible.builtin.service",
        }
        mock_converter.get_puppet_ansible_module_map.return_value = expected

        from souschef.orchestrators.puppet import get_puppet_ansible_module_map

        result = get_puppet_ansible_module_map()

        mock_converter.get_puppet_ansible_module_map.assert_called_once_with()
        assert result == expected
