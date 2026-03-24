"""
Consolidated coverage tests for small-gap modules.

Targets:
- souschef/orchestrators/salt.py         line 213
- souschef/assessment.py                 line 282
- souschef/generators/powershell.py      lines 350, 576, 751, 800
- souschef/orchestration.py              lines 87, 106
- souschef/converters/puppet_to_ansible.py  lines 153, 825
- souschef/core/path_utils.py            lines 262-264
- souschef/parsers/puppet.py             line 101
- souschef/ui/pages/__init__.py          line 29
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from unittest.mock import patch

# ---------------------------------------------------------------------------
# orchestrators/salt.py — line 213
# ---------------------------------------------------------------------------


def test_generate_salt_inventory_error_in_top_json() -> None:
    """generate_salt_inventory returns error when top_json has Error key (line 213)."""
    from souschef.orchestrators.salt import generate_salt_inventory

    # top_json must be valid JSON (no JSONDecodeError) AND contain "Error"
    # AND the parsed dict must not have "environments" key.
    error_payload = json.dumps({"Error": "top file failed"})
    with patch(
        "souschef.orchestrators.salt.salt_parser.parse_salt_top",
        return_value=error_payload,
    ):
        result = generate_salt_inventory("/some/top.sls")

    data = json.loads(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# assessment.py — line 282
# ---------------------------------------------------------------------------


def test_normalize_cookbook_root_returns_str_candidate() -> None:
    """_normalize_cookbook_root returns string candidate when _normalize_path returns a non-Path value (line 282)."""
    from souschef.assessment import _normalize_cookbook_root

    # Patch _normalize_path (as used in assessment) to return a plain string.
    with patch(
        "souschef.assessment._normalize_path",
        return_value="/some/cookbook",
    ):
        result = _normalize_cookbook_root("/some/cookbook")

    # result should be the string that was returned by the mock
    assert result == "/some/cookbook"


# ---------------------------------------------------------------------------
# generators/powershell.py — line 350 (warnings.append inside loop)
# ---------------------------------------------------------------------------


def test_generate_powershell_role_structure_with_warning_action() -> None:
    """generate_powershell_role_structure logs a warning when an action has an unknown action_type (line 350)."""
    from souschef.generators.powershell import generate_powershell_role_structure

    ir: dict[str, Any] = {
        "source": "test.ps1",
        "actions": [
            {
                "action_type": "totally_unknown_type",
                "params": {},
                "source_line": 5,
                "raw": "Some-UnknownCmd -Foo bar",
            }
        ],
        "metrics": {},
    }
    result = generate_powershell_role_structure(ir)
    # Result is a text block — should contain task key info
    assert "tasks" in result or "roles" in result or "playbook" in result


# ---------------------------------------------------------------------------
# generators/powershell.py — line 576 (fallback for unrecognised action type
# in analyze_powershell_migration_fidelity)
# ---------------------------------------------------------------------------


def test_analyze_powershell_migration_fidelity_unrecognised_action() -> None:
    """analyze_powershell_migration_fidelity increments fallback for an unrecognised action_type (line 576)."""
    from souschef.generators.powershell import analyze_powershell_migration_fidelity

    ir: dict[str, Any] = {
        "source": "test.ps1",
        "actions": [
            {
                "action_type": "completely_unknown_xyz",
                "params": {},
                "source_line": 1,
                "raw": "Unknown-Cmd",
            }
        ],
        "metrics": {},
    }
    result_str = analyze_powershell_migration_fidelity(ir)
    data = json.loads(result_str)
    # Unrecognised type → fallback count >= 1
    assert data["fallback_actions"] >= 1


# ---------------------------------------------------------------------------
# generators/powershell.py — line 751 (_build_survey_spec break at idx >= 9)
# ---------------------------------------------------------------------------


def test_build_survey_spec_truncates_at_10_fields() -> None:
    """_build_survey_spec stops after 10 survey fields (line 751 break)."""
    from souschef.generators.powershell import _build_survey_spec

    # Create 15 extra vars — only first 10 should appear
    extra_vars = {f"VAR_{i}": f"val{i}" for i in range(15)}
    result = _build_survey_spec(extra_vars)
    assert result["spec"] is not None
    assert len(result["spec"]) == 10


# ---------------------------------------------------------------------------
# generators/powershell.py — line 800 (_build_recommendations fidelity >= 80)
# ---------------------------------------------------------------------------


def test_build_recommendations_good_fidelity_branch() -> None:
    """_build_recommendations includes the 'Good fidelity' message for fidelity of 85 (line 800)."""
    from souschef.generators.powershell import _build_recommendations

    recs = _build_recommendations(
        fidelity=85,
        fallback=1,
        review_required=[],
        metrics={},
    )
    assert any("Good fidelity" in r or "85" in r for r in recs)


# ---------------------------------------------------------------------------
# orchestration.py — lines 87 and 106
# ---------------------------------------------------------------------------


def test_orchestrate_generate_playbook_from_recipe() -> None:
    """orchestrate_generate_playbook_from_recipe delegates to generate_playbook_from_recipe (line 87)."""
    from souschef.orchestration import orchestrate_generate_playbook_from_recipe

    with patch(
        "souschef.orchestration.generate_playbook_from_recipe",
        return_value="playbook yaml",
    ) as mock_fn:
        result = orchestrate_generate_playbook_from_recipe(
            recipe_path="/some/recipe.rb",
            cookbook_path="/some/cookbook",
        )

    mock_fn.assert_called_once_with(
        recipe_path="/some/recipe.rb",
        cookbook_path="/some/cookbook",
    )
    assert result == "playbook yaml"


def test_orchestrate_generate_playbook_from_recipe_with_ai() -> None:
    """orchestrate_generate_playbook_from_recipe_with_ai delegates to generate_playbook_from_recipe_with_ai (line 106)."""
    from souschef.orchestration import (
        orchestrate_generate_playbook_from_recipe_with_ai,
    )

    with patch(
        "souschef.orchestration.generate_playbook_from_recipe_with_ai",
        return_value="ai playbook yaml",
    ) as mock_fn:
        result = orchestrate_generate_playbook_from_recipe_with_ai(
            recipe_path="/some/recipe.rb",
            ai_provider="openai",
            api_key="key123",
            model="gpt-4",
            temperature=0.3,
            max_tokens=4000,
        )

    assert mock_fn.called
    assert result == "ai playbook yaml"


# ---------------------------------------------------------------------------
# converters/puppet_to_ansible.py — lines 153 and 825
# ---------------------------------------------------------------------------


def test_convert_puppet_manifest_to_ansible_value_error(tmp_path: Any) -> None:
    """convert_puppet_manifest_to_ansible returns Error string on ValueError (line 153)."""
    from souschef.converters.puppet_to_ansible import convert_puppet_manifest_to_ansible

    with patch(
        "souschef.converters.puppet_to_ansible._ensure_within_base_path",
        side_effect=ValueError("path escapes workspace"),
    ):
        result = convert_puppet_manifest_to_ansible("/some/manifest.pp")

    assert result.startswith("Error:")
    assert "path escapes workspace" in result


def test_convert_puppet_manifest_to_ansible_with_ai_value_error() -> None:
    """convert_puppet_manifest_to_ansible_with_ai returns Error string on ValueError (line 825)."""
    from souschef.converters.puppet_to_ansible import (
        convert_puppet_manifest_to_ansible_with_ai,
    )

    with patch(
        "souschef.converters.puppet_to_ansible._ensure_within_base_path",
        side_effect=ValueError("path escapes workspace"),
    ):
        result = convert_puppet_manifest_to_ansible_with_ai(
            manifest_path="/some/manifest.pp",
            ai_provider="openai",
            api_key="key",
            model="gpt-4",
            temperature=0.3,
            max_tokens=4000,
        )

    assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# core/path_utils.py — lines 262-264 (ValueError from second commonpath call)
# ---------------------------------------------------------------------------


def test_ensure_within_base_path_second_commonpath_raises_value_error(
    tmp_path: Any,
) -> None:
    """_validate_ui_path raises ValueError when second os.path.commonpath call raises ValueError (lines 262-264)."""
    import pytest

    from souschef.core.path_utils import _ensure_within_base_path

    safe_file = tmp_path / "safe.txt"
    safe_file.write_text("content")

    original_commonpath = os.path.commonpath
    call_count = 0

    def raise_on_second(paths: list[str]) -> str:
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise ValueError("different drives (mocked)")
        return original_commonpath(paths)

    with (
        patch(
            "souschef.core.path_utils.os.path.commonpath",
            side_effect=raise_on_second,
        ),
        pytest.raises(ValueError, match="Path traversal attempt"),
    ):
        _ensure_within_base_path(safe_file, tmp_path)


# ---------------------------------------------------------------------------
# parsers/puppet.py — line 101 (ValueError handler in parse_puppet_manifest)
# ---------------------------------------------------------------------------


def test_parse_puppet_manifest_value_error() -> None:
    """parse_puppet_manifest returns Error string on ValueError (line 101)."""
    from souschef.parsers.puppet import parse_puppet_manifest

    with patch(
        "souschef.parsers.puppet._ensure_within_base_path",
        side_effect=ValueError("path escapes workspace"),
    ):
        result = parse_puppet_manifest("/some/manifest.pp")

    assert result.startswith("Error:")
    assert "path escapes workspace" in result


# ---------------------------------------------------------------------------
# ui/pages/__init__.py — line 29 (importlib.import_module when not in
# sys.modules)
# ---------------------------------------------------------------------------


def test_pages_lazy_import_when_not_in_sys_modules() -> None:
    """_PagesModule.__getattribute__ calls importlib.import_module when a submodule is not already in sys.modules (line 29)."""
    import souschef.ui.pages as pages

    # Temporarily remove one of the exported submodules from sys.modules
    # to force the importlib.import_module branch.
    full_name = "souschef.ui.pages.history"
    saved = sys.modules.pop(full_name, None)
    try:
        module = pages.__getattribute__("history")
        assert module is not None
    finally:
        # Restore sys.modules to its original state
        if saved is not None:
            sys.modules[full_name] = saved
        elif full_name in sys.modules:
            sys.modules.pop(full_name)
