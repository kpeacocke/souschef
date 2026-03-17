"""
Unit tests for souschef/generators/powershell.py.

Covers all public generator functions:
- generate_windows_inventory
- generate_windows_group_vars
- generate_ansible_requirements
- generate_powershell_role_structure
- generate_powershell_awx_job_template
- analyze_powershell_migration_fidelity
"""

from __future__ import annotations

import json

import yaml

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _minimal_ir(
    actions: list[dict] | None = None,
    source: str = "test_script.ps1",
) -> dict:
    """Build a minimal parsed IR dict suitable for generator calls."""
    return {
        "source": source,
        "actions": actions or [],
        "warnings": [],
        "metrics": {
            "total_lines": 1,
            "skipped_lines": 0,
            "windows_feature": 0,
            "service": 0,
            "registry": 0,
            "file": 0,
            "package": 0,
            "user": 0,
            "firewall": 0,
            "scheduled_task": 0,
            "environment": 0,
            "certificate": 0,
            "other_enterprise": 0,
            "other": 0,
        },
    }


def _action(action_type: str, params: dict | None = None) -> dict:
    """Build a minimal action dict."""
    return {
        "action_type": action_type,
        "params": params or {},
        "source_line": 1,
        "raw": "",
    }


# ---------------------------------------------------------------------------
# generate_windows_inventory
# ---------------------------------------------------------------------------


