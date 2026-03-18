"""Unit tests for souschef/orchestrators/powershell.py."""

from unittest.mock import MagicMock, patch


class TestParsePowershellContent:
    """Tests for parse_powershell_content."""

    @patch("souschef.orchestrators.powershell.powershell_parser")
    def test_delegates_with_defaults(self, mock_parser: MagicMock) -> None:
        """Test delegation with default source."""
        mock_parser.parse_powershell_content.return_value = "parsed output"

        from souschef.orchestrators.powershell import parse_powershell_content

        result = parse_powershell_content("Write-Host 'hello'")

        mock_parser.parse_powershell_content.assert_called_once_with(
            "Write-Host 'hello'",
            "<inline>",
        )
        assert result == "parsed output"

    @patch("souschef.orchestrators.powershell.powershell_parser")
    def test_passes_custom_source(self, mock_parser: MagicMock) -> None:
        """Test that custom source is forwarded."""
        mock_parser.parse_powershell_content.return_value = ""

        from souschef.orchestrators.powershell import parse_powershell_content

        parse_powershell_content("Write-Host 'hello'", source="deploy.ps1")

        mock_parser.parse_powershell_content.assert_called_once_with(
            "Write-Host 'hello'",
            "deploy.ps1",
        )


class TestConvertPowershellContentToAnsible:
    """Tests for convert_powershell_content_to_ansible."""

    @patch("souschef.orchestrators.powershell.powershell_converter")
    def test_delegates_with_defaults(self, mock_converter: MagicMock) -> None:
        """Test delegation with default parameters."""
        mock_converter.convert_powershell_content_to_ansible.return_value = "---"

        from souschef.orchestrators.powershell import (
            convert_powershell_content_to_ansible,
        )

        result = convert_powershell_content_to_ansible("Write-Host 'hello'")

        mock_converter.convert_powershell_content_to_ansible.assert_called_once_with(
            "Write-Host 'hello'",
            playbook_name="powershell_migration",
            hosts="windows",
            source="<inline>",
        )
        assert result == "---"

    @patch("souschef.orchestrators.powershell.powershell_converter")
    def test_passes_custom_params(self, mock_converter: MagicMock) -> None:
        """Test that custom parameters are forwarded."""
        mock_converter.convert_powershell_content_to_ansible.return_value = "---"

        from souschef.orchestrators.powershell import (
            convert_powershell_content_to_ansible,
        )

        convert_powershell_content_to_ansible(
            "Write-Host 'hello'",
            playbook_name="my_playbook",
            hosts="win_servers",
            source="script.ps1",
        )

        mock_converter.convert_powershell_content_to_ansible.assert_called_once_with(
            "Write-Host 'hello'",
            playbook_name="my_playbook",
            hosts="win_servers",
            source="script.ps1",
        )


class TestAnalyzePowershellMigrationFidelity:
    """Tests for analyze_powershell_migration_fidelity."""

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_delegates_correctly(self, mock_generators: MagicMock) -> None:
        """Test delegation to generators module."""
        mock_generators.analyze_powershell_migration_fidelity.return_value = (
            "fidelity report"
        )
        parsed_ir = {"actions": []}

        from souschef.orchestrators.powershell import (
            analyze_powershell_migration_fidelity,
        )

        result = analyze_powershell_migration_fidelity(parsed_ir)

        mock_generators.analyze_powershell_migration_fidelity.assert_called_once_with(
            parsed_ir
        )
        assert result == "fidelity report"


class TestGenerateWindowsInventory:
    """Tests for generate_windows_inventory."""

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_delegates_with_hardcoded_defaults(
        self, mock_generators: MagicMock
    ) -> None:
        """Test that hardcoded defaults are passed to generator regardless of args."""
        mock_generators.generate_windows_inventory.return_value = "[windows]\nhost1"

        from souschef.orchestrators.powershell import generate_windows_inventory

        result = generate_windows_inventory()

        mock_generators.generate_windows_inventory.assert_called_once_with(
            hosts=None,
            winrm_port=5986,
            use_ssl=True,
            validate_certs=False,
            winrm_transport="ntlm",
        )
        assert result == "[windows]\nhost1"

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_ignores_passed_args(self, mock_generators: MagicMock) -> None:
        """Test that args are ignored in favour of hardcoded defaults."""
        mock_generators.generate_windows_inventory.return_value = ""

        from souschef.orchestrators.powershell import generate_windows_inventory

        # Even when args are passed, the function uses hardcoded defaults
        generate_windows_inventory("ignored_arg", key="ignored_kwarg")

        mock_generators.generate_windows_inventory.assert_called_once_with(
            hosts=None,
            winrm_port=5986,
            use_ssl=True,
            validate_certs=False,
            winrm_transport="ntlm",
        )


