"""Targeted server.py coverage tests for remaining wrapper and Salt report branches."""

from __future__ import annotations

import json
from unittest.mock import patch

from souschef import server


def test_generate_ansible_role_from_bash_wrapper_calls_internal() -> None:
    """Server wrapper should delegate role generation to internal helper."""
    with patch(
        "souschef.server._generate_ansible_role_from_bash_file",
        return_value='{"status":"success"}',
    ) as mock_internal:
        result = server.generate_ansible_role_from_bash("script.sh", "role")

    assert result == '{"status":"success"}'
    mock_internal.assert_called_once_with("script.sh", "role")


def test_server_wrappers_handle_permission_error() -> None:
    """Path-based wrappers should map PermissionError into contextual error strings."""
    with patch(
        "souschef.server._normalise_workspace_path",
        side_effect=PermissionError("denied"),
    ):
        assert server.parse_template("/x").startswith(
            "Error during validating template path"
        )
        assert server.parse_custom_resource("/x").startswith(
            "Error during validating resource path"
        )
        assert server.list_directory("/x").startswith(
            "Error during validating directory path"
        )
        assert server.read_file("/x").startswith("Error during validating file path")
        assert server.read_cookbook_metadata("/x").startswith(
            "Error during validating metadata path"
        )
        assert server.parse_recipe("/x").startswith(
            "Error during validating recipe path"
        )
        assert server.parse_attributes("/x").startswith(
            "Error during validating attributes path"
        )
        assert server.list_cookbook_structure("/x").startswith(
            "Error during validating cookbook path"
        )


def test_query_salt_master_rejects_invalid_url_format() -> None:
    """query_salt_master should reject malformed URLs before network calls."""
    result = json.loads(server.query_salt_master("not-a-url", "user", "pass"))
    assert result["status"] == "error"
    assert "Invalid master_url format" in result["error"]


def test_assess_salt_migration_complexity_validates_path_length_error() -> None:
    """Path validation errors should be returned from complexity assessment tool."""
    with patch(
        "souschef.server._validate_path_length", side_effect=ValueError("too long")
    ):
        result = server.assess_salt_migration_complexity("x" * 5000)
    assert "Error during validating Salt directory path" in result


def test_assess_salt_migration_complexity_success_path() -> None:
    """Complexity wrapper should delegate after validation passes."""
    with (
        patch("souschef.server._validate_path_length"),
        patch("souschef.server._assess_salt_complexity", return_value="ok") as assess,
    ):
        result = server.assess_salt_migration_complexity("/srv/salt")
    assert result == "ok"
    assess.assert_called_once_with("/srv/salt")


def test_plan_salt_migration_invalid_json_passthrough() -> None:
    """plan_salt_migration should return raw payload when complexity JSON is invalid."""
    with (
        patch("souschef.server._validate_path_length"),
        patch("souschef.server._assess_salt_complexity", return_value="not-json"),
    ):
        result = server.plan_salt_migration("/srv/salt")
    assert result == "not-json"


def test_plan_salt_migration_path_validation_error() -> None:
    """plan_salt_migration should return contextual errors for invalid paths."""
    with patch(
        "souschef.server._validate_path_length", side_effect=ValueError("too long")
    ):
        result = server.plan_salt_migration("x" * 5000)
    assert "Error during validating Salt directory path" in result


def test_plan_salt_migration_error_payload() -> None:
    """plan_salt_migration should return explicit error text from complexity payload."""
    with (
        patch("souschef.server._validate_path_length"),
        patch(
            "souschef.server._assess_salt_complexity",
            return_value=json.dumps({"error": "complexity failed"}),
        ),
    ):
        result = server.plan_salt_migration("/srv/salt")
    assert result == "complexity failed"


