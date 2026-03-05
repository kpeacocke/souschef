"""Targeted branch tests to close the last coverage gaps."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from souschef.ansible_upgrade import _scan_collections, _scan_playbooks
from souschef.cli import cli
from souschef.converters.conversion_audit import (
    ConversionAuditTrail,
    ConversionDecision,
    ResourceConversionRecord,
)
from souschef.core import chef_server as chef_server_core
from souschef.core.chef_server import ChefServerClient, ChefServerConfig
from souschef.core.errors import SousChefError
from souschef.core.path_utils import _resolve_path_under_base
from souschef.ir.plugin import PluginRegistry, SourceParser, TargetGenerator
from souschef.ir.schema import SourceType, TargetType
from souschef.migration_v2 import MigrationOrchestrator
from souschef.parsers.inspec import (
    _convert_file_to_goss,
    _convert_file_to_serverspec,
    _convert_file_to_testinfra,
    _convert_package_to_goss,
    _convert_package_to_serverspec,
    _convert_package_to_testinfra,
    _parse_controls_from_file,
)
from souschef.profiling import (
    PerformanceReport,
    ProfileResult,
    compare_performance,
    generate_cookbook_performance_report,
)
from souschef.storage.database import PostgresStorageManager


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_path_utils_invalid_character_branch(tmp_path: Path) -> None:
    """Invalid characters should be rejected by strict path validation."""
    with pytest.raises(ValueError):
        _resolve_path_under_base("bad*path", str(tmp_path))


def test_path_utils_commonpath_value_error_branch(tmp_path: Path) -> None:
    """Commonpath ValueError should be translated into traversal error."""
    with (
        patch("souschef.core.path_utils.os.path.commonpath", side_effect=ValueError),
        pytest.raises(ValueError),
    ):
        _resolve_path_under_base("relative/file.txt", str(tmp_path))


def test_conversion_audit_duration_and_html_export(tmp_path: Path) -> None:
    """Audit trail should calculate duration and export rows for default CSS class."""
    trail = ConversionAuditTrail(migration_id="m1", cookbook_name="cb")
    trail.start_time = "2026-01-01T00:00:00"
    trail.end_time = "2026-01-01T00:00:05"
    trail.add_resource_record(
        ResourceConversionRecord(
            resource_type="package",
            resource_name="nginx",
            decision=ConversionDecision.NOT_APPLICABLE,
            reason="n/a",
        )
    )
    data = trail.to_dict()
    assert data["duration_seconds"] == 5.0

    out = tmp_path / "audit.html"
    trail.export_html_report(str(out))
    assert out.exists()


def test_plugin_registry_none_paths_and_info() -> None:
    """Plugin registry should return None for unregistered plugins and metadata when registered."""

    class _Parser(SourceParser):
        @property
        def source_type(self) -> SourceType:
            return SourceType.CHEF

        @property
        def supported_versions(self) -> list[str]:
            return ["18"]

        def parse(self, source_path: str, **options):  # type: ignore[no-untyped-def]
            return MagicMock()

        def validate(self, source_path: str) -> dict[str, object]:
            return {"valid": True, "errors": [], "warnings": []}

    class _Generator(TargetGenerator):
        @property
        def target_type(self) -> TargetType:
            return TargetType.ANSIBLE

        @property
        def supported_versions(self) -> list[str]:
            return ["2.17"]

        def generate(self, graph, output_path: str, **options):  # type: ignore[no-untyped-def]
            return None

        def validate_ir(self, graph) -> dict[str, object]:  # type: ignore[no-untyped-def]
            return {"compatible": True, "issues": [], "warnings": []}

    reg = PluginRegistry()
    assert reg.get_parser(SourceType.PUPPET) is None
    assert reg.get_generator(TargetType.TERRAFORM) is None

    reg.register_parser(SourceType.CHEF, _Parser)
    reg.register_generator(TargetType.ANSIBLE, _Generator)
    assert reg.get_generator(TargetType.ANSIBLE) is not None
    info = reg.get_registry_info()
    assert info["parsers"]
    assert info["generators"]


def test_ansible_upgrade_scan_collections_and_playbooks(tmp_path: Path) -> None:
    """Collection and playbook scanning should populate result structures."""
    req = tmp_path / "requirements.yml"
    req.write_text("collections: []")
    pb = tmp_path / "site.yml"
    pb.write_text("---\n- hosts: all\n  tasks: []\n")

    result = {"collections": {}, "playbooks_scanned": 0, "compatibility_issues": []}

    with patch(
        "souschef.ansible_upgrade.parse_requirements_yml", return_value={"a": "1"}
    ):
        _scan_collections(tmp_path, result)

    with patch(
        "souschef.ansible_upgrade.scan_playbook_for_version_issues",
        return_value={"warnings": ["deprecated syntax"]},
    ):
        _scan_playbooks(tmp_path, result)

    assert result["collections"] == {"a": "1"}
    assert result["playbooks_scanned"] >= 1
    assert result["compatibility_issues"]


def test_inspec_converter_branches() -> None:
    """InSpec conversion helpers should extract version/mode/owner branches."""
    lines: list[str] = []
    pkg_expectations = [
        {"matcher": "be_installed", "type": "it", "property": ""},
        {"matcher": "match /1.2/", "type": "its", "property": "version"},
    ]
    _convert_package_to_testinfra(lines, "nginx", pkg_expectations)
    assert any("pkg.version.startswith" in line for line in lines)

    lines = []
    file_expectations = [
        {"matcher": "exist", "type": "it", "property": ""},
        {"matcher": "cmp '0644'", "type": "its", "property": "mode"},
        {"matcher": "eq 'root'", "type": "its", "property": "owner"},
    ]
    _convert_file_to_testinfra(lines, "/etc/nginx/nginx.conf", file_expectations)
    assert any("f.user" in line for line in lines)

    lines = []
    _convert_package_to_serverspec(lines, "nginx", pkg_expectations)
    assert any("match" in line for line in lines)

    lines = []
    _convert_file_to_serverspec(lines, "/tmp/x", file_expectations)
    assert any("owner" in line for line in lines)

    goss_pkg = _convert_package_to_goss(pkg_expectations)
    assert goss_pkg.get("versions") == ["1.2"]

    goss_file = _convert_file_to_goss(file_expectations)
    assert goss_file.get("owner") == "root"


def test_parse_controls_from_file_fallback_read(tmp_path: Path) -> None:
    """Control parsing should fall back to direct read when safe read bases fail."""
    control = tmp_path / "control.rb"
    control.write_text("control 'x' do\n  impact 1.0\n  title 't'\nend\n")

    with patch("souschef.parsers.inspec.safe_read_text", side_effect=ValueError):
        controls = _parse_controls_from_file(control)

    assert controls
    assert controls[0]["file"] == "control.rb"


def test_profiling_nonexistent_path_raises() -> None:
    """Profiling report should raise for missing cookbook path."""
    with pytest.raises(SousChefError):
        generate_cookbook_performance_report("/definitely/missing/cookbook")


def test_profiling_templates_and_compare(tmp_path: Path) -> None:
    """Profiling should include templates and compare function should format report."""
    (tmp_path / "metadata.rb").write_text('name "x"\nversion "1.0.0"')
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "default.rb").write_text("package 'nginx'")
    (tmp_path / "attributes").mkdir()
    (tmp_path / "attributes" / "default.rb").write_text("default['x'] = 1")
    (tmp_path / "resources").mkdir()
    (tmp_path / "resources" / "custom.rb").write_text("resource_name :x")
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "default.erb").write_text("hello <%= @x %>")

    report = generate_cookbook_performance_report(str(tmp_path))
    assert isinstance(report, PerformanceReport)
    assert any("parse_templates" in r.operation_name for r in report.operation_results)

    before = PerformanceReport("cb", total_time=10.0, total_memory=1000)
    after = PerformanceReport("cb", total_time=8.0, total_memory=800)
    text = compare_performance(before, after)
    assert "Performance Comparison" in text

    p_before = ProfileResult("op", execution_time=2.0, peak_memory=200)
    p_after = ProfileResult("op", execution_time=1.0, peak_memory=100)
    assert "Change" in compare_performance(p_before, p_after)


def test_chef_server_client_filters_non_dict_items() -> None:
    """Chef client listing helpers should ignore non-dictionary entries."""
    cfg = ChefServerConfig(
        server_url="https://chef.example.com",
        organisation="default",
        client_name="u",
        client_key="k",
    )
    client = ChefServerClient(cfg)

    payload = {
        "prod": {"url": "u1"},
        "raw": "ignore-me",
    }
    with patch.object(client, "_request", return_value=_FakeResponse(payload)):
        envs = client.list_environments()
        assert envs == [{"name": "prod", "url": "u1"}]

    with patch.object(client, "_request", return_value=_FakeResponse(payload)):
        policies = client.list_policies()
        assert policies == [{"name": "prod", "url": "u1"}]


def test_migration_v2_assign_hosts_exception_branch() -> None:
    """Host-to-group assignment should record warnings on API failures."""
    orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")
    orchestrator.result = SimpleNamespace(warnings=[])

    client = SimpleNamespace(
        server_url="https://awx.example.com",
        session=SimpleNamespace(
            get=MagicMock(side_effect=RuntimeError("boom")),
        ),
    )

    orchestrator._assign_hosts_to_created_groups(  # pylint: disable=protected-access
        client=client,
        inventory_id=1,
        env_groups={},
        role_groups={},
        node_env_map={},
        node_roles_map={},
    )

    assert orchestrator.result.warnings


def test_cli_convert_json_importerror_branch() -> None:
    """CLI convert command should fall back to YAML output when yaml import fails."""
    runner = CliRunner()

    orig_import = __import__

    def fake_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "yaml":
            raise ImportError("no yaml")
        return orig_import(name, *args, **kwargs)

    with (
        patch("souschef.cli.convert_resource_to_task", return_value="x: 1"),
        patch("builtins.__import__", side_effect=fake_import),
    ):
        result = runner.invoke(
            cli,
            ["convert", "package", "nginx", "--format", "json"],
        )
    assert result.exit_code == 0
    assert "Warning: PyYAML not installed" in result.output


def test_cli_convert_json_generic_exception_branch() -> None:
    """CLI convert command should output raw data when YAML parsing fails."""
    runner = CliRunner()

    class _YamlStub:
        @staticmethod
        def safe_load(_value: str):
            raise RuntimeError("parse failed")

    with (
        patch("souschef.cli.convert_resource_to_task", return_value="not yaml"),
        patch.dict("sys.modules", {"yaml": _YamlStub()}),
    ):
        result = runner.invoke(
            cli,
            ["convert", "package", "nginx", "--format", "json"],
        )
    assert result.exit_code == 0
    assert "not yaml" in result.output


def test_cli_ls_error_path_exits() -> None:
    """CLI ls should exit non-zero on error string responses."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("existing").mkdir()
        with patch("souschef.cli.list_directory", return_value="Error: missing"):
            result = runner.invoke(cli, ["ls", "existing"])

    assert result.exit_code == 1


