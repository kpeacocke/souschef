"""
Tests for missing coverage branches in souschef/migration_v2.py.

Covers error paths, edge cases, and exception handling branches
not reached by existing test suites.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from souschef.migration_v2 import (
    ChefServerOptions,
    MigrationOrchestrator,
    MigrationResult,
    MigrationStatus,
)


def _make_orchestrator() -> MigrationOrchestrator:
    """Create a standard MigrationOrchestrator for testing."""
    return MigrationOrchestrator(
        chef_version="15.10.91",
        target_platform="awx",
        target_version="24.6.1",
    )


def _init_result(orch: MigrationOrchestrator, cookbook_path: str = "/tmp/cb") -> None:
    """Initialise a MigrationResult on the orchestrator."""
    from datetime import datetime

    from souschef.migration_v2 import ConversionMetrics

    orch.result = MigrationResult(
        migration_id=orch.migration_id,
        status=MigrationStatus.PENDING,
        chef_version="18",
        target_platform="awx",
        target_version="23",
        ansible_version="2.15",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        source_cookbook=cookbook_path,
        metrics=ConversionMetrics(),
    )


# ---------------------------------------------------------------------------
# Lines 543-551: Chef Server query skipped – missing configuration
# ---------------------------------------------------------------------------


def test_migrate_cookbook_chef_server_missing_config(tmp_path: Path) -> None:
    """Test that partial chef_server config (server_url only) adds a warning."""
    cookbook_dir = tmp_path / "mycookbook"
    cookbook_dir.mkdir()
    (cookbook_dir / "recipes").mkdir()
    (cookbook_dir / "recipes" / "default.rb").write_text('package "vim"')

    orch = _make_orchestrator()
    chef_opts = ChefServerOptions(
        server_url="https://chef.example.com",
        organisation=None,
        client_name=None,
    )

    with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
        mock_gen.return_value = "Error: could not convert"
        result = orch.migrate_cookbook(
            str(cookbook_dir),
            skip_validation=True,
            chef_server=chef_opts,
        )

    assert any(
        "missing configuration" in str(w.get("message", "")) for w in result.warnings
    )


def test_migrate_cookbook_chef_server_missing_client_key(tmp_path: Path) -> None:
    """Test that full server config but no client key adds a missing-key warning."""
    cookbook_dir = tmp_path / "mycookbook"
    cookbook_dir.mkdir()
    (cookbook_dir / "recipes").mkdir()

    orch = _make_orchestrator()
    chef_opts = ChefServerOptions(
        server_url="https://chef.example.com",
        organisation="myorg",
        client_name="admin",
        client_key_path=None,
        client_key=None,
    )

    with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
        mock_gen.return_value = "Error: skip"
        result = orch.migrate_cookbook(
            str(cookbook_dir),
            skip_validation=True,
            chef_server=chef_opts,
        )

    assert any(
        "missing client key" in str(w.get("message", "")) for w in result.warnings
    )


# ---------------------------------------------------------------------------
# Lines 600-602: _validate_playbooks called (skip_validation=False)
# ---------------------------------------------------------------------------


def test_migrate_cookbook_skip_validation_false(tmp_path: Path) -> None:
    """Test that skip_validation=False triggers validation path."""
    cookbook_dir = tmp_path / "cb"
    cookbook_dir.mkdir()
    (cookbook_dir / "recipes").mkdir()
    (cookbook_dir / "recipes" / "default.rb").write_text('package "vim"')

    orch = _make_orchestrator()

    with (
        patch(
            "souschef.migration_v2.generate_playbook_from_recipe",
            return_value="---\n- hosts: all",
        ),
        patch.object(orch, "_validate_playbooks") as mock_val,
    ):
        result = orch.migrate_cookbook(str(cookbook_dir), skip_validation=False)

    mock_val.assert_called_once()
    assert result.status == MigrationStatus.VALIDATED


# ---------------------------------------------------------------------------
# Lines 688-760: _prepare_cookbook_source – cookbook path doesn't exist
# ---------------------------------------------------------------------------


def test_prepare_cookbook_source_missing_path_no_server() -> None:
    """Test _prepare_cookbook_source raises ValueError when no server config."""
    orch = _make_orchestrator()
    _init_result(orch, "/nonexistent/cookbook")

    with pytest.raises(ValueError, match="Chef Server configuration is required"):
        orch._prepare_cookbook_source(
            cookbook_path="/nonexistent/path",
            chef_server_url=None,
            chef_organisation=None,
            chef_client_name=None,
            chef_client_key_path=None,
            chef_client_key=None,
            chef_node=None,
            chef_policy=None,
            cookbook_name=None,
            cookbook_version=None,
            dependency_depth="full",
            use_cache=True,
            offline_bundle_path=None,
        )


def test_prepare_cookbook_source_missing_key() -> None:
    """Test _prepare_cookbook_source raises ValueError when no client key."""
    orch = _make_orchestrator()
    _init_result(orch)

    with pytest.raises(ValueError, match="client key is required"):
        orch._prepare_cookbook_source(
            cookbook_path="/nonexistent/path",
            chef_server_url="https://chef.example.com",
            chef_organisation="myorg",
            chef_client_name="admin",
            chef_client_key_path=None,
            chef_client_key=None,
            chef_node=None,
            chef_policy=None,
            cookbook_name="mycookbook",
            cookbook_version=None,
            dependency_depth="full",
            use_cache=True,
            offline_bundle_path=None,
        )


# ---------------------------------------------------------------------------
# Lines 874-876, 943: _build_migration_report with offline_bundle and run_list
# ---------------------------------------------------------------------------


def test_build_migration_report_with_optional_fields() -> None:
    """Test _build_migration_report includes offline_bundle and run_list."""
    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None
    orch.result.offline_bundle_path = "/tmp/offline.tar.gz"
    orch.result.run_list = ["cookbook1::default", "cookbook2::install"]

    report = orch._build_migration_report()

    assert "Offline bundle" in report
    assert "cookbook1::default" in report
    assert "cookbook2::install" in report


# ---------------------------------------------------------------------------
# Line 1112: _convert_attributes_parallel with no attribute files
# ---------------------------------------------------------------------------


def test_convert_attributes_parallel_empty_dir(tmp_path: Path) -> None:
    """Test _convert_attributes_parallel returns early when no .rb files exist."""
    cookbook_dir = tmp_path / "cb"
    cookbook_dir.mkdir()
    (cookbook_dir / "attributes").mkdir()
    # No .rb files placed – should return early (line 1112)

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    orch._convert_attributes_parallel(str(cookbook_dir), max_workers=1)

    assert orch.result is not None
    assert orch.result.metrics.attributes_converted == 0


# ---------------------------------------------------------------------------
# Lines 1202-1204: _convert_recipes exception branch
# ---------------------------------------------------------------------------


def test_convert_recipes_exception(tmp_path: Path) -> None:
    """Test _convert_recipes handles exception during recipe conversion."""
    cookbook_dir = tmp_path / "cb"
    (cookbook_dir / "recipes").mkdir(parents=True)
    (cookbook_dir / "recipes" / "default.rb").write_text('package "vim"')

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    with patch(
        "souschef.migration_v2.generate_playbook_from_recipe",
        side_effect=RuntimeError("boom"),
    ):
        orch._convert_recipes(str(cookbook_dir))

    assert orch.result is not None
    assert orch.result.metrics.recipes_skipped == 1


# ---------------------------------------------------------------------------
# Lines 1226-1233: _convert_attributes skipped/exception branches
# ---------------------------------------------------------------------------


def test_convert_attributes_failure(tmp_path: Path) -> None:
    """Test _convert_attributes handles attributes that fail to convert."""
    cookbook_dir = tmp_path / "cb"
    (cookbook_dir / "attributes").mkdir(parents=True)
    (cookbook_dir / "attributes" / "default.rb").write_text("default['key'] = 'val'")

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    with patch(
        "souschef.migration_v2.parse_attributes",
        return_value="Error: parse failure",
    ):
        orch._convert_attributes(str(cookbook_dir))

    assert orch.result is not None
    assert orch.result.metrics.attributes_skipped == 1


def test_convert_attributes_exception(tmp_path: Path) -> None:
    """Test _convert_attributes handles exceptions during attribute conversion."""
    cookbook_dir = tmp_path / "cb"
    (cookbook_dir / "attributes").mkdir(parents=True)
    (cookbook_dir / "attributes" / "default.rb").write_text("default['key'] = 'val'")

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    with patch(
        "souschef.migration_v2.parse_attributes",
        side_effect=OSError("disk error"),
    ):
        orch._convert_attributes(str(cookbook_dir))

    assert orch.result is not None
    assert orch.result.metrics.attributes_skipped == 1


# ---------------------------------------------------------------------------
# Lines 1261-1262: _analyze_resources exception
# ---------------------------------------------------------------------------


def test_analyze_resources_exception(tmp_path: Path) -> None:
    """Test _process_recipe_resources handles recipe parse exceptions gracefully."""
    cookbook_dir = tmp_path / "cb"
    (cookbook_dir / "recipes").mkdir(parents=True)
    recipe_file = cookbook_dir / "recipes" / "default.rb"
    recipe_file.write_text('package "vim"')

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    with patch(
        "souschef.migration_v2.parse_recipe",
        side_effect=RuntimeError("parse boom"),
    ):
        orch._process_recipe_resources(str(cookbook_dir))


# ---------------------------------------------------------------------------
# Lines 1278-1279: _extract_recipe_resource_count exception
# ---------------------------------------------------------------------------


def test_extract_recipe_resource_count_exception(tmp_path: Path) -> None:
    """Test _extract_recipe_resource_count silently handles exceptions."""
    orch = _make_orchestrator()
    _init_result(orch)

    # Passing a fake Path with a name attribute that would be accessed
    fake_path = MagicMock(spec=Path)
    fake_path.name = "bad.rb"

    # Cause content.split to raise
    orch._extract_recipe_resource_count(fake_path, "not\ta\tstring\x00")


# ---------------------------------------------------------------------------
# Lines 1305-1309: _process_custom_resources exception
# ---------------------------------------------------------------------------


def test_process_custom_resources_exception(tmp_path: Path) -> None:
    """Test _process_custom_resources handles exceptions per-file."""
    cookbook_dir = tmp_path / "cb"
    (cookbook_dir / "resources").mkdir(parents=True)
    (cookbook_dir / "resources" / "myresource.rb").write_text("# resource")

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    # Patch the glob to return a file whose .stem raises an exception
    mock_file = MagicMock(spec=Path)
    mock_file.name = "myresource.rb"
    mock_file.__str__ = lambda self: str(  # type: ignore[assignment]
        cookbook_dir / "resources" / "myresource.rb"
    )

    def _boom() -> str:
        raise OSError("stem error")

    type(mock_file).stem = property(lambda self: _boom())

    with patch.object(Path, "glob", return_value=iter([mock_file])):
        orch._process_custom_resources(str(cookbook_dir))

    assert orch.result is not None
    assert orch.result.metrics.resources_skipped >= 1


# ---------------------------------------------------------------------------
# Lines 1351-1352: _process_library_handlers exception
# ---------------------------------------------------------------------------


def test_process_library_handlers_exception(tmp_path: Path) -> None:
    """Test _process_library_handlers handles per-file exceptions."""
    cookbook_dir = tmp_path / "cb"
    libraries_dir = cookbook_dir / "libraries"
    libraries_dir.mkdir(parents=True)
    lib_file = libraries_dir / "myhandler.rb"
    lib_file.write_text("class MyHandler < Chef::Handler\nend")

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    mock_file = MagicMock(spec=Path)
    mock_file.name = "myhandler.rb"
    mock_file.stem = "myhandler"
    mock_file.read_text.side_effect = OSError("read error")

    with patch.object(Path, "glob", return_value=iter([mock_file])):
        orch._process_library_handlers(str(cookbook_dir))


# ---------------------------------------------------------------------------
# Lines 1367-1380: _process_recipe_handlers with rescue/notifies content
# ---------------------------------------------------------------------------


def test_process_recipe_handlers_rescue_notifies(tmp_path: Path) -> None:
    """Test _process_recipe_handlers detects rescue+notifies in recipes."""
    cookbook_dir = tmp_path / "cb"
    recipes_dir = cookbook_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    recipe_content = (
        "service 'nginx' do\n"
        "  action :start\n"
        "  notifies :restart, 'service[nginx]'\n"
        "rescue\n"
        "end\n"
    )
    (recipes_dir / "default.rb").write_text(recipe_content)

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    orch._process_recipe_handlers(str(cookbook_dir))

    assert orch.result is not None
    assert any(w.get("type") == "handler" for w in orch.result.warnings)


def test_process_recipe_handlers_read_exception(tmp_path: Path) -> None:
    """Test _process_recipe_handlers handles read exceptions gracefully."""
    cookbook_dir = tmp_path / "cb"
    recipes_dir = cookbook_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    (recipes_dir / "default.rb").write_text("# empty")

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    mock_file = MagicMock(spec=Path)
    mock_file.name = "default.rb"
    mock_file.read_text.side_effect = OSError("read error")

    with patch.object(Path, "glob", return_value=iter([mock_file])):
        orch._process_recipe_handlers(str(cookbook_dir))


# ---------------------------------------------------------------------------
# Lines 1409-1416, 1426-1435: _convert_templates failure and exception
# ---------------------------------------------------------------------------


def test_convert_templates_failure(tmp_path: Path) -> None:
    """Test _convert_templates handles templates that fail to convert."""
    cookbook_dir = tmp_path / "cb"
    templates_dir = cookbook_dir / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "nginx.conf.erb").write_text("<%= @port %>")

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    with patch(
        "souschef.migration_v2.convert_template_file",
        return_value={"success": False, "error": "ERB parse failed"},
    ):
        orch._convert_templates(str(cookbook_dir))

    assert orch.result is not None
    assert orch.result.metrics.templates_skipped == 1


def test_convert_templates_exception(tmp_path: Path) -> None:
    """Test _convert_templates handles exceptions during template conversion."""
    cookbook_dir = tmp_path / "cb"
    templates_dir = cookbook_dir / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "nginx.conf.erb").write_text("<%= @port %>")

    orch = _make_orchestrator()
    _init_result(orch, str(cookbook_dir))

    with patch(
        "souschef.migration_v2.convert_template_file",
        side_effect=RuntimeError("template boom"),
    ):
        orch._convert_templates(str(cookbook_dir))

    assert orch.result is not None
    assert orch.result.metrics.templates_skipped == 1


# ---------------------------------------------------------------------------
# Line 1474: ansible-lint validation passes (returncode 0)
# ---------------------------------------------------------------------------


def test_run_playbook_validation_passes(tmp_path: Path) -> None:
    """Test _run_playbook_validation logs success when ansible-lint passes."""
    playbook_file = tmp_path / "site.yml"
    playbook_file.write_text("---\n- hosts: all\n  tasks: []\n")

    orch = _make_orchestrator()
    _init_result(orch)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        orch._run_playbook_validation([playbook_file])

    assert orch.result is not None
    assert not any(w.get("phase") == "validation" for w in orch.result.warnings)


# ---------------------------------------------------------------------------
# Lines 1486-1502: ansible-lint not found / timeout / generic exception
# ---------------------------------------------------------------------------


def test_run_playbook_validation_not_found(tmp_path: Path) -> None:
    """Test _run_playbook_validation handles ansible-lint not being installed."""
    playbook_file = tmp_path / "site.yml"
    playbook_file.write_text("---\n")

    orch = _make_orchestrator()
    _init_result(orch)

    with patch(
        "subprocess.run", side_effect=FileNotFoundError("ansible-lint not found")
    ):
        orch._run_playbook_validation([playbook_file])

    assert orch.result is not None


def test_run_playbook_validation_timeout(tmp_path: Path) -> None:
    """Test _run_playbook_validation handles validation timeout."""
    playbook_file = tmp_path / "site.yml"
    playbook_file.write_text("---\n")

    orch = _make_orchestrator()
    _init_result(orch)

    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ansible-lint", timeout=30),
    ):
        orch._run_playbook_validation([playbook_file])

    assert orch.result is not None
    assert any(
        "timed out" in str(w.get("message", "")).lower() for w in orch.result.warnings
    )


def test_run_playbook_validation_generic_exception(tmp_path: Path) -> None:
    """Test _run_playbook_validation handles unexpected exceptions."""
    playbook_file = tmp_path / "site.yml"
    playbook_file.write_text("---\n")

    orch = _make_orchestrator()
    _init_result(orch)

    with patch("subprocess.run", side_effect=OSError("unexpected")):
        orch._run_playbook_validation([playbook_file])

    assert orch.result is not None
    assert any(
        "Validation error" in str(w.get("message", "")) for w in orch.result.warnings
    )


# ---------------------------------------------------------------------------
# Lines 1578-1579: _optimize_generated_playbooks with no playbooks
# ---------------------------------------------------------------------------


def test_optimize_generated_playbooks_empty() -> None:
    """Test _optimize_generated_playbooks returns early when no playbooks."""
    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None
    orch.result.playbooks_generated = []

    orch._optimize_generated_playbooks()

    assert orch.result.optimization_metrics == {}


# ---------------------------------------------------------------------------
# Line 1610: _finalize_audit_trail with no audit trail
# ---------------------------------------------------------------------------


def test_finalize_audit_trail_no_trail() -> None:
    """Test _finalize_audit_trail returns early when audit_trail is None."""
    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None
    orch.result.audit_trail = None

    orch._finalize_audit_trail()  # Should not raise


# ---------------------------------------------------------------------------
# Lines 1637-1638: _finalize_audit_trail export failure
# ---------------------------------------------------------------------------


def test_finalize_audit_trail_export_failure() -> None:
    """Test _finalize_audit_trail handles export exceptions gracefully."""
    from souschef.converters.conversion_audit import ConversionAuditTrail

    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None

    audit = ConversionAuditTrail(
        migration_id=orch.migration_id,
        cookbook_name="test_cookbook",
    )
    orch.result.audit_trail = audit

    with patch.object(
        ConversionAuditTrail,
        "export_json",
        side_effect=OSError("disk full"),
    ):
        orch._finalize_audit_trail()  # Should not raise


# ---------------------------------------------------------------------------
# Line 1753: non-dict node in _populate_inventory_from_chef_nodes
# ---------------------------------------------------------------------------


def test_populate_inventory_non_dict_node() -> None:
    """Test _populate_inventory_from_chef_nodes skips non-dict nodes."""
    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None
    orch.result.chef_nodes = ["not-a-dict", 42, None]  # type: ignore[list-item]

    mock_client = MagicMock()

    orch._populate_inventory_from_chef_nodes(mock_client, inventory_id=1)

    mock_client.add_host.assert_not_called()


# ---------------------------------------------------------------------------
# Lines 1757-1764: missing hostname in _populate_inventory_from_chef_nodes
# ---------------------------------------------------------------------------


def test_populate_inventory_missing_hostname() -> None:
    """Test _populate_inventory_from_chef_nodes warns when hostname not resolved."""
    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None
    orch.result.chef_nodes = [{"name": None, "ipaddress": None}]

    mock_client = MagicMock()

    with patch.object(orch, "_resolve_chef_hostname", return_value=None):
        orch._populate_inventory_from_chef_nodes(mock_client, inventory_id=1)

    assert any(
        "missing hostname" in str(w.get("message", "")).lower()
        for w in orch.result.warnings
    )


# ---------------------------------------------------------------------------
# Lines 1777-1778: add_host exception in _populate_inventory_from_chef_nodes
# ---------------------------------------------------------------------------


def test_populate_inventory_add_host_exception() -> None:
    """Test _populate_inventory_from_chef_nodes handles add_host exceptions."""
    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None
    orch.result.chef_nodes = [{"name": "web01"}]

    mock_client = MagicMock()
    mock_client.add_host.side_effect = RuntimeError("API error")

    with (
        patch.object(orch, "_resolve_chef_hostname", return_value="web01"),
        patch.object(orch, "_build_chef_host_variables", return_value={}),
    ):
        orch._populate_inventory_from_chef_nodes(mock_client, inventory_id=1)

    assert any(
        "Failed to add host" in str(w.get("message", "")) for w in orch.result.warnings
    )


# ---------------------------------------------------------------------------
# Lines 1858, 1862: non-dict node / no hostname in _extract_chef_environments_and_roles
# ---------------------------------------------------------------------------


def test_extract_chef_environments_non_dict_node() -> None:
    """Test _extract_chef_environments_and_roles skips non-dict nodes."""
    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None
    orch.result.chef_nodes = ["not-a-dict", 99]  # type: ignore[list-item]

    envs, roles, _, _ = orch._extract_chef_environments_and_roles()

    assert len(envs) == 0
    assert len(roles) == 0


def test_extract_chef_environments_no_hostname() -> None:
    """Test _extract_chef_environments_and_roles skips nodes without hostname."""
    orch = _make_orchestrator()
    _init_result(orch)
    assert orch.result is not None
    orch.result.chef_nodes = [{"name": None, "ipaddress": None}]

    with patch.object(orch, "_resolve_chef_hostname", return_value=None):
        _, _, env_map, _ = orch._extract_chef_environments_and_roles()

    assert len(env_map) == 0


# ---------------------------------------------------------------------------
# Lines 2028-2029: exception in _assign_host_to_env_group
# ---------------------------------------------------------------------------


def test_assign_host_to_env_group_exception() -> None:
    """Test _assign_host_to_env_group handles add_host_to_group exceptions."""
    orch = _make_orchestrator()
    _init_result(orch)

    mock_client = MagicMock()
    mock_client.add_host_to_group.side_effect = RuntimeError("group error")

    orch._assign_host_to_env_group(
        client=mock_client,
        inventory_id=1,
        hostname="web01",
        host_id=42,
        env_groups={"production": 10},
        node_env_map={"web01": "production"},
    )
    # Should log warning without raising


# ---------------------------------------------------------------------------
# Lines 2051-2052: exception in _assign_host_to_role_groups
# ---------------------------------------------------------------------------


def test_assign_host_to_role_groups_exception() -> None:
    """Test _assign_host_to_role_groups handles add_host_to_group exceptions."""
    orch = _make_orchestrator()
    _init_result(orch)

    mock_client = MagicMock()
    mock_client.add_host_to_group.side_effect = RuntimeError("role group error")

    orch._assign_host_to_role_groups(
        client=mock_client,
        inventory_id=1,
        hostname="web01",
        host_id=42,
        role_groups={"webserver": 20},
        node_roles_map={"web01": ["webserver"]},
    )
    # Should log warning without raising


# ---------------------------------------------------------------------------
# Lines 2120-2122: _create_execution_environment with AWXClient
# ---------------------------------------------------------------------------


def test_create_execution_environment_awx() -> None:
    """Test _create_execution_environment creates EE for AWXClient."""
    from souschef.api_clients import AWXClient

    orch = _make_orchestrator()
    _init_result(orch)

    mock_client = MagicMock(spec=AWXClient)
    mock_client.create_execution_environment.return_value = {"id": "99"}

    result = orch._create_execution_environment(mock_client)

    assert result == 99
    mock_client.create_execution_environment.assert_called_once()


def test_create_execution_environment_tower() -> None:
    """Test _create_execution_environment returns 0 for non-AWX/AAP clients."""
    from souschef.api_clients import AnsiblePlatformClient

    orch = _make_orchestrator()
    _init_result(orch)

    mock_client = MagicMock(spec=AnsiblePlatformClient)

    result = orch._create_execution_environment(mock_client)

    assert result == 0


# ---------------------------------------------------------------------------
# Lines 2275, 2278: load_state – JSON parse error and non-dict payload
# ---------------------------------------------------------------------------


def test_load_state_json_parse_error() -> None:
    """Test load_state skips entries that cannot be JSON-decoded."""
    mock_entry = MagicMock()
    mock_entry.conversion_data = "not-valid-json"

    mock_storage = MagicMock()
    mock_storage.get_conversion_history.return_value = [mock_entry]

    result = MigrationOrchestrator.load_state(
        "nonexistent-id", storage_manager=mock_storage
    )

    assert result is None


def test_load_state_non_dict_payload() -> None:
    """Test load_state skips entries where JSON decodes to non-dict."""
    mock_entry = MagicMock()
    mock_entry.conversion_data = json.dumps(["list", "not", "dict"])

    mock_storage = MagicMock()
    mock_storage.get_conversion_history.return_value = [mock_entry]

    result = MigrationOrchestrator.load_state(
        "nonexistent-id", storage_manager=mock_storage
    )

    assert result is None


# ---------------------------------------------------------------------------
# Lines 2284-2285: load_state – fallback when payload has migration_id directly
# ---------------------------------------------------------------------------


def test_load_state_fallback_direct_payload() -> None:
    """Test load_state uses payload directly when migration_result key is absent."""
    from datetime import datetime

    target_id = "test-mig-fallback"
    payload = {
        "migration_id": target_id,
        "status": "converted",
        "chef_version": "18",
        "target_platform": "awx",
        "target_version": "23",
        "ansible_version": "2.15",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "source_cookbook": "/tmp/cb",
    }

    mock_entry = MagicMock()
    mock_entry.conversion_data = json.dumps(payload)

    mock_storage = MagicMock()
    mock_storage.get_conversion_history.return_value = [mock_entry]

    result = MigrationOrchestrator.load_state(target_id, storage_manager=mock_storage)

    assert result is not None
    assert result.migration_id == target_id


# ---------------------------------------------------------------------------
# Line 2292: _resolve_conversion_status raises when result is None
# ---------------------------------------------------------------------------


def test_resolve_conversion_status_no_result() -> None:
    """Test _resolve_conversion_status raises RuntimeError when result is None."""
    orch = _make_orchestrator()
    orch.result = None

    with pytest.raises(RuntimeError, match="No migration result"):
        orch._resolve_conversion_status()
