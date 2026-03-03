"""Tests for MigrationOrchestrator helper methods."""

from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from souschef.migration_v2 import (
    MigrationOrchestrator,
    MigrationResult,
    MigrationStatus,
)


class TestMigrationRunListHelpers:
    """Tests for run_list helper methods."""

    def test_normalise_run_list_from_list(self):
        """Test normalising run_list provided as list."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")
        run_list = ["recipe[nginx::default]", "role[web]"]

        result = orchestrator._normalise_run_list(run_list)

        assert result == ["nginx::default", "web"]

    def test_normalise_run_list_from_string(self):
        """Test normalising run_list provided as string."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")
        run_list = "recipe[redis::default],role[cache]"

        result = orchestrator._normalise_run_list(run_list)

        assert result == ["redis::default", "cache"]

    def test_normalise_run_list_from_unknown_type(self):
        """Test normalising run_list with unsupported type."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")

        result = orchestrator._normalise_run_list(123)

        assert result == []

    def test_extract_cookbooks_from_run_list(self):
        """Test extracting cookbooks from run_list values."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")
        run_list = ["nginx::default", "redis", "postgres::server"]

        result = orchestrator._extract_cookbooks_from_run_list(run_list)

        assert result == ["nginx", "redis", "postgres"]

    def test_resolve_primary_cookbook_prefers_name(self):
        """Test resolving primary cookbook when explicit name provided."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")

        result = orchestrator._resolve_primary_cookbook("explicit", ["fallback"])

        assert result == "explicit"

    def test_resolve_primary_cookbook_uses_run_list(self):
        """Test resolving primary cookbook from run_list when name missing."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")

        result = orchestrator._resolve_primary_cookbook(None, ["first", "second"])

        assert result == "first"

    def test_resolve_primary_cookbook_requires_name(self):
        """Test resolving primary cookbook raises without name or run_list."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")

        with pytest.raises(ValueError, match="Cookbook name is required"):
            orchestrator._resolve_primary_cookbook(None, [])

    def test_extract_policy_run_list_prefers_revision(self):
        """Test policy run_list extraction uses revision payload when available."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")
        client = MagicMock()
        client.get_policy_revision.return_value = {
            "run_list": ["recipe[app::install]", "role[web]"]
        }
        policy_payload = {"revision_id": "abc123", "run_list": ["recipe[old::default]"]}

        result = orchestrator._extract_policy_run_list(client, "policy", policy_payload)

        assert result == ["app::install", "web"]

    def test_extract_policy_run_list_uses_latest_revision(self):
        """Test policy run_list with revisions map uses latest key."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")
        client = MagicMock()
        client.get_policy_revision.return_value = {
            "run_list": ["recipe[latest::default]"]
        }
        policy_payload = {
            "revisions": {
                "2024-01-01": {},
                "2024-05-01": {},
            }
        }

        result = orchestrator._extract_policy_run_list(client, "policy", policy_payload)

        assert result == ["latest::default"]

    def test_extract_policy_run_list_falls_back(self):
        """Test policy run_list falls back when revision data missing."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")
        client = MagicMock()
        policy_payload = {"run_list": ["recipe[base::default]", "role[base]"]}

        result = orchestrator._extract_policy_run_list(client, "policy", policy_payload)

        assert result == ["base::default", "base"]


class TestMigrationResultHelpers:
    """Tests for migration result helpers."""

    def test_flatten_dict_expands_paths(self):
        """Test flattening nested dictionaries."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")

        flattened = orchestrator._flatten_dict({"a": {"b": 1}, "c": 2})

        assert flattened == {"a.b": 1, "c": 2}

    def test_format_attribute_value_serialises(self):
        """Test attribute value formatting."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")

        assert orchestrator._format_attribute_value(["a"]) == '["a"]'
        assert orchestrator._format_attribute_value({"k": "v"}) == '{"k": "v"}'
        assert orchestrator._format_attribute_value(3) == "3"

    def test_build_migration_report_includes_conflicts(self):
        """Test report includes conflict count and run list."""
        orchestrator = MigrationOrchestrator("15.10.91", "awx", "24.6.1")
        orchestrator.result = MigrationResult(
            migration_id="mig-test",
            status=MigrationStatus.CONVERTED,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.16.0",
            created_at="now",
            updated_at="now",
            source_cookbook="/tmp/cookbook",  # NOSONAR
            run_list=["nginx::default"],
            variable_provenance={
                "attributes": {
                    "a": {"has_conflict": True, "value": "1"},
                    "b": {"has_conflict": False, "value": "2"},
                }
            },
        )

        report = orchestrator._build_migration_report()

        assert "Attribute conflicts: 1" in report
        assert "Run list:" in report
        assert "nginx::default" in report

    def test_migration_result_round_trip(self):
        """Test MigrationResult to_dict and from_dict."""
        result = MigrationResult(
            migration_id="mig-123",
            status=MigrationStatus.PENDING,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.16.0",
            created_at="now",
            updated_at="later",
            source_cookbook="/tmp/cookbook",  # NOSONAR
        )

        payload = result.to_dict()
        restored = MigrationResult.from_dict(payload)

        assert restored.migration_id == result.migration_id
        assert restored.status == MigrationStatus.PENDING

    def test_migration_result_from_dict_invalid_payload(self):
        """Test from_dict rejects non-dictionary payloads."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            MigrationResult.from_dict(cast(dict[str, Any], "not a dict"))

    def test_migration_result_from_dict_unknown_status(self):
        """Test from_dict uses pending on unknown status values."""
        payload = {
            "migration_id": "mig-xyz",
            "status": "unknown",
            "chef_version": "15.10.91",
            "target_platform": "awx",
            "target_version": "24.6.1",
            "ansible_version": "2.16.0",
            "created_at": "now",
            "updated_at": "now",
            "source_cookbook": "/tmp/cookbook",  # NOSONAR
        }

        restored = MigrationResult.from_dict(payload)

        assert restored.status == MigrationStatus.PENDING
