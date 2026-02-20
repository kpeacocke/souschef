"""Tests for Chef search parsing and inventory helpers."""

import json
import os
import tempfile
from pathlib import Path

from souschef.converters import playbook as playbook_helpers


def test_parse_chef_search_query_complex() -> None:
    """Test parsing a complex Chef search query."""
    info = playbook_helpers._parse_chef_search_query("role:web AND environment:prod")

    assert info["index"] == "node"
    assert info["complexity"] == "complex"
    assert len(info["conditions"]) == 2
    assert info["logical_operators"] == ["AND"]


def test_generate_group_name_variants() -> None:
    """Test group name generation for operators."""
    equal = {"key": "role", "value": "web", "operator": "equal"}
    wildcard = {"key": "role", "value": "web*", "operator": "wildcard"}
    regex = {"key": "role", "value": ".*", "operator": "regex"}

    assert playbook_helpers._generate_group_name_from_condition(equal, 0) == "role_web"
    assert playbook_helpers._generate_group_name_from_condition(wildcard, 1) == (
        "role_wildcard_1"
    )
    assert playbook_helpers._generate_group_name_from_condition(regex, 2) == (
        "role_regex_2"
    )


def test_generate_inventory_from_search_role_condition() -> None:
    """Test inventory generation for role search."""
    search_info = {
        "conditions": [{"key": "role", "value": "web", "operator": "equal"}],
        "complexity": "simple",
        "logical_operators": [],
    }

    inventory = playbook_helpers._generate_ansible_inventory_from_search(search_info)

    assert inventory["inventory_type"] == "static"
    assert "role_web" in inventory["groups"]
    assert inventory["variables"]["role_web_role"] == "web"


def test_convert_chef_search_to_inventory_json() -> None:
    """Test converting Chef search query to JSON inventory."""
    result = playbook_helpers.convert_chef_search_to_inventory("role:web")

    data = json.loads(result)
    assert data["inventory_type"]


def test_generate_dynamic_inventory_invalid_json() -> None:
    """Test dynamic inventory returns error for bad JSON."""
    result = playbook_helpers.generate_dynamic_inventory_script("not json")

    assert result.startswith("Error:")


def test_analyse_chef_search_patterns_invalid_path() -> None:
    """Test search pattern analysis with invalid path."""
    result = playbook_helpers.analyse_chef_search_patterns("/invalid/path")

    assert result.startswith("Error:")


def test_analyse_chef_search_patterns_from_file() -> None:
    """Test search pattern analysis from a recipe file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        previous_root = os.environ.get("SOUSCHEF_WORKSPACE_ROOT")
        os.environ["SOUSCHEF_WORKSPACE_ROOT"] = tmpdir
        try:
            recipe_path = Path(tmpdir) / "default.rb"
            recipe_path.write_text(
                "ruby_block 'search' do\n"
                "  block do\n"
                "    search(:node, 'role:web')\n"
                "  end\n"
                "end\n",
                encoding="utf-8",
            )

            result = playbook_helpers.analyse_chef_search_patterns(str(recipe_path))
            data = json.loads(result)

            assert "discovered_searches" in data
        finally:
            if previous_root is None:
                os.environ.pop("SOUSCHEF_WORKSPACE_ROOT", None)
            else:
                os.environ["SOUSCHEF_WORKSPACE_ROOT"] = previous_root


def test_parse_search_condition_variants() -> None:
    """Test search condition parsing for multiple operators."""
    wildcard = playbook_helpers._parse_search_condition("role:web*")
    regex = playbook_helpers._parse_search_condition("role:~web.*")
    not_equal = playbook_helpers._parse_search_condition("role:!web")
    range_cond = playbook_helpers._parse_search_condition("memory:(>1 AND <5)")
    tag = playbook_helpers._parse_search_condition("tags:blue")

    assert wildcard["operator"] == "wildcard"
    assert regex["operator"] == "regex"
    assert not_equal["operator"] == "not_equal"
    assert range_cond["operator"] == "range"
    assert tag["operator"] == "contains"


def test_should_use_dynamic_inventory_for_regex() -> None:
    """Test dynamic inventory detection for regex queries."""
    info = {
        "conditions": [{"key": "role", "value": ".*", "operator": "regex"}],
        "logical_operators": [],
        "complexity": "intermediate",
    }

    assert playbook_helpers._should_use_dynamic_inventory(info) is True