def test_cli_ui_importerror_branch() -> None:
    """CLI ui should handle ImportError branch gracefully."""
    runner = CliRunner()
    with patch("subprocess.run", side_effect=ImportError("streamlit missing")):
        result = runner.invoke(cli, ["ui", "--port", "8502"])
    assert result.exit_code == 1
    assert "Streamlit is not installed" in result.output


def test_playbook_error_branches() -> None:
    """Playbook helpers should return error strings for unexpected exceptions."""
    from souschef.converters import playbook

    with patch(
        "souschef.converters.playbook.parse_recipe", side_effect=RuntimeError("boom")
    ):
        result = playbook.generate_playbook_from_recipe("/tmp/recipe.rb")
    assert result.startswith("Error generating playbook:")

    with patch(
        "souschef.converters.playbook._normalize_path",
        side_effect=RuntimeError("bad path"),
    ):
        result = playbook.analyse_chef_search_patterns("/tmp")
    assert result.startswith("Error analyzing Chef search patterns:")


def test_core_chef_server_connection_error_branch() -> None:
    """Core chef connection validation should surface ConnectionError status."""
    with patch(
        "souschef.core.chef_server._build_client_from_env",
        side_effect=chef_server_core.ConnectionError,
    ):
        success, message = chef_server_core._validate_chef_server_connection(
            "https://chef.example.com",
            "client",
        )
    assert success is False
    assert "Connection error" in message