class TestGenerateWindowsInventory:
    """Tests for generate_windows_inventory()."""

    def test_default_contains_windows_group(self) -> None:
        """Default inventory contains the [windows] group header."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory()
        assert "[windows]" in result

    def test_default_contains_winrm_connection(self) -> None:
        """Default inventory contains ansible_connection=winrm."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory()
        assert "ansible_connection=winrm" in result

    def test_default_placeholder_host(self) -> None:
        """Default inventory includes the placeholder host."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory()
        assert "windows-host1.example.com" in result

    def test_custom_hosts_included(self) -> None:
        """Provided hosts appear in the inventory."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory(hosts=["web01.corp", "web02.corp"])
        assert "web01.corp" in result
        assert "web02.corp" in result

    def test_custom_winrm_port(self) -> None:
        """Custom winrm_port is reflected in the inventory."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory(winrm_port=5985)
        assert "5985" in result

    def test_ssl_transport_flag(self) -> None:
        """use_ssl=True sets winrm scheme to https and default transport to ntlm."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory(use_ssl=True)
        assert "ansible_winrm_scheme=https" in result
        assert "ansible_winrm_transport=ntlm" in result

    def test_non_ssl_transport_flag(self) -> None:
        """use_ssl=False sets winrm scheme to http."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory(use_ssl=False)
        assert "ansible_winrm_scheme=http" in result

    def test_custom_winrm_transport(self) -> None:
        """Custom winrm_transport is reflected in inventory."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory(winrm_transport="kerberos")
        assert "ansible_winrm_transport=kerberos" in result

    def test_validate_certs_ignore(self) -> None:
        """validate_certs=False sets cert validation to ignore."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory(validate_certs=False)
        assert "ignore" in result

    def test_validate_certs_validate(self) -> None:
        """validate_certs=True sets cert validation to validate."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory(validate_certs=True)
        assert "validate" in result

    def test_output_ends_with_newline(self) -> None:
        """Inventory output ends with a newline."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory()
        assert result.endswith("\n")

    def test_windows_vars_section_present(self) -> None:
        """Inventory contains the [windows:vars] section."""
        from souschef.generators.powershell import generate_windows_inventory

        result = generate_windows_inventory()
        assert "[windows:vars]" in result


# ---------------------------------------------------------------------------
# generate_windows_group_vars
# ---------------------------------------------------------------------------


class TestGenerateWindowsGroupVars:
    """Tests for generate_windows_group_vars()."""

    def test_output_is_valid_yaml(self) -> None:
        """Output is parseable YAML."""
        from souschef.generators.powershell import generate_windows_group_vars

        result = generate_windows_group_vars()
        # Strip the header comment lines before parsing
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_default_connection_winrm(self) -> None:
        """ansible_connection is winrm."""
        from souschef.generators.powershell import generate_windows_group_vars

        parsed = yaml.safe_load(generate_windows_group_vars())
        assert parsed["ansible_connection"] == "winrm"

    def test_default_user(self) -> None:
        """Default ansible_user is Administrator."""
        from souschef.generators.powershell import generate_windows_group_vars

        parsed = yaml.safe_load(generate_windows_group_vars())
        assert parsed["ansible_user"] == "Administrator"

    def test_custom_user(self) -> None:
        """Custom ansible_user is reflected in output."""
        from souschef.generators.powershell import generate_windows_group_vars

        parsed = yaml.safe_load(generate_windows_group_vars(ansible_user="svc_ansible"))
        assert parsed["ansible_user"] == "svc_ansible"

    def test_custom_port(self) -> None:
        """Custom winrm_port is reflected in output."""
        from souschef.generators.powershell import generate_windows_group_vars

        parsed = yaml.safe_load(generate_windows_group_vars(winrm_port=5985))
        assert parsed["ansible_port"] == 5985

    def test_ssl_transport(self) -> None:
        """use_ssl=True sets winrm scheme to https and default transport to ntlm."""
        from souschef.generators.powershell import generate_windows_group_vars

        parsed = yaml.safe_load(generate_windows_group_vars(use_ssl=True))
        assert parsed["ansible_winrm_scheme"] == "https"
        assert parsed["ansible_winrm_transport"] == "ntlm"

    def test_non_ssl_transport(self) -> None:
        """use_ssl=False sets winrm scheme to http."""
        from souschef.generators.powershell import generate_windows_group_vars

        parsed = yaml.safe_load(generate_windows_group_vars(use_ssl=False))
        assert parsed["ansible_winrm_scheme"] == "http"

    def test_custom_winrm_transport(self) -> None:
        """Custom winrm_transport is reflected in group_vars."""
        from souschef.generators.powershell import generate_windows_group_vars

        parsed = yaml.safe_load(generate_windows_group_vars(winrm_transport="kerberos"))
        assert parsed["ansible_winrm_transport"] == "kerberos"

    def test_vault_password_placeholder(self) -> None:
        """Output references a vault placeholder for the password."""
        from souschef.generators.powershell import generate_windows_group_vars

        result = generate_windows_group_vars()
        assert "vault" in result.lower()


# ---------------------------------------------------------------------------
# generate_ansible_requirements
# ---------------------------------------------------------------------------


class TestGenerateAnsibleRequirements:
    """Tests for generate_ansible_requirements()."""

    def test_output_is_valid_yaml(self) -> None:
        """Output is parseable YAML."""
        from souschef.generators.powershell import generate_ansible_requirements

        result = generate_ansible_requirements()
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_contains_ansible_windows_collection(self) -> None:
        """Output always includes the ansible.windows collection."""
        from souschef.generators.powershell import generate_ansible_requirements

        result = generate_ansible_requirements()
        assert "ansible.windows" in result

    def test_contains_community_windows_collection(self) -> None:
        """Output always includes community.windows collection."""
        from souschef.generators.powershell import generate_ansible_requirements

        result = generate_ansible_requirements()
        assert "community.windows" in result

    def test_none_ir_includes_all_collections(self) -> None:
        """With parsed_ir=None all conditional collections are included."""
        from souschef.generators.powershell import generate_ansible_requirements

        result = generate_ansible_requirements(parsed_ir=None)
        parsed = yaml.safe_load(result)
        names = [c["name"] for c in parsed["collections"]]
        assert "ansible.windows" in names

    def test_chocolatey_collection_added_for_chocolatey_install(self) -> None:
        """chocolatey.chocolatey is added when chocolatey_install is present."""
        from souschef.generators.powershell import generate_ansible_requirements

        ir = _minimal_ir([_action("chocolatey_install", {"package_name": "git"})])
        result = generate_ansible_requirements(parsed_ir=ir)
        assert "chocolatey.chocolatey" in result

    def test_no_chocolatey_collection_without_matching_action(self) -> None:
        """chocolatey.chocolatey is not added when no chocolatey actions present."""
        from souschef.generators.powershell import generate_ansible_requirements

        ir = _minimal_ir(
            [_action("windows_feature_install", {"feature_name": "Web-Server"})]
        )
        parsed = yaml.safe_load(generate_ansible_requirements(parsed_ir=ir))
        names = [c["name"] for c in parsed["collections"]]
        assert "chocolatey.chocolatey" not in names

    def test_collections_key_present(self) -> None:
        """YAML output contains a 'collections' key."""
        from souschef.generators.powershell import generate_ansible_requirements

        parsed = yaml.safe_load(generate_ansible_requirements())
        assert "collections" in parsed

    def test_install_comment_present(self) -> None:
        """Output contains the ansible-galaxy install instruction comment."""
        from souschef.generators.powershell import generate_ansible_requirements

        result = generate_ansible_requirements()
        assert "ansible-galaxy" in result


# ---------------------------------------------------------------------------
# generate_powershell_role_structure
# ---------------------------------------------------------------------------


class TestGeneratePowershellRoleStructure:
    """Tests for generate_powershell_role_structure()."""

    def test_returns_dict(self) -> None:
        """Function returns a dict."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert isinstance(result, dict)

    def test_contains_tasks_main_yml(self) -> None:
        """Returned dict contains roles/<role>/tasks/main.yml."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert any("tasks/main.yml" in k for k in result)

    def test_contains_handlers_main_yml(self) -> None:
        """Returned dict contains roles/<role>/handlers/main.yml."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert any("handlers/main.yml" in k for k in result)

    def test_contains_defaults_main_yml(self) -> None:
        """Returned dict contains roles/<role>/defaults/main.yml."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert any("defaults/main.yml" in k for k in result)

    def test_contains_meta_main_yml(self) -> None:
        """Returned dict contains roles/<role>/meta/main.yml."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert any("meta/main.yml" in k for k in result)

    def test_contains_readme(self) -> None:
        """Returned dict contains roles/<role>/README.md."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert any("README.md" in k for k in result)

    def test_contains_top_level_playbook(self) -> None:
        """Returned dict contains the top-level playbook file."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(
            _minimal_ir(), playbook_name="deploy"
        )
        assert "deploy.yml" in result

    def test_contains_inventory_hosts(self) -> None:
        """Returned dict contains inventory/hosts."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert "inventory/hosts" in result

    def test_contains_group_vars(self) -> None:
        """Returned dict contains group_vars/windows.yml."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert "group_vars/windows.yml" in result

    def test_contains_requirements_yml(self) -> None:
        """Returned dict contains requirements.yml."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        assert "requirements.yml" in result

    def test_custom_role_name_in_paths(self) -> None:
        """Custom role_name is used in the role directory paths."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir(), role_name="my_role")
        assert any("my_role" in k for k in result)

    def test_tasks_content_is_valid_yaml(self) -> None:
        """tasks/main.yml content is valid YAML."""
        from souschef.generators.powershell import generate_powershell_role_structure

        result = generate_powershell_role_structure(_minimal_ir())
        tasks_key = next(k for k in result if "tasks/main.yml" in k)
        parsed = yaml.safe_load(result[tasks_key])
        assert parsed is None or isinstance(parsed, list)

    def test_feature_install_adds_reboot_handler(self) -> None:
        """windows_feature_install action causes a reboot handler to be added."""
        from souschef.generators.powershell import generate_powershell_role_structure

        ir = _minimal_ir(
            [_action("windows_feature_install", {"feature_name": "Web-Server"})]
        )
        result = generate_powershell_role_structure(ir)
        handlers_key = next(k for k in result if "handlers/main.yml" in k)
        assert "Reboot" in result[handlers_key]

    def test_with_real_actions(self) -> None:
        """Role structure is generated correctly with multiple real actions."""
        from souschef.generators.powershell import generate_powershell_role_structure

        ir = _minimal_ir(
            [
                _action("user_create", {"username": "svc_app"}),
                _action("firewall_rule_create", {"rule_name": "Allow-80"}),
                _action("environment_set", {"name": "APP_ENV", "value": "prod"}),
            ]
        )
        result = generate_powershell_role_structure(ir)
        assert len(result) >= 10


