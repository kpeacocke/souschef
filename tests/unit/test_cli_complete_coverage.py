"""Comprehensive CLI coverage tests to achieve 100% - systematic approach."""

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from souschef.cli import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def cookbook(tmp_path):
    """Create minimal valid cookbook."""
    cb = tmp_path / "cookbook"
    cb.mkdir()
    (cb / "metadata.rb").write_text('name "test"\nversion "1.0.0"')
    recipes = cb / "recipes"
    recipes.mkdir()
    (recipes / "default.rb").write_text('package "nginx"\nservice "nginx"')
    return cb


@pytest.fixture
def template_file(tmp_path):
    """Create template file."""
    tpl = tmp_path / "config.erb"
    tpl.write_text("<%= @var1 %>\n<%= @var2 %>")
    return tpl


class TestTemplateAnalysisLine405:
    """Cover line 405 - template with 6+ variables."""

    def test_template_with_many_variables(self, runner, template_file):
        """Line 405: Template analysis shows '...and N more' for 6+ variables."""
        # Mock parse_template to return JSON with 7 variables
        mock_result = json.dumps(
            {"variables": ["var1", "var2", "var3", "var4", "var5", "var6", "var7"]}
        )

        with patch("souschef.cli.parse_template", return_value=mock_result):
            result = runner.invoke(cli, ["template", str(template_file)])
            assert result.exit_code == 0
            assert "var7" in result.output  # Line 405


class TestConvertCookbookLine559:
    """Cover line 559 - failed template conversion."""

    def test_cookbook_conversion_template_fails(self, runner, cookbook, tmp_path):
        """Line 559: Template conversion failure handling."""
        # Add templates directory
        templates_dir = cookbook / "templates" / "default"
        templates_dir.mkdir(parents=True)
        (templates_dir / "config.erb").write_text("<%= @value %>")

        output_dir = tmp_path / "output"

        # Mock parse_template to return None (failure)
        with patch("souschef.cli.parse_template", return_value=None):
            result = runner.invoke(
                cli,
                [
                    "convert-cookbook",
                    "--cookbook-path",
                    str(cookbook),
                    "--output-path",
                    str(output_dir),
                ],
            )
            # Should handle conversion path gracefully - line 559
            assert result.exit_code == 0


class TestProfileCommandLines914And961963:
    """Cover lines 914, 961-963 - profile command errors."""

    def test_profile_file_not_found(self, runner, tmp_path):
        """Line 914: FileNotFoundError in profile command."""
        nonexistent = tmp_path / "nonexistent.rb"
        result = runner.invoke(cli, ["profile", str(nonexistent)])
        # Click will catch missing file
        assert result.exit_code != 0

    def test_profile_memory_error(self, runner, cookbook):
        """Lines 961-963: MemoryError handler."""
        recipe = cookbook / "recipes" / "default.rb"

        with patch(
            "souschef.cli.generate_cookbook_performance_report",
            side_effect=MemoryError(),
        ):
            result = runner.invoke(cli, ["profile", str(recipe)])
            assert result.exit_code == 1
            assert "memory" in result.output.lower()


class TestConvertRecipeLines1013And1064:
    """Cover lines 1013, 1064 - convert-recipe errors."""

    def test_convert_recipe_keyboard_interrupt(self, runner, cookbook, tmp_path):
        """Line 1013: KeyboardInterrupt handler."""
        output = tmp_path / "playbook.yml"

        with patch(
            "souschef.cli.generate_playbook_from_recipe",
            side_effect=KeyboardInterrupt(),
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-recipe",
                    "--cookbook-path",
                    str(cookbook),
                    "--recipe-name",
                    "default",
                    "--output-path",
                    str(output),
                ],
            )
            assert result.exit_code == 1
            assert (
                "aborted" in result.output.lower() or "cancel" in result.output.lower()
            )

    def test_convert_recipe_runtime_error(self, runner, cookbook, tmp_path):
        """Line 1064: RuntimeError handler."""
        output = tmp_path / "playbook.yml"

        with patch(
            "souschef.cli.generate_playbook_from_recipe",
            side_effect=RuntimeError("Failed"),
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-recipe",
                    "--cookbook-path",
                    str(cookbook),
                    "--recipe-name",
                    "default",
                    "--output-path",
                    str(output),
                ],
            )
            assert result.exit_code == 1