class TestGenerateWindowsGroupVars:
    """Tests for generate_windows_group_vars."""

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_delegates_with_defaults(self, mock_generators: MagicMock) -> None:
        """Test delegation with default parameters."""
        mock_generators.generate_windows_group_vars.return_value = "group_vars content"

        from souschef.orchestrators.powershell import generate_windows_group_vars

        result = generate_windows_group_vars()

        mock_generators.generate_windows_group_vars.assert_called_once_with(
            ansible_user="Administrator",
            winrm_port=5986,
            use_ssl=True,
            validate_certs=False,
            winrm_transport="ntlm",
        )
        assert result == "group_vars content"

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_passes_custom_params(self, mock_generators: MagicMock) -> None:
        """Test that custom parameters are forwarded."""
        mock_generators.generate_windows_group_vars.return_value = ""

        from souschef.orchestrators.powershell import generate_windows_group_vars

        generate_windows_group_vars(
            ansible_user="admin",
            winrm_port=5985,
            use_ssl=False,
            validate_certs=True,
            winrm_transport="kerberos",
        )

        mock_generators.generate_windows_group_vars.assert_called_once_with(
            ansible_user="admin",
            winrm_port=5985,
            use_ssl=False,
            validate_certs=True,
            winrm_transport="kerberos",
        )


class TestGenerateAnsibleRequirements:
    """Tests for generate_ansible_requirements."""

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_delegates_with_none(self, mock_generators: MagicMock) -> None:
        """Test delegation with default None parsed_ir."""
        mock_generators.generate_ansible_requirements.return_value = (
            "requirements content"
        )

        from souschef.orchestrators.powershell import generate_ansible_requirements

        result = generate_ansible_requirements()

        mock_generators.generate_ansible_requirements.assert_called_once_with(None)
        assert result == "requirements content"

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_passes_parsed_ir(self, mock_generators: MagicMock) -> None:
        """Test that parsed_ir is forwarded."""
        mock_generators.generate_ansible_requirements.return_value = ""
        parsed_ir = {"collections": ["ansible.windows"]}

        from souschef.orchestrators.powershell import generate_ansible_requirements

        generate_ansible_requirements(parsed_ir)

        mock_generators.generate_ansible_requirements.assert_called_once_with(parsed_ir)


class TestGeneratePowershellRoleStructure:
    """Tests for generate_powershell_role_structure."""

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_delegates_with_defaults(self, mock_generators: MagicMock) -> None:
        """Test delegation with default parameters."""
        expected = {"tasks/main.yml": "---"}
        mock_generators.generate_powershell_role_structure.return_value = expected
        parsed_ir: dict[str, object] = {"actions": []}

        from souschef.orchestrators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(parsed_ir)

        mock_generators.generate_powershell_role_structure.assert_called_once_with(
            parsed_ir,
            role_name="windows_provisioning",
            playbook_name="site",
            hosts="windows",
        )
        assert result == expected

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_passes_custom_params(self, mock_generators: MagicMock) -> None:
        """Test that custom parameters are forwarded."""
        mock_generators.generate_powershell_role_structure.return_value = {}
        parsed_ir: dict[str, object] = {}

        from souschef.orchestrators.powershell import generate_powershell_role_structure

        generate_powershell_role_structure(
            parsed_ir,
            role_name="my_role",
            playbook_name="deploy",
            hosts="win_servers",
        )

        mock_generators.generate_powershell_role_structure.assert_called_once_with(
            parsed_ir,
            role_name="my_role",
            playbook_name="deploy",
            hosts="win_servers",
        )


class TestGeneratePowershellAwxJobTemplate:
    """Tests for generate_powershell_awx_job_template."""

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_delegates_with_defaults(self, mock_generators: MagicMock) -> None:
        """Test delegation with default parameters."""
        mock_generators.generate_powershell_awx_job_template.return_value = (
            "job template"
        )
        parsed_ir: dict[str, object] = {"actions": []}

        from souschef.orchestrators.powershell import (
            generate_powershell_awx_job_template,
        )

        result = generate_powershell_awx_job_template(parsed_ir)

        mock_generators.generate_powershell_awx_job_template.assert_called_once_with(
            parsed_ir,
            job_template_name="Windows PowerShell Migration",
            playbook="site.yml",
            inventory="windows-inventory",
            project="windows-migration-project",
            credential_name="windows-winrm-credential",
            environment="production",
            include_survey=True,
        )
        assert result == "job template"

    @patch("souschef.orchestrators.powershell.powershell_generators")
    def test_passes_custom_params(self, mock_generators: MagicMock) -> None:
        """Test that custom parameters are forwarded."""
        mock_generators.generate_powershell_awx_job_template.return_value = ""
        parsed_ir: dict[str, object] = {}

        from souschef.orchestrators.powershell import (
            generate_powershell_awx_job_template,
        )

        generate_powershell_awx_job_template(
            parsed_ir,
            job_template_name="My Job",
            playbook="deploy.yml",
            inventory="prod-inv",
            project="my-project",
            credential_name="my-cred",
            environment="staging",
            include_survey=False,
        )

        mock_generators.generate_powershell_awx_job_template.assert_called_once_with(
            parsed_ir,
            job_template_name="My Job",
            playbook="deploy.yml",
            inventory="prod-inv",
            project="my-project",
            credential_name="my-cred",
            environment="staging",
            include_survey=False,
        )