def test_plan_salt_migration_builds_markdown_plan() -> None:
    """plan_salt_migration should produce a detailed markdown migration plan."""
    payload = {
        "summary": {
            "complexity_level": "high",
            "total_files": 4,
            "total_states": 55,
            "estimated_effort_days": 20,
            "estimated_effort_days_with_souschef": 12,
            "high_complexity_files": ["a.sls", "b.sls"],
            "module_breakdown": {"cmd": 10, "service": 8, "pkg": 15},
        }
    }
    with (
        patch("souschef.server._validate_path_length"),
        patch(
            "souschef.server._assess_salt_complexity",
            return_value=json.dumps(payload),
        ),
    ):
        result = server.plan_salt_migration(
            "/srv/salt", timeline_weeks=10, target_platform="awx"
        )

    assert "# SaltStack to Ansible Migration Plan" in result
    assert "Target Platform: AWX" in result
    assert "Phase 1" in result


def test_build_salt_migration_report_json_structure() -> None:
    """JSON report builder should include module coverage and metadata."""
    summary = {"complexity_level": "medium"}
    files = [
        {
            "file": "x.sls",
            "complexity_level": "low",
            "state_count": 1,
            "complexity_score": 1.0,
        }
    ]
    module_breakdown = {"pkg": 1, "unknown": 2}

    result = json.loads(
        server._build_salt_migration_report_json(
            "/srv/salt",
            summary,
            files,
            module_breakdown,
        )
    )

    assert result["report_type"] == "salt_migration"
    assert "module_coverage" in result
    assert result["module_coverage"]["pkg"]["supported"] is True
    assert result["module_coverage"]["unknown"]["supported"] is False


def test_generate_salt_migration_report_json_and_markdown() -> None:
    """Report tool should produce both JSON and markdown formats from complexity data."""
    complexity_data = {
        "summary": {
            "complexity_level": "medium",
            "total_files": 2,
            "total_states": 3,
            "estimated_effort_days": 4,
            "estimated_effort_days_with_souschef": 2,
            "estimated_effort_hours": 32,
            "estimated_effort_weeks": "1 week",
            "high_complexity_files": ["complex.sls"],
            "module_breakdown": {"pkg": 1, "service": 1, "custom": 1},
        },
        "files": [
            {
                "file": "a.sls",
                "state_count": 1,
                "complexity_score": 1.1,
                "complexity_level": "low",
            },
            {
                "file": "b.sls",
                "state_count": 2,
                "complexity_score": 5.0,
                "complexity_level": "high",
            },
        ],
    }

    with (
        patch("souschef.server._validate_path_length"),
        patch(
            "souschef.server._assess_salt_complexity",
            return_value=json.dumps(complexity_data),
        ),
    ):
        report_json = server.generate_salt_migration_report(
            "/srv/salt", report_format="json"
        )
        report_md = server.generate_salt_migration_report(
            "/srv/salt", report_format="markdown"
        )

    parsed = json.loads(report_json)
    assert parsed["report_type"] == "salt_migration"
    assert "Executive Summary" in report_md
    assert "Complexity Analysis" in report_md


def test_generate_salt_migration_report_error_and_passthrough() -> None:
    """Report tool should pass through invalid JSON or explicit error payloads."""
    with (
        patch("souschef.server._validate_path_length"),
        patch("souschef.server._assess_salt_complexity", return_value="not-json"),
    ):
        assert server.generate_salt_migration_report("/srv/salt") == "not-json"

    with (
        patch("souschef.server._validate_path_length"),
        patch(
            "souschef.server._assess_salt_complexity",
            return_value=json.dumps({"error": "failed"}),
        ),
    ):
        assert server.generate_salt_migration_report("/srv/salt") == "failed"


def test_generate_salt_migration_report_path_validation_error() -> None:
    """Report tool should return formatted errors on path validation failure."""
    with patch(
        "souschef.server._validate_path_length", side_effect=ValueError("too long")
    ):
        result = server.generate_salt_migration_report("x" * 5000)
    assert "Error during validating Salt directory path" in result