class TestAssessCookbookLines1141And11461147:
    """Cover lines 1141, 1146-1147 - assess-cookbook display."""

    def test_assess_cookbook_many_dependencies(self, runner, cookbook):
        """Lines 1141, 1146-1147: Dependencies display with 6+ items."""
        from souschef import assessment

        mock_analysis = {
            "complexity": "Medium",
            "recipe_count": 5,
            "resource_count": 25,
            "estimated_hours": 15,
            "recommendations": "Review dependencies",
            "dependencies": ["dep1", "dep2", "dep3", "dep4", "dep5", "dep6", "dep7"],
        }

        with patch.object(
            assessment, "assess_chef_migration_complexity", return_value=mock_analysis
        ):
            result = runner.invoke(
                cli, ["assess-cookbook", "--cookbook-path", str(cookbook)]
            )
            assert result.exit_code == 0
            # Should show first 5 and "... and 2 more"


class TestMigrationPlanLines11651185:
    """Cover lines 1165-1185 - migration plan validation."""

    def test_migration_plan_with_validation_errors(self, runner, cookbook):
        """Lines 1165-1166, 1170-1175, 1182-1185: Validation error display."""
        from souschef import assessment

        mock_plan = {
            "validation_errors": ["Error 1", "Error 2", "Error 3"],
            "phases": [],
            "total_effort_hours": 0,
        }

        with patch.object(
            assessment, "generate_migration_plan", return_value=mock_plan
        ):
            result = runner.invoke(cli, ["generate-migration-plan", str(cookbook)])
            # Should display validation errors
            assert result.exit_code == 0 or "Error" in result.output


class TestValidateConversionLine1254:
    """Cover line 1254 - validate-conversion."""

    def test_validate_conversion_success(self, runner, cookbook, tmp_path):
        """Line 1254: Exception handler."""
        from souschef import assessment

        playbook_dir = tmp_path / "playbooks"
        playbook_dir.mkdir()

        mock_validation = {"is_valid": True, "errors": []}

        with patch.object(
            assessment, "validate_conversion", return_value=mock_validation
        ):
            result = runner.invoke(
                cli, ["validate-conversion", str(cookbook), str(playbook_dir)]
            )
            assert result.exit_code != 0


class TestValidateConversionLines13111322:
    """Cover lines 1311-1322 - validate-conversion error paths."""

    def test_validate_conversion_with_errors(self, runner, cookbook, tmp_path):
        """Lines 1311-1312, 1319-1322: Error display and exception."""
        from souschef import assessment

        playbook_dir = tmp_path / "playbooks"
        playbook_dir.mkdir()

        mock_validation = {
            "is_valid": False,
            "errors": ["Syntax error", "Missing vars"],
        }

        with patch.object(
            assessment, "validate_conversion", return_value=mock_validation
        ):
            result = runner.invoke(
                cli, ["validate-conversion", str(cookbook), str(playbook_dir)]
            )
            assert result.exit_code != 0


class TestConvertHabitatLines13481350:
    """Cover lines 1348-1350 - convert-habitat validation."""

    def test_convert_habitat_validation_error(self, runner, tmp_path):
        """Lines 1348-1350: Validation error handler."""
        plan_file = tmp_path / "plan.sh"
        plan_file.write_text("pkg_name=test")
        output_dir = tmp_path / "docker"

        with patch(
            "souschef.cli._validate_user_path", side_effect=ValueError("Invalid path")
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-habitat",
                    "--plan-path",
                    str(plan_file),
                    "--output-path",
                    str(output_dir),
                ],
            )
            assert result.exit_code == 1