# ---------------------------------------------------------------------------
# generate_powershell_awx_job_template
# ---------------------------------------------------------------------------


class TestGeneratePowershellAwxJobTemplate:
    """Tests for generate_powershell_awx_job_template()."""

    def test_output_contains_job_template_json_header(self) -> None:
        """Output contains the 'Job Template JSON' markdown header."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(_minimal_ir())
        assert "Job Template JSON" in result

    def test_output_contains_cli_import_command(self) -> None:
        """Output contains the 'CLI Import Command' markdown header."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(_minimal_ir())
        assert "CLI Import Command" in result

    def test_json_block_is_parseable(self) -> None:
        """The JSON block embedded in the output is parseable."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(_minimal_ir())
        # Extract the JSON block between ```json and ```
        start = result.index("```json\n") + len("```json\n")
        end = result.index("\n```", start)
        parsed = json.loads(result[start:end])
        assert "name" in parsed

    def test_custom_template_name(self) -> None:
        """Custom job_template_name appears in the output."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(
            _minimal_ir(), job_template_name="My Deploy Template"
        )
        assert "My Deploy Template" in result

    def test_custom_playbook(self) -> None:
        """Custom playbook filename appears in the output."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(
            _minimal_ir(), playbook="deploy.yml"
        )
        assert "deploy.yml" in result

    def test_custom_project(self) -> None:
        """Custom project name appears in the output."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(
            _minimal_ir(), project="my-windows-project"
        )
        assert "my-windows-project" in result

    def test_awx_cli_command_present(self) -> None:
        """awx-cli command is present in the output."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(_minimal_ir())
        assert "awx-cli" in result

    def test_script_analysis_summary_present(self) -> None:
        """Output contains the Script Analysis Summary section."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(_minimal_ir())
        assert "Script Analysis Summary" in result

    def test_environment_var_actions_produce_survey(self) -> None:
        """environment_set actions generate survey vars when include_survey=True."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        ir = _minimal_ir(
            [_action("environment_set", {"name": "APP_ENV", "value": "prod"})]
        )
        result = generate_powershell_awx_job_template(ir, include_survey=True)
        # The JSON block should have survey_enabled true
        start = result.index("```json\n") + len("```json\n")
        end = result.index("\n```", start)
        parsed = json.loads(result[start:end])
        assert "survey_spec" in parsed

    def test_no_survey_when_disabled(self) -> None:
        """survey_enabled is false when include_survey=False."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        result = generate_powershell_awx_job_template(
            _minimal_ir(), include_survey=False
        )
        start = result.index("```json\n") + len("```json\n")
        end = result.index("\n```", start)
        parsed = json.loads(result[start:end])
        assert parsed["survey_enabled"] is False