def test_get_module_coverage_maps_supported_and_unsupported() -> None:
    """_get_module_coverage should map known module equivalents and unsupported ones."""
    out = server._get_module_coverage({"pkg": 1, "cmd": 2, "mystery": 3})
    assert out["pkg"]["ansible_equiv"] == "ansible.builtin.package"
    assert out["cmd"]["supported"] is True
    assert out["mystery"]["ansible_equiv"] == "Custom/Manual"


def test_generate_salt_inventory_invalid_json_and_error_marker() -> None:
    """Inventory tool should return JSON errors for parse failures and explicit errors."""
    with (
        patch("souschef.server._validate_path_length"),
        patch("souschef.server._parse_salt_top", return_value="not-json"),
    ):
        result = json.loads(server.generate_salt_inventory("/srv/salt/top.sls"))
    assert "error" in result

    with (
        patch("souschef.server._validate_path_length"),
        patch(
            "souschef.server._parse_salt_top",
            return_value=json.dumps({"Error": "bad top.sls"}),
        ),
    ):
        # hits the `"Error" in top_json and "environments" not in top_data` branch
        result2 = json.loads(server.generate_salt_inventory("/srv/salt/top.sls"))
    assert "error" in result2


def test_generate_salt_inventory_path_validation_error() -> None:
    """generate_salt_inventory should return contextual path validation errors."""
    with patch(
        "souschef.server._validate_path_length", side_effect=ValueError("too long")
    ):
        result = server.generate_salt_inventory("x" * 5000)
    assert "Error during validating top.sls path" in result


def test_generate_salt_inventory_success_extracts_groups_hosts() -> None:
    """Inventory tool should parse inventory text into groups and hosts."""
    top_data = {"environments": {"base": {"*": ["common"]}}}
    with (
        patch("souschef.server._validate_path_length"),
        patch("souschef.server._parse_salt_top", return_value=json.dumps(top_data)),
        patch(
            "souschef.server._top_to_ansible_inventory",
            return_value="[web]\nweb01\nweb02\n[db]\ndb01",
        ),
    ):
        result = json.loads(server.generate_salt_inventory("/srv/salt/top.sls"))

    assert result["groups"] == ["web", "db"]
    assert "web01" in result["hosts"]


def test_convert_salt_wrapper_path_validation_errors() -> None:
    """Salt conversion wrappers should return formatted validation errors."""
    with patch(
        "souschef.server._validate_path_length", side_effect=ValueError("too long")
    ):
        pillar_result = server.convert_salt_pillar_to_vars("x" * 5000)
        dir_result = server.convert_salt_directory_to_ansible("x" * 5000, "out")

    assert pillar_result.startswith("Error during validating pillar path")
    assert dir_result.startswith("Error during validating paths")


def test_convert_salt_wrapper_success_delegation() -> None:
    """Salt conversion wrappers should delegate after successful validation."""
    with (
        patch("souschef.server._validate_path_length"),
        patch(
            "souschef.server._convert_salt_pillar_to_vars", return_value="pillar-ok"
        ) as pillar,
        patch(
            "souschef.server._convert_salt_directory_to_roles", return_value="dir-ok"
        ) as directory,
    ):
        pillar_result = server.convert_salt_pillar_to_vars("/srv/salt/pillar.sls")
        dir_result = server.convert_salt_directory_to_ansible("/srv/salt", "/tmp/out")

    assert pillar_result == "pillar-ok"
    assert dir_result == "dir-ok"
    pillar.assert_called_once_with("/srv/salt/pillar.sls", "yaml")
    directory.assert_called_once_with("/srv/salt", "/tmp/out")


def test_import_puppet_catalog_to_ir_tool_error_json() -> None:
    """import_puppet_catalog_to_ir tool should wrap exceptions as JSON errors."""
    with patch(
        "souschef.server._normalise_workspace_path", side_effect=ValueError("bad path")
    ):
        result = server.import_puppet_catalog_to_ir(
            "https://puppet.example.test",
            "cert.pem",
            "key.pem",
            "web01",
        )

    assert json.loads(result) == {"status": "error", "error": "bad path"}
