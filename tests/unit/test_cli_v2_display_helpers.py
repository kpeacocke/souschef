"""Tests for cli_v2_commands display helper functions."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from souschef.cli_v2_commands import (
    _display_migrations_json,
    _display_migrations_text,
)


class TestDisplayMigrationsJson:
    """Test _display_migrations_json helper function."""

    def test_display_migrations_json_empty_list(self, capsys) -> None:
        """Empty conversions list outputs empty JSON array."""
        _display_migrations_json([])

        captured = capsys.readouterr()
        assert "[]" in captured.out

    def test_display_migrations_json_single_conversion(self, capsys) -> None:
        """Single conversion is properly formatted."""
        conv = MagicMock()
        conv.id = 1
        conv.cookbook_name = "test-cookbook"
        conv.output_type = "playbook"
        conv.status = "success"
        conv.files_generated = 5
        conv.created_at = "2025-01-01T00:00:00"
        conv.conversion_data = json.dumps(
            {
                "migration_result": {
                    "migration_id": "mig-12345678",
                    "status": "completed",
                }
            }
        )

        _display_migrations_json([conv])

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output) == 1
        assert output[0]["cookbook_name"] == "test-cookbook"
        assert output[0]["status"] == "success"

    def test_display_migrations_json_missing_migration_data(self, capsys) -> None:
        """Conversion with no migration_data still outputs valid JSON."""
        conv = MagicMock()
        conv.id = 1
        conv.cookbook_name = "cookbook"
        conv.output_type = "playbook"
        conv.status = "failed"
        conv.files_generated = 0
        conv.created_at = "2025-01-01T00:00:00"
        conv.conversion_data = None

        _display_migrations_json([conv])

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output) == 1
        assert output[0]["migration_id"] is None
        assert output[0]["migration_status"] is None


class TestDisplayMigrationsText:
    """Test _display_migrations_text helper function."""

    def test_display_migrations_text_empty_list(self, capsys) -> None:
        """Empty conversions list still shows header."""
        _display_migrations_text([], 50)

        captured = capsys.readouterr()
        assert "Recent Migrations" in captured.out
        assert "0 of 50" in captured.out

    def test_display_migrations_text_single_migration(self, capsys) -> None:
        """Single migration displays formatted output."""
        conv = MagicMock()
        conv.id = 1
        conv.cookbook_name = "test-cookbook"
        conv.status = "success"
        conv.files_generated = 5
        conv.created_at = "2025-01-01T00:00:00"
        conv.conversion_data = json.dumps(
            {
                "migration_result": {
                    "migration_id": "mig-12345678901234567890",
                    "metrics": {"recipes_converted": 5, "recipes_total": 10},
                }
            }
        )

        _display_migrations_text([conv], 20)

        captured = capsys.readouterr()
        assert "test-cookbook" in captured.out
        assert "success" in captured.out
        assert "50.0%" in captured.out

    def test_display_migrations_text_no_metrics(self, capsys) -> None:
        """Migration without metrics doesn't output conversion rate."""
        conv = MagicMock()
        conv.id = 1
        conv.cookbook_name = "cookbook"
        conv.status = "pending"
        conv.files_generated = 0
        conv.created_at = "2025-01-01T00:00:00"
        conv.conversion_data = json.dumps({"migration_result": {}})

        _display_migrations_text([conv], 20)

        captured = capsys.readouterr()
        # Check that output doesn't crash and shows expected data
        assert "cookbook" in captured.out
        assert "pending" in captured.out

    def test_display_migrations_text_multiple_migrations(self, capsys) -> None:
        """Multiple migrations are all displayed."""
        convs = []
        for i in range(3):
            conv = MagicMock()
            conv.id = i + 1
            conv.cookbook_name = f"cookbook-{i}"
            conv.status = "success"
            conv.files_generated = 2
            conv.created_at = f"2025-01-0{i + 1}T00:00:00"
            conv.conversion_data = json.dumps({"migration_result": {}})
            convs.append(conv)

        _display_migrations_text(convs, 50)

        captured = capsys.readouterr()
        assert "cookbook-0" in captured.out
        assert "cookbook-1" in captured.out
        assert "cookbook-2" in captured.out
        assert "3 of 50" in captured.out