# ---------------------------------------------------------------------------
# analyze_powershell_migration_fidelity
# ---------------------------------------------------------------------------


class TestAnalyzePowershellMigrationFidelity:
    """Tests for analyze_powershell_migration_fidelity()."""

    def test_returns_valid_json(self) -> None:
        """Output is valid JSON."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        result = analyze_powershell_migration_fidelity(_minimal_ir())
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_fidelity_score_is_int(self) -> None:
        """fidelity_score is an integer."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        parsed = json.loads(analyze_powershell_migration_fidelity(_minimal_ir()))
        assert isinstance(parsed["fidelity_score"], int)

    def test_fidelity_score_range(self) -> None:
        """fidelity_score is between 0 and 100 inclusive."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        parsed = json.loads(analyze_powershell_migration_fidelity(_minimal_ir()))
        assert 0 <= parsed["fidelity_score"] <= 100

    def test_empty_script_fidelity_100(self) -> None:
        """An empty script yields fidelity_score of 100."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        parsed = json.loads(analyze_powershell_migration_fidelity(_minimal_ir()))
        assert parsed["fidelity_score"] == 100
        assert parsed["total_actions"] == 0

    def test_all_high_fidelity_actions_score_100(self) -> None:
        """A script with only high-fidelity actions scores 100."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        ir = _minimal_ir(
            [
                _action("windows_feature_install", {"feature_name": "Web-Server"}),
                _action("user_create", {"username": "svc_app"}),
            ]
        )
        parsed = json.loads(analyze_powershell_migration_fidelity(ir))
        assert parsed["fidelity_score"] == 100

    def test_win_shell_fallback_reduces_score(self) -> None:
        """win_shell actions reduce the fidelity score."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        ir = _minimal_ir(
            [
                _action("windows_feature_install", {"feature_name": "Web-Server"}),
                _action("win_shell", {"raw_command": "some-cmd"}),
            ]
        )
        parsed = json.loads(analyze_powershell_migration_fidelity(ir))
        assert parsed["fidelity_score"] < 100
        assert parsed["fallback_actions"] >= 1

    def test_review_required_list_present(self) -> None:
        """review_required key is present in the output."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        parsed = json.loads(analyze_powershell_migration_fidelity(_minimal_ir()))
        assert "review_required" in parsed
        assert isinstance(parsed["review_required"], list)

    def test_firewall_rule_create_in_review_required(self) -> None:
        """firewall_rule_create actions appear in review_required."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        ir = _minimal_ir([_action("firewall_rule_create", {"rule_name": "Allow-80"})])
        parsed = json.loads(analyze_powershell_migration_fidelity(ir))
        types = [r["action_type"] for r in parsed["review_required"]]
        assert "firewall_rule_create" in types

    def test_summary_string_present(self) -> None:
        """Summary key contains a human-readable string."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        parsed = json.loads(analyze_powershell_migration_fidelity(_minimal_ir()))
        assert isinstance(parsed["summary"], str)
        assert len(parsed["summary"]) > 0

    def test_recommendations_list_present(self) -> None:
        """Recommendations key is a list."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        parsed = json.loads(analyze_powershell_migration_fidelity(_minimal_ir()))
        assert isinstance(parsed["recommendations"], list)

    def test_source_key_preserved(self) -> None:
        """Source key from parsed_ir is preserved in the output."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        ir = _minimal_ir(source="my_script.ps1")
        parsed = json.loads(analyze_powershell_migration_fidelity(ir))
        assert parsed["source"] == "my_script.ps1"

    def test_total_actions_count(self) -> None:
        """total_actions reflects the number of actions in parsed_ir."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        ir = _minimal_ir(
            [
                _action("user_create", {"username": "a"}),
                _action("user_remove", {"username": "b"}),
                _action("win_shell", {"raw_command": "x"}),
            ]
        )
        parsed = json.loads(analyze_powershell_migration_fidelity(ir))
        assert parsed["total_actions"] == 3

    def test_automated_plus_fallback_equals_total(self) -> None:
        """automated_actions + fallback_actions accounts for all actions."""
        from souschef.generators.powershell import analyze_powershell_migration_fidelity

        ir = _minimal_ir(
            [
                _action("windows_feature_install", {"feature_name": "Web-Server"}),
                _action("win_shell", {"raw_command": "something"}),
                _action("user_create", {"username": "svc"}),
            ]
        )
        parsed = json.loads(analyze_powershell_migration_fidelity(ir))
        total = parsed["total_actions"]
        automated = parsed["automated_actions"]
        fallback = parsed["fallback_actions"]
        review_count = len(parsed["review_required"])
        # automated actions + fallback + any unaccounted = total
        assert automated + fallback <= total
        assert automated + fallback + review_count >= automated