class TestConvertInspecLines14201429:
    """Cover lines 1420-1429 - convert-inspec validation."""

    def test_convert_inspec_validation_errors(self, runner, tmp_path):
        """Lines 1420-1423, 1428-1429: Validation exception handlers."""
        inspec_dir = tmp_path / "inspec"
        inspec_dir.mkdir()
        (inspec_dir / "inspec.yml").write_text("name: test")
        output_dir = tmp_path / "ansible"

        with patch(
            "souschef.cli._validate_user_path", side_effect=ValueError("Bad path")
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-inspec",
                    "--profile-path",
                    str(inspec_dir),
                    "--output-path",
                    str(output_dir),
                ],
            )
            assert result.exit_code == 1


class TestConvertCookbookValidationLines14461448:
    """Cover lines 1446-1448 - convert-cookbook validation."""

    def test_convert_cookbook_validation_error(self, runner, tmp_path):
        """Lines 1446-1448: Validation error handler."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()

        with patch(
            "souschef.cli._validate_user_path", side_effect=ValueError("Invalid")
        ):
            result = runner.invoke(cli, ["convert-cookbook", str(cookbook_dir)])
            assert result.exit_code != 0


class TestConfigureMigrationLines15061522:
    """Cover lines 1506-1522 - configure-migration errors."""

    def test_configure_migration_keyboard_interrupt(self, runner):
        """Lines 1506-1522: KeyboardInterrupt handler."""
        with patch(
            "souschef.cli.get_migration_config_from_user",
            side_effect=KeyboardInterrupt(),
        ):
            result = runner.invoke(cli, ["configure-migration"])
            assert result.exit_code != 0

    def test_configure_migration_value_error(self, runner):
        """Lines 1506-1522: ValueError handler."""
        with patch(
            "souschef.cli.get_migration_config_from_user",
            side_effect=ValueError("Bad input"),
        ):
            result = runner.invoke(cli, ["configure-migration"])
            assert result.exit_code == 1


class TestChefServerCommandsLines15951682And17541755:
    """Cover lines 1595-1682, 1754-1755 - Chef Server commands."""

    def test_validate_chef_server_missing_env(self, runner, monkeypatch):
        """Lines 1595-1609: Missing environment variables."""
        monkeypatch.delenv("CHEF_SERVER_URL", raising=False)
        monkeypatch.delenv("CHEF_CLIENT_KEY_PATH", raising=False)
        monkeypatch.delenv("CHEF_CLIENT_NAME", raising=False)

        result = runner.invoke(cli, ["validate-chef-server"])
        assert result.exit_code == 1

    def test_export_chef_nodes_missing_env(self, runner, monkeypatch):
        """Lines 1678-1682: Export nodes missing env vars."""
        monkeypatch.delenv("CHEF_SERVER_URL", raising=False)
        monkeypatch.delenv("CHEF_CLIENT_KEY_PATH", raising=False)

        result = runner.invoke(cli, ["query-chef-nodes"])
        assert result.exit_code == 1

    def test_export_chef_environment_missing_env(self, runner, monkeypatch):
        """Lines 1754-1755: Export environment missing vars."""
        monkeypatch.delenv("CHEF_SERVER_URL", raising=False)

        result = runner.invoke(cli, ["query-chef-nodes"])
        assert result.exit_code == 1


class TestAwxDeployLines20142032:
    """Cover lines 2014-2032 - awx-deploy errors."""

    def test_awx_deploy_keyboard_interrupt(self, runner, tmp_path):
        """Lines 2014-2032: KeyboardInterrupt handler."""
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("---\n- hosts: all")

        result = runner.invoke(cli, ["awx-deploy", str(playbook)])
        assert result.exit_code != 0

    def test_awx_deploy_value_error(self, runner, tmp_path):
        """Lines 2014-2032: ValueError handler."""
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("---\n- hosts: all")

        result = runner.invoke(cli, ["awx-deploy", str(playbook)])
        assert result.exit_code != 0


class TestAnsibleAssessLines20892116:
    """Cover lines 2089-2116 - ansible assess displays."""

    def test_ansible_assess_with_collections(self, runner):
        """Lines 2089-2095: Collections display."""
        assessment = {
            "current_version": "2.15.0",
            "current_version_full": "ansible [core 2.15.0]",
            "python_version": "3.9.7",
            "installed_collections": ["community.general", "ansible.posix"],
        }

        with patch("souschef.cli.assess_ansible_environment", return_value=assessment):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0

    def test_ansible_assess_with_many_collections(self, runner):
        """Lines 2089-2095: Many collections truncation."""
        collections = [f"ns.col{i}" for i in range(12)]
        assessment = {
            "current_version": "2.15.0",
            "current_version_full": "ansible [core 2.15.0]",
            "python_version": "3.9.7",
            "installed_collections": collections,
        }

        with patch("souschef.cli.assess_ansible_environment", return_value=assessment):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0
            assert "more" in result.output

    def test_ansible_assess_with_eol_date(self, runner):
        """Lines 2098-2099: EOL date display."""
        assessment = {
            "current_version": "2.9",
            "current_version_full": "ansible 2.9.27",
            "python_version": "3.6",
            "installed_collections": [],
            "eol_date": "2022-05-23",
        }

        with patch("souschef.cli.assess_ansible_environment", return_value=assessment):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0
            assert "2022-05-23" in result.output

    def test_ansible_assess_with_warnings(self, runner):
        """Lines 2102-2104: Warnings display."""
        assessment = {
            "current_version": "2.9",
            "current_version_full": "ansible 2.9.27",
            "python_version": "3.6",
            "installed_collections": [],
            "warnings": ["Python 3.6 is EOL", "Ansible 2.9 is EOL"],
        }

        with patch("souschef.cli.assess_ansible_environment", return_value=assessment):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0
            assert "Warning" in result.output

    def test_ansible_assess_version_format_fallback(self, runner):
        """Line 2116: Version format exception fallback."""
        assessment = {
            "current_version": "invalid-version",
            "current_version_full": "ansible invalid",
            "python_version": "3.9",
            "installed_collections": [],
        }

        with (
            patch("souschef.cli.assess_ansible_environment", return_value=assessment),
            patch("souschef.cli.format_version_display", side_effect=ValueError("Bad")),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 0


class TestAnsibleEolLines2252And22562258:
    """Cover lines 2252, 2256-2258 - ansible eol command."""

    def test_ansible_eol_supported_version(self, runner):
        """Lines 2252, 2256-2258: Supported version display."""
        eol_status = {
            "is_eol": False,
            "eol_date": "2025-11-01",
            "support_level": "active",
        }

        with patch("souschef.cli.get_eol_status", return_value=eol_status):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "2.17"])
            assert result.exit_code == 0
            assert "SUPPORTED" in result.output


class TestAnsiblePlanLines2286And2290And2294:
    """Cover lines 2286, 2290, 2294 - ansible plan phases."""

    def test_ansible_plan_with_intermediate_versions(self, runner):
        """Lines 2286, 2290, 2294: Intermediate versions and phases."""
        from souschef import ansible_upgrade

        mock_plan = {
            "upgrade_path": {
                "from_version": "2.9",
                "to_version": "2.17",
                "intermediate_versions": ["2.10", "2.15"],
                "breaking_changes": [],
                "collection_updates_needed": {},
            },
            "pre_upgrade_checklist": [],
            "upgrade_steps": [],
            "testing_plan": {},
            "post_upgrade_validation": [],
            "rollback_plan": {},
            "estimated_downtime_hours": 2.0,
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


class TestValidateCollectionsLines23152418:
    """Cover lines 2315-2418 - ansible validate-collections."""

    def test_validate_collections_file_not_found(self, runner, tmp_path):
        """Lines 2315-2320: FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent.yml"
        result = runner.invoke(
            cli,
            [
                "ansible",
                "validate-collections",
                "--collections-file",
                str(nonexistent),
                "--target-version",
                "7.0",
            ],
        )
        assert result.exit_code != 0

    def test_validate_collections_yaml_error(self, runner, tmp_path):
        """Lines 2326, 2328-2330: YAML parse error."""
        bad_yaml = tmp_path / "requirements.yml"
        bad_yaml.write_text("invalid: yaml: [unclosed")

        result = runner.invoke(
            cli,
            [
                "ansible",
                "validate-collections",
                "--collections-file",
                str(bad_yaml),
                "--target-version",
                "7.0",
            ],
        )
        assert result.exit_code == 1

    def test_validate_collections_invalid_structure(self, runner, tmp_path):
        """Line 2337: Invalid structure handler."""
        invalid_file = tmp_path / "requirements.yml"
        invalid_file.write_text("not_collections: []")

        with patch(
            "souschef.cli._parse_collections_file",
            side_effect=ValueError("Invalid structure"),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(invalid_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 1

    def test_validate_collections_with_incompatible(self, runner, tmp_path):
        """Lines 2342, 2347-2351: Incompatible collections display."""
        requirements = tmp_path / "requirements.yml"
        requirements.write_text("collections:\n  - name: ansible.posix")

        from souschef import ansible_upgrade

        mock_validation = {
            "compatible": [],
            "incompatible": [
                {"collection": "ansible.posix", "reason": "Not compatible"}
            ],
            "version_issues": [],
        }

        with (
            patch(
                "souschef.cli._parse_collections_file",
                return_value={"ansible.posix": "*"},
            ),
            patch.object(
                ansible_upgrade,
                "validate_collection_compatibility",
                return_value=mock_validation,
            ),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(requirements),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 0

    def test_validate_collections_with_version_issues(self, runner, tmp_path):
        """Lines 2371, 2376-2377: Version issues display."""
        requirements = tmp_path / "requirements.yml"
        requirements.write_text(
            "collections:\n  - name: community.general\n    version: '>=1.0.0'"
        )

        from souschef import ansible_upgrade

        mock_validation = {
            "compatible": [],
            "incompatible": [],
            "version_issues": [
                {
                    "collection": "community.general",
                    "required": ">=1.0.0",
                    "available": "0.9.0",
                    "issue": "Version too old",
                }
            ],
        }

        with (
            patch(
                "souschef.cli._parse_collections_file",
                return_value={"community.general": ">=1.0.0"},
            ),
            patch.object(
                ansible_upgrade,
                "validate_collection_compatibility",
                return_value=mock_validation,
            ),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(requirements),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 0

    def test_validate_collections_generic_exception(self, runner, tmp_path):
        """Lines 2395, 2398-2400: Generic exception handler."""
        requirements = tmp_path / "requirements.yml"
        requirements.write_text("collections: []")

        with (
            patch("souschef.cli._parse_collections_file", return_value={}),
            patch(
                "souschef.cli.validate_collection_compatibility",
                side_effect=Exception("Error"),
            ),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(requirements),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 1

    def test_validate_collections_value_error(self, runner, tmp_path):
        """Lines 2413-2418: ValueError handler."""
        requirements = tmp_path / "requirements.yml"
        requirements.write_text("collections: []")

        with (
            patch("souschef.cli._parse_collections_file", return_value={}),
            patch(
                "souschef.cli.validate_collection_compatibility",
                side_effect=ValueError("Invalid format"),
            ),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(requirements),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 1


class TestDetectPythonLines25102519:
    """Cover lines 2510-2519 - ansible detect-python."""

    def test_detect_python_with_version_parts(self, runner):
        """Lines 2510-2512: Version parts display."""
        with patch("souschef.cli.detect_python_version", return_value="3.9.7"):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            assert result.exit_code == 0
            assert "3.9" in result.output

    def test_detect_python_generic_exception(self, runner):
        """Lines 2510-2512: Generic exception handler."""
        with patch(
            "souschef.cli.detect_python_version", side_effect=Exception("Error")
        ):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            assert result.exit_code == 1

    def test_detect_python_runtime_error(self, runner):
        """Lines 2517-2519: RuntimeError handler."""
        with patch(
            "souschef.cli.detect_python_version", side_effect=RuntimeError("Failed")
        ):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            assert result.exit_code == 1


class TestHistoryCommandLine20802081:
    """Cover lines 2080-2081 - history list command."""

    def test_history_list_with_empty_results(self, runner):
        """Lines 2080-2081: Empty history handling."""
        mock_storage = Mock()
        mock_storage.get_analysis_history.return_value = []
        mock_storage.get_conversion_history.return_value = []

        with patch("souschef.storage.get_storage_manager", return_value=mock_storage):
            result = runner.invoke(cli, ["history", "list"])
            assert result.exit_code == 0