def test_core_chef_server_wrappers_call_client() -> None:
    """Core wrapper functions should delegate to built client methods."""
    client = SimpleNamespace(
        search_nodes=MagicMock(return_value=[{"name": "n1"}]),
        list_roles=MagicMock(return_value=[{"name": "web"}]),
    )
    with patch("souschef.core.chef_server._build_client_from_env", return_value=client):
        nodes = chef_server_core.get_chef_nodes("name:n1")
        roles = chef_server_core.list_chef_roles()
    assert nodes and roles


def test_cli_history_non_empty_branches() -> None:
    """CLI history command should render both analysis and conversion rows."""
    runner = CliRunner()

    analysis = SimpleNamespace(
        id=1,
        cookbook_name="cb",
        cookbook_version="1.0.0",
        complexity="medium",
        estimated_hours=10.0,
        estimated_hours_with_souschef=6.0,
        created_at="2026-01-01",
    )
    conversion = SimpleNamespace(
        id=2,
        cookbook_name="cb",
        output_type="playbook",
        status="success",
        files_generated=3,
        created_at="2026-01-01",
    )

    storage = MagicMock()
    storage.get_analysis_history.return_value = [analysis]
    storage.get_conversion_history.return_value = [conversion]

    with patch("souschef.storage.get_storage_manager", return_value=storage):
        result = runner.invoke(
            cli,
            ["history", "list", "--type", "both", "--limit", "1"],
        )

    assert result.exit_code == 0
    assert "Analysis History" in result.output
    assert "Conversion History" in result.output


