"""Focused coverage tests for UI page lazy API wrappers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def test_bash_migration_wrapper_calls() -> None:
    """Bash page wrappers should delegate to the lazy API module."""
    from souschef.ui.pages import bash_migration

    fake_api = SimpleNamespace(
        convert_bash_content_to_ansible=lambda content, script_path=None: (
            f"convert:{content}:{script_path}"
        ),
        generate_ansible_role_from_bash=lambda content,
        role_name=None,
        script_path=None: (f"role:{content}:{role_name}:{script_path}"),
    )
    with patch("souschef.ui.pages.bash_migration._bash_api", return_value=fake_api):
        assert (
            bash_migration.convert_bash_content_to_ansible("echo hi", "x.sh")
            == "convert:echo hi:x.sh"
        )
        assert (
            bash_migration.generate_ansible_role_from_bash("echo hi", "r", "x.sh")
            == "role:echo hi:r:x.sh"
        )


def test_chef_server_settings_wrapper_calls() -> None:
    """Chef server settings wrappers should delegate to lazy API module."""
    from souschef.ui.pages import chef_server_settings

    fake_api = SimpleNamespace(
        assess_single_cookbook_with_ai=lambda *args, **kwargs: {"ok": True},
        orchestrate_get_storage_manager=lambda *args, **kwargs: "storage",
    )
    with patch(
        "souschef.ui.pages.chef_server_settings._chef_api", return_value=fake_api
    ):
        assert chef_server_settings.assess_single_cookbook_with_ai("cb") == {"ok": True}
        assert chef_server_settings.get_storage_manager("x") == "storage"


def test_cookbook_analysis_wrapper_calls() -> None:
    """Cookbook analysis proxy wrappers should delegate to lazy Chef API."""
    from souschef.ui.pages import cookbook_analysis

    fake_api = SimpleNamespace(
        analyse_cookbook_dependencies=lambda *args, **kwargs: "deps",
        assess_single_cookbook_with_ai=lambda *args, **kwargs: {"ai": True},
        orchestrate_cookbook_metadata_parsing=lambda *args, **kwargs: {"meta": 1},
        orchestrate_generate_playbook_from_recipe=lambda *args, **kwargs: "playbook",
        orchestrate_generate_playbook_from_recipe_with_ai=lambda *args, **kwargs: (
            "playbook-ai"
        ),
        orchestrate_get_blob_storage=lambda *args, **kwargs: "blob",
        orchestrate_template_conversion=lambda *args, **kwargs: "templates",
    )
    with patch("souschef.ui.pages.cookbook_analysis._chef_api", return_value=fake_api):
        assert cookbook_analysis.analyse_cookbook_dependencies("cb") == "deps"
        assert cookbook_analysis.assess_single_cookbook_with_ai("cb") == {"ai": True}
        assert cookbook_analysis.parse_cookbook_metadata("cb") == {"meta": 1}
        assert cookbook_analysis.generate_playbook_from_recipe("r") == "playbook"
        assert (
            cookbook_analysis.generate_playbook_from_recipe_with_ai("r")
            == "playbook-ai"
        )
        assert cookbook_analysis.get_blob_storage("x") == "blob"
        assert cookbook_analysis._convert_templates_impl("x") == "templates"


def test_migration_config_activity_breakdown_wrapper() -> None:
    """Migration config wrapper should call lazy-imported Chef API."""
    from souschef.ui.pages import migration_config

    fake_api = SimpleNamespace(
        calculate_activity_breakdown=lambda *a, **k: {"hours": 1}
    )
    with patch(
        "souschef.ui.pages.migration_config.importlib.import_module",
        return_value=fake_api,
    ):
        assert migration_config.calculate_activity_breakdown("x") == {"hours": 1}


def test_powershell_wrappers_and_stored_results_branch() -> None:
    """PowerShell wrappers and rerun persistence branch should be covered."""
    from souschef.ui.pages import powershell_migration

    fake_api = SimpleNamespace(
        analyze_powershell_migration_fidelity=lambda *a, **k: "fidelity",
        generate_windows_inventory=lambda *a, **k: "inventory",
        generate_windows_group_vars=lambda *a, **k: "group_vars",
        generate_ansible_requirements=lambda *a, **k: "requirements",
        generate_powershell_role_structure=lambda *a, **k: {"role": "ok"},
        generate_powershell_awx_job_template=lambda *a, **k: "awx",
    )
    with patch(
        "souschef.ui.pages.powershell_migration._powershell_api", return_value=fake_api
    ):
        assert (
            powershell_migration.analyze_powershell_migration_fidelity("x")
            == "fidelity"
        )
        assert powershell_migration.generate_windows_inventory("x") == "inventory"
        assert powershell_migration.generate_windows_group_vars("x") == "group_vars"
        assert powershell_migration.generate_ansible_requirements("x") == "requirements"
        assert powershell_migration.generate_powershell_role_structure("x") == {
            "role": "ok"
        }
        assert powershell_migration.generate_powershell_awx_job_template("x") == "awx"

    # Cover _render_action_buttons branch where no buttons are clicked.
    st_mock = MagicMock()
    cols = [MagicMock(), MagicMock(), MagicMock()]
    for col in cols:
        col.__enter__ = lambda s: s
        col.__exit__ = MagicMock(return_value=False)
    st_mock.columns.return_value = cols
    st_mock.button.side_effect = [False, False, False]

    with (
        patch("souschef.ui.pages.powershell_migration.st", st_mock),
        patch(
            "souschef.ui.pages.powershell_migration._display_stored_results"
        ) as mock_stored,
    ):
        powershell_migration._render_action_buttons("script", "play", "hosts", "role")
    mock_stored.assert_called_once_with()


def test_puppet_migration_wrapper_calls() -> None:
    """Puppet page wrappers should delegate to the lazy API module."""
    from souschef.ui.pages import puppet_migration

    fake_api = SimpleNamespace(
        list_puppet_server_nodes=lambda *a, **k: {"nodes": []},
        import_puppet_catalog_to_ir=lambda *a, **k: {"catalog": True},
        parse_puppet_module=lambda *a, **k: "parsed-module",
        convert_puppet_module_to_ansible=lambda *a, **k: "converted-module",
        convert_puppet_module_to_ansible_with_ai=lambda *a, **k: "converted-module-ai",
    )
    with patch("souschef.ui.pages.puppet_migration._puppet_api", return_value=fake_api):
        assert puppet_migration.list_puppet_server_nodes("url") == {"nodes": []}
        assert puppet_migration.import_puppet_catalog_to_ir("cat") == {"catalog": True}
        assert puppet_migration.parse_puppet_module("mod") == "parsed-module"
        assert (
            puppet_migration.convert_puppet_module_to_ansible("mod")
            == "converted-module"
        )
        assert (
            puppet_migration.convert_puppet_module_to_ansible_with_ai("mod")
            == "converted-module-ai"
        )


def test_salt_migration_wrapper_calls() -> None:
    """Salt page wrappers should delegate to the lazy API module."""
    from souschef.ui.pages import salt_migration

    fake_api = SimpleNamespace(
        assess_salt_complexity=lambda *a, **k: "complexity",
        convert_salt_directory_to_roles=lambda *a, **k: "roles",
        convert_salt_sls_to_ansible=lambda *a, **k: "sls",
        generate_salt_inventory=lambda *a, **k: "inventory",
        parse_salt_directory=lambda *a, **k: "parse-dir",
        parse_salt_pillar=lambda *a, **k: "parse-pillar",
        parse_salt_sls=lambda *a, **k: "parse-sls",
        plan_salt_migration=lambda *a, **k: "plan",
    )
    with patch("souschef.ui.pages.salt_migration._salt_api", return_value=fake_api):
        assert salt_migration.assess_salt_complexity("x") == "complexity"
        assert salt_migration.convert_salt_directory_to_roles("x") == "roles"
        assert salt_migration.convert_salt_sls_to_ansible("x") == "sls"
        assert salt_migration.generate_salt_inventory("x") == "inventory"
        assert salt_migration.parse_salt_directory("x") == "parse-dir"
        assert salt_migration.parse_salt_pillar("x") == "parse-pillar"
        assert salt_migration.parse_salt_sls("x") == "parse-sls"
        assert salt_migration.plan_salt_migration("x") == "plan"


def test_salt_migration_salt_api_loader_calls_import_module() -> None:
    """Salt page lazy loader should import the Salt API module."""
    from souschef.ui.pages import salt_migration

    sentinel = object()
    with patch(
        "souschef.ui.pages.salt_migration.importlib.import_module",
        return_value=sentinel,
    ) as mock_import:
        loaded = salt_migration._salt_api()

    assert loaded is sentinel
    mock_import.assert_called_once_with("souschef.api.salt_api")