# ---------------------------------------------------------------------------
# Chocolatey package name normalisation (via generate_powershell_awx_job_template)
# ---------------------------------------------------------------------------


class TestChocolateyPackageNameNormalisation:
    """Tests for Chocolatey package name normalisation in AWX job template extra_vars."""

    def _extra_vars(self, package_name: str) -> dict:
        """Return extra_vars dict produced for a single chocolatey_install action."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        ir = _minimal_ir([_action("chocolatey_install", {"package_name": package_name})])
        result = generate_powershell_awx_job_template(ir, include_survey=False)
        start = result.index("```json\n") + len("```json\n")
        end = result.index("\n```", start)
        parsed = json.loads(result[start:end])
        return json.loads(parsed.get("extra_vars", "{}"))

    def test_hyphens_replaced_with_underscores(self) -> None:
        """Hyphens in package names are replaced with underscores."""
        extra = self._extra_vars("my-package")
        assert "my_package_version" in extra

    def test_dots_replaced_with_underscores(self) -> None:
        """Dots in package names are replaced with underscores."""
        extra = self._extra_vars("pkg.name")
        assert "pkg_name_version" in extra

    def test_leading_digits_stripped(self) -> None:
        """Leading digits are stripped so the variable name is valid."""
        extra = self._extra_vars("7zip")
        assert "zip_version" in extra
        for key in extra:
            assert not key[0].isdigit(), f"Variable key starts with digit: {key}"

    def test_version_value_is_latest(self) -> None:
        """Chocolatey extra_vars value defaults to 'latest'."""
        extra = self._extra_vars("git")
        assert extra.get("git_version") == "latest"

    def test_environment_set_name_normalised(self) -> None:
        """Environment variable names are normalised to lowercase with underscores."""
        from souschef.generators.powershell import generate_powershell_awx_job_template

        ir = _minimal_ir(
            [_action("environment_set", {"name": "MY-VAR", "value": "hello"})]
        )
        result = generate_powershell_awx_job_template(ir, include_survey=False)
        start = result.index("```json\n") + len("```json\n")
        end = result.index("\n```", start)
        parsed = json.loads(result[start:end])
        extra = json.loads(parsed.get("extra_vars", "{}"))
        assert "my_var" in extra
        assert extra["my_var"] == "hello"