def test_postgres_manager_none_and_exception_branches() -> None:
    """Postgres manager should handle empty rows and exceptions gracefully."""

    class _Cursor:
        def __init__(self, row=None, rowcount=0):
            self._row = row
            self.rowcount = rowcount

        def fetchone(self):
            return self._row

    class _Conn:
        def __init__(self, row=None, rowcount=0, raise_on_execute=False):
            self._row = row
            self._rowcount = rowcount
            self._raise = raise_on_execute

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *_args, **_kwargs):
            if self._raise:
                raise RuntimeError("db error")
            return _Cursor(self._row, self._rowcount)

        def commit(self):
            return None

        def rollback(self):
            return None

    with patch.object(
        PostgresStorageManager, "_ensure_database_exists", lambda self: None
    ):
        mgr = PostgresStorageManager("postgres://example")

    with patch.object(mgr, "_connect", return_value=_Conn(row=None)):
        assert (
            mgr.save_analysis(
                cookbook_name="cb",
                cookbook_path="/tmp/cb",
                cookbook_version="1.0",
                complexity="low",
                estimated_hours=1.0,
                estimated_hours_with_souschef=0.5,
                recommendations="ok",
                analysis_data={},
            )
            is None
        )

    with patch.object(mgr, "_connect", return_value=_Conn(row=None)):
        assert mgr.get_analysis_by_fingerprint("fp") is None
        assert mgr.get_cached_analysis("/tmp/cb") is None

    with patch.object(mgr, "_connect", return_value=_Conn(row=None, rowcount=0)):
        assert mgr.save_conversion("cb", "playbook", "ok", 1, {}) is None

    with patch.object(mgr, "_connect", return_value=_Conn(raise_on_execute=True)):
        assert mgr.delete_analysis(123) is False
        assert mgr.delete_conversion(456) is False


def test_postgres_manager_positive_row_branches() -> None:
    """Postgres manager should return converted rows and success booleans."""

    class _Cursor:
        def __init__(self, row=None, rowcount=0):
            self._row = row
            self.rowcount = rowcount

        def fetchone(self):
            return self._row

    class _Conn:
        def __init__(self, row=None, rowcount=0):
            self._row = row
            self._rowcount = rowcount

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, *_args, **_kwargs):
            if "ALTER TABLE" in sql:
                return _Cursor(None, 0)
            return _Cursor(self._row, self._rowcount)

        def commit(self):
            return None

        def rollback(self):
            return None

    with patch.object(
        PostgresStorageManager, "_ensure_database_exists", lambda self: None
    ):
        mgr = PostgresStorageManager("postgres://example")

    # Cover line that commits after ALTER TABLE in _ensure_database_exists.
    with patch.object(mgr, "_connect", return_value=_Conn()):
        mgr._ensure_database_exists()  # pylint: disable=protected-access

    analysis_row = {
        "id": 9,
        "cookbook_name": "cb",
        "cookbook_path": "/tmp/cb",
        "cookbook_version": "1.0",
        "complexity": "low",
        "estimated_hours": 1.0,
        "estimated_hours_with_souschef": 0.5,
        "recommendations": "ok",
        "analysis_data": "{}",
        "ai_provider": None,
        "ai_model": None,
        "cache_key": "k",
        "cookbook_blob_key": None,
        "created_at": "2026-01-01",
    }
    with patch.object(mgr, "_connect", return_value=_Conn(row={"id": 7})):
        saved_id = mgr.save_analysis(
            cookbook_name="cb",
            cookbook_path="/tmp/cb",
            cookbook_version="1.0",
            complexity="low",
            estimated_hours=1.0,
            estimated_hours_with_souschef=0.5,
            recommendations="ok",
            analysis_data={},
        )
    assert saved_id == 7

    with patch.object(mgr, "_connect", return_value=_Conn(row=analysis_row)):
        assert mgr.get_analysis_by_fingerprint("fp") is not None
        assert mgr.get_cached_analysis("/tmp/cb") is not None

    with patch.object(mgr, "_connect", return_value=_Conn(row={"id": 12})):
        conv_id = mgr.save_conversion("cb", "playbook", "ok", 1, {})
    assert conv_id == 12

    with patch.object(mgr, "_connect", return_value=_Conn(row=None, rowcount=1)):
        assert mgr.delete_analysis(1) is True
        assert mgr.delete_conversion(1) is True
