"""Unit tests for souschef/orchestrators/bash.py."""

from unittest.mock import MagicMock, patch

from souschef.orchestrators.bash import (
    convert_bash_content_to_ansible,
    generate_ansible_role_from_bash,
    parse_bash_script_content,
)


class TestParseBashScriptContent:
    """Tests for parse_bash_script_content."""

    @patch("souschef.orchestrators.bash.bash_parser")
    def test_delegates_to_bash_parser(self, mock_parser: MagicMock) -> None:
        """Test that the call is delegated to the bash parser module."""
        expected = {"commands": ["echo hello"]}
        mock_parser.parse_bash_script_content.return_value = expected

        result = parse_bash_script_content("echo hello")

        mock_parser.parse_bash_script_content.assert_called_once_with("echo hello")
        assert result == expected

    @patch("souschef.orchestrators.bash.bash_parser")
    def test_passes_content_through(self, mock_parser: MagicMock) -> None:
        """Test that content is passed unmodified."""
        content = "#!/bin/bash\napt-get install nginx"
        mock_parser.parse_bash_script_content.return_value = {}

        parse_bash_script_content(content)

        mock_parser.parse_bash_script_content.assert_called_once_with(content)


class TestConvertBashContentToAnsible:
    """Tests for convert_bash_content_to_ansible."""

    @patch("souschef.orchestrators.bash.bash_to_ansible")
    def test_delegates_with_defaults(self, mock_converter: MagicMock) -> None:
        """Test delegation with default script_path."""
        mock_converter.convert_bash_content_to_ansible.return_value = (
            "---\n- hosts: all"
        )

        result = convert_bash_content_to_ansible("echo hello")

        mock_converter.convert_bash_content_to_ansible.assert_called_once_with(
            "echo hello",
            script_path="script.sh",
        )
        assert result == "---\n- hosts: all"

    @patch("souschef.orchestrators.bash.bash_to_ansible")
    def test_passes_custom_script_path(self, mock_converter: MagicMock) -> None:
        """Test that custom script_path is forwarded."""
        mock_converter.convert_bash_content_to_ansible.return_value = "---"

        convert_bash_content_to_ansible("echo hello", script_path="setup.sh")

        mock_converter.convert_bash_content_to_ansible.assert_called_once_with(
            "echo hello",
            script_path="setup.sh",
        )


class TestGenerateAnsibleRoleFromBash:
    """Tests for generate_ansible_role_from_bash."""

    @patch("souschef.orchestrators.bash.bash_to_ansible")
    def test_delegates_with_defaults(self, mock_converter: MagicMock) -> None:
        """Test delegation with default role_name and script_path."""
        mock_converter.generate_ansible_role_from_bash.return_value = "role output"

        result = generate_ansible_role_from_bash("echo hello")

        mock_converter.generate_ansible_role_from_bash.assert_called_once_with(
            "echo hello",
            role_name="bash_converted",
            script_path="script.sh",
        )
        assert result == "role output"

    @patch("souschef.orchestrators.bash.bash_to_ansible")
    def test_passes_custom_params(self, mock_converter: MagicMock) -> None:
        """Test that custom role_name and script_path are forwarded."""
        mock_converter.generate_ansible_role_from_bash.return_value = "custom output"

        generate_ansible_role_from_bash(
            "echo hello",
            role_name="my_role",
            script_path="deploy.sh",
        )

        mock_converter.generate_ansible_role_from_bash.assert_called_once_with(
            "echo hello",
            role_name="my_role",
            script_path="deploy.sh",
        )
