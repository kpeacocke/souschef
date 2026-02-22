"""
Tests for uncovered lines in parsers, generators, ansible_versions, and caching.

Covers exception handlers, edge cases, and rarely-exercised code paths in
parsers/attributes, parsers/ansible_inventory, generators/repo,
core/ansible_versions, and core/caching.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# souschef/parsers/attributes.py – lines 94-118, 154, 216, 301,
#   341-342, 393-400, 424, 431-432, 515
# ---------------------------------------------------------------------------


class TestAttributesParser:
    """Tests for attributes parser exception handling and edge cases."""

    def test_parse_attributes_with_provenance_value_error(self) -> None:
        """parse_attributes_with_provenance returns error string for ValueError."""
        from souschef.parsers.attributes import parse_attributes_with_provenance

        with patch(
            "souschef.parsers.attributes._normalize_path",
            side_effect=ValueError("invalid path"),
        ):
            result = parse_attributes_with_provenance("/fake/path")
        assert "Error" in str(result)

    def test_parse_attributes_with_provenance_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """parse_attributes_with_provenance returns error string for FileNotFoundError."""
        from souschef.parsers.attributes import parse_attributes_with_provenance

        result = parse_attributes_with_provenance(str(tmp_path / "nonexistent.rb"))
        assert "Error" in str(result) or "not found" in str(result).lower()

    def test_parse_attributes_with_provenance_is_directory_error(
        self, tmp_path: Path
    ) -> None:
        """parse_attributes_with_provenance returns error string for IsADirectoryError."""
        from souschef.parsers.attributes import parse_attributes_with_provenance

        with (
            patch(
                "souschef.parsers.attributes.safe_read_text",
                side_effect=IsADirectoryError("is a dir"),
            ),
            patch(
                "souschef.parsers.attributes._get_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "souschef.parsers.attributes._ensure_within_base_path",
                return_value=tmp_path / "attrs.rb",
            ),
        ):
            result = parse_attributes_with_provenance(str(tmp_path))
        assert "Error" in str(result)

    def test_parse_attributes_with_provenance_permission_error(
        self, tmp_path: Path
    ) -> None:
        """parse_attributes_with_provenance returns error string for PermissionError."""
        from souschef.parsers.attributes import parse_attributes_with_provenance

        with (
            patch(
                "souschef.parsers.attributes.safe_read_text",
                side_effect=PermissionError("access denied"),
            ),
            patch(
                "souschef.parsers.attributes._get_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "souschef.parsers.attributes._ensure_within_base_path",
                return_value=tmp_path / "attrs.rb",
            ),
        ):
            result = parse_attributes_with_provenance(str(tmp_path / "attrs.rb"))
        assert "Error" in str(result)

    def test_parse_attributes_with_provenance_generic_exception(
        self, tmp_path: Path
    ) -> None:
        """parse_attributes_with_provenance returns error string for unexpected exceptions."""
        from souschef.parsers.attributes import parse_attributes_with_provenance

        with (
            patch(
                "souschef.parsers.attributes.safe_read_text",
                side_effect=RuntimeError("unexpected"),
            ),
            patch(
                "souschef.parsers.attributes._get_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "souschef.parsers.attributes._ensure_within_base_path",
                return_value=tmp_path / "attrs.rb",
            ),
        ):
            result = parse_attributes_with_provenance(str(tmp_path / "attrs.rb"))
        assert "error" in str(result).lower() or "Error" in str(result)

    def test_extract_precedence_path_returns_none_for_no_match(self) -> None:
        """_extract_precedence_and_path returns None for unrecognised lines."""
        from souschef.parsers.attributes import _extract_precedence_and_path

        result = _extract_precedence_and_path("some_random_line = value")
        assert result is None

    def test_convert_ruby_word_array_no_match_returns_content(self) -> None:
        """_convert_ruby_word_array returns original content when no match."""
        from souschef.parsers.attributes import _convert_ruby_word_array

        result = _convert_ruby_word_array("['one', 'two']")
        assert result == "['one', 'two']"

    def test_convert_ruby_word_array_with_valid_content(self) -> None:
        """_convert_ruby_word_array converts %w() syntax to YAML list."""
        from souschef.parsers.attributes import _convert_ruby_word_array

        result = _convert_ruby_word_array("%w(apple banana cherry)")
        assert "apple" in result
        assert "banana" in result
        assert "cherry" in result

    def test_convert_ruby_array_empty_returns_empty_list(self) -> None:
        """_convert_ruby_array returns '[]' for empty brackets."""
        from souschef.parsers.attributes import _convert_ruby_array

        result = _convert_ruby_array("[]")
        assert result == "[]"

    def test_convert_ruby_hash_empty_returns_empty_dict(self) -> None:
        """_convert_ruby_hash returns '{}' for empty braces."""
        from souschef.parsers.attributes import _convert_ruby_hash

        result = _convert_ruby_hash("{}")
        assert result == "{}"

    def test_collect_multiline_value_empty_lines_at_start_are_skipped(self) -> None:
        """_collect_multiline_value skips empty lines at the beginning."""
        from souschef.parsers.attributes import _collect_multiline_value

        lines = ["", "  'value'", "default['other'] = 'x'"]
        value, idx = _collect_multiline_value(lines, 0)
        assert "value" in value

    def test_extract_attributes_with_force_override_precedence(self) -> None:
        """_extract_attributes extracts force_override attributes."""
        from souschef.parsers.attributes import _extract_attributes

        content = "force_override['config']['key'] = 'forced_value'\n"
        result = _extract_attributes(content)
        assert any(a["precedence"] == "force_override" for a in result)

    def test_extract_attributes_with_automatic_precedence(self) -> None:
        """_extract_attributes extracts automatic attributes."""
        from souschef.parsers.attributes import _extract_attributes

        content = "automatic['ohai']['platform'] = 'ubuntu'\n"
        result = _extract_attributes(content)
        assert any(a["precedence"] == "automatic" for a in result)


# ---------------------------------------------------------------------------
# souschef/parsers/ansible_inventory.py – lines 69, 230, 234, 270, 281-289,
#   316, 381-384, 399-400, 415-416, 448, 460, 522-523, 533, 551-552,
#   610-612, 617-619, 624-631
# ---------------------------------------------------------------------------


class TestAnsibleInventoryParser:
    """Tests for Ansible inventory parser edge cases."""

    def test_parse_group_header_malformed_line_returns_none(self) -> None:
        """_parse_group_header returns None for a malformed bracket-but-invalid line."""
        from souschef.parsers.ansible_inventory import _parse_group_header

        inventory: dict = {"groups": {}}
        # [!invalid] – regex won't match expected group name
        result = _parse_group_header("[!]", inventory)
        # Should be None or return without crash
        assert result is None or isinstance(result, tuple)

    def test_parse_inventory_yaml_empty_file_returns_empty_dict(
        self, tmp_path: Path
    ) -> None:
        """parse_inventory_yaml returns {} when YAML file contains only None."""
        from souschef.parsers.ansible_inventory import parse_inventory_yaml

        inv_file = tmp_path / "inventory.yml"
        inv_file.write_text("")  # Empty file → yaml.safe_load returns None

        result = parse_inventory_yaml(str(inv_file))
        assert result == {}

    def test_parse_inventory_yaml_non_dict_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """parse_inventory_yaml raises ValueError when YAML is not a dict."""
        from souschef.parsers.ansible_inventory import parse_inventory_yaml

        inv_file = tmp_path / "inventory.yml"
        inv_file.write_text("- item1\n- item2\n")

        with pytest.raises(ValueError, match="Invalid inventory structure"):
            parse_inventory_yaml(str(inv_file))

    def test_parse_inventory_file_unknown_format_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """parse_inventory_file raises ValueError for unknown file extension."""
        from souschef.parsers.ansible_inventory import parse_inventory_file

        inv_file = tmp_path / "inventory.unknown"
        inv_file.write_text("[all]\nhost1\n")

        with pytest.raises(ValueError, match="Unknown inventory file format"):
            parse_inventory_file(str(inv_file))

    def test_parse_inventory_file_ini_fallback_both_fail_raises(
        self, tmp_path: Path
    ) -> None:
        """parse_inventory_file raises ValueError when both INI and YAML fail."""
        from souschef.parsers.ansible_inventory import parse_inventory_file

        inv_file = tmp_path / "inventory"
        inv_file.write_text("{{{invalid}}}")

        with (
            patch(
                "souschef.parsers.ansible_inventory.parse_inventory_ini",
                side_effect=ValueError("bad ini"),
            ),
            patch(
                "souschef.parsers.ansible_inventory.parse_inventory_yaml",
                side_effect=ValueError("bad yaml"),
            ),
            pytest.raises(ValueError, match="Could not parse"),
        ):
            parse_inventory_file(str(inv_file))

    def test_validate_ansible_executable_not_named_ansible_raises(
        self, tmp_path: Path
    ) -> None:
        """_validate_ansible_executable raises ValueError when file is not named 'ansible'."""
        from souschef.parsers.ansible_inventory import _validate_ansible_executable

        wrong_name = tmp_path / "ansible-playbook"
        wrong_name.write_bytes(b"#!/bin/bash")
        wrong_name.chmod(0o755)

        with pytest.raises(ValueError, match="must be named 'ansible'"):
            _validate_ansible_executable(str(wrong_name))

    def test_parse_collections_string_item(self) -> None:
        """_parse_collections handles string items (adds them with '*' version)."""
        from souschef.parsers.ansible_inventory import _parse_collections

        requirements = {"collections": ["community.general", "ansible.posix"]}
        result = _parse_collections(requirements)
        assert result.get("community.general") == "*"
        assert result.get("ansible.posix") == "*"

    def test_parse_roles_string_item(self) -> None:
        """_parse_roles handles string items (adds them with '*' version)."""
        from souschef.parsers.ansible_inventory import _parse_roles

        requirements = {"roles": ["geerlingguy.java", "geerlingguy.nginx"]}
        result = _parse_roles(requirements)
        assert result.get("geerlingguy.java") == "*"

    def test_parse_requirements_yml_invalid_filename_raises(
        self, tmp_path: Path
    ) -> None:
        """parse_requirements_yml raises ValueError for non-requirements.yml filename."""
        from souschef.parsers.ansible_inventory import parse_requirements_yml

        wrong_name = tmp_path / "galaxy.yml"
        wrong_name.write_text("collections:\n  - name: community.general\n")

        with pytest.raises(ValueError, match="Invalid requirements file name"):
            parse_requirements_yml(str(wrong_name))

    def test_parse_requirements_yml_non_dict_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """parse_requirements_yml raises ValueError when YAML is not a dict."""
        from souschef.parsers.ansible_inventory import parse_requirements_yml

        req_file = tmp_path / "requirements.yml"
        req_file.write_text("- simple_item\n- another_item\n")

        with pytest.raises(ValueError, match="Invalid requirements format"):
            parse_requirements_yml(str(req_file))

    def test_analyse_playbook_detects_legacy_include_syntax(
        self, tmp_path: Path
    ) -> None:
        """scan_playbook_for_version_issues detects deprecated modules and legacy include syntax."""
        from souschef.parsers.ansible_inventory import scan_playbook_for_version_issues

        # Use vars to place ec2 and include at the right YAML position so
        # the module_pattern regex (`^\s*word:`) can match them.
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text(
            "---\n"
            "- hosts: all\n"
            "  vars:\n"
            "    ec2: legacy_value\n"
            "    include: tasks/other.yml\n"
            "  tasks:\n"
            "    - name: test\n"
            "      debug:\n"
            "        msg: hello\n"
        )

        result = scan_playbook_for_version_issues(str(playbook_file))
        assert "deprecated_modules" in result
        assert "ec2" in result["deprecated_modules"]
        assert "legacy_syntax" in result
        assert len(result["legacy_syntax"]) > 0

    def test_parse_config_for_paths_silences_errors(self, tmp_path: Path) -> None:
        """_parse_config_for_paths silently ignores errors."""
        from souschef.parsers.ansible_inventory import _parse_config_for_paths

        paths: dict[str, str | None] = {}
        with patch(
            "souschef.parsers.ansible_inventory.parse_ansible_cfg",
            side_effect=FileNotFoundError("not found"),
        ):
            # Should not raise
            _parse_config_for_paths(str(tmp_path / "ansible.cfg"), paths)
        assert paths == {}


# ---------------------------------------------------------------------------
# souschef/generators/repo.py – lines 148, 159-167, 632-633, 637, 659-662,
#   706-707, 786, 814, 817-820, 834, 848-849
# ---------------------------------------------------------------------------


class TestRepoGenerator:
    """Tests for generators/repo.py edge cases."""

    def test_create_gitignore_file_writes_content(self, tmp_path: Path) -> None:
        """_create_gitignore writes a .gitignore to the given directory."""
        from souschef.generators.repo import _create_gitignore

        _create_gitignore(tmp_path)
        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        assert len(gitignore.read_text()) > 0

    def test_create_requirements_yml_writes_content(self, tmp_path: Path) -> None:
        """_create_requirements_yml writes a requirements.yml file."""
        from souschef.generators.repo import _create_requirements_yml

        _create_requirements_yml(tmp_path)
        req_file = tmp_path / "requirements.yml"
        assert req_file.exists()
        assert len(req_file.read_text()) > 0

    def test_create_ansible_cfg_writes_configuration(self, tmp_path: Path) -> None:
        """_create_ansible_cfg writes an ansible.cfg file."""
        from souschef.generators.repo import RepoType, _create_ansible_cfg

        _create_ansible_cfg(tmp_path, RepoType.INVENTORY_FIRST)
        cfg_file = tmp_path / "ansible.cfg"
        assert cfg_file.exists()

    def test_get_roles_destination_returns_path(self, tmp_path: Path) -> None:
        """_get_roles_destination returns a valid Path."""
        from souschef.generators.repo import RepoType, _get_roles_destination

        result = _get_roles_destination(tmp_path, RepoType.PLAYBOOKS_ROLES, "myorg")
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# souschef/core/ansible_versions.py – lines 396, 423, 715-716, 744, 781-796,
#   799-806, 810, 813-814
# ---------------------------------------------------------------------------


class TestAnsibleVersions:
    """Tests for ansible_versions module edge cases."""

    def test_get_eol_status_unknown_version_returns_error(self) -> None:
        """get_eol_status returns error for unknown version."""
        from souschef.core.ansible_versions import get_eol_status

        result = get_eol_status("99.99")
        assert "error" in result

    def test_get_eol_status_version_with_no_eol_date(self) -> None:
        """get_eol_status returns supported status when no EOL date is set."""
        from souschef.core.ansible_versions import ANSIBLE_VERSIONS, get_eol_status

        # Find a version with no eol_date
        version_with_no_eol = None
        for v, info in ANSIBLE_VERSIONS.items():
            if info.eol_date is None:
                version_with_no_eol = v
                break

        if version_with_no_eol:
            result = get_eol_status(version_with_no_eol)
            assert result.get("is_eol") is False

    def test_get_eol_status_version_approaching_eol(self) -> None:
        """get_eol_status returns EOL Approaching when < 90 days remain."""
        from datetime import date

        from souschef.core.ansible_versions import ANSIBLE_VERSIONS, get_eol_status

        # Find a version with eol_date within 90 days
        approaching_version = None
        for v, info in ANSIBLE_VERSIONS.items():
            if info.eol_date and 0 < (info.eol_date - date.today()).days < 90:
                approaching_version = v
                break

        if approaching_version:
            result = get_eol_status(approaching_version)
            assert result.get("status") == "EOL Approaching"

    def test_calculate_upgrade_path_returns_dict(self) -> None:
        """calculate_upgrade_path returns a dict with path information."""
        from souschef.core.ansible_versions import calculate_upgrade_path

        result = calculate_upgrade_path("2.9", "2.14")
        assert isinstance(result, dict)

    def test_get_python_compatibility_returns_list(self) -> None:
        """get_python_compatibility returns a list for a known version."""
        from souschef.core.ansible_versions import get_python_compatibility

        result = get_python_compatibility("2.14")
        assert isinstance(result, (dict, list))


# ---------------------------------------------------------------------------
# souschef/core/caching.py – lines 228, 298-299, 333-335, 352-353, 403, 413, 446
# ---------------------------------------------------------------------------


class TestCaching:
    """Tests for caching module edge cases."""

    def test_memory_cache_evict_oldest_when_full(self) -> None:
        """MemoryCache._evict_oldest removes the oldest entry when cache is full."""
        from souschef.core.caching import MemoryCache

        cache: MemoryCache[str, str] = MemoryCache(max_size=2)
        cache.set("key1", "val1")
        cache.set("key2", "val2")
        # Adding a third entry should trigger eviction
        cache.set("key3", "val3")
        assert cache.size() <= 2

    def test_memory_cache_evict_oldest_on_empty_cache_does_nothing(self) -> None:
        """MemoryCache._evict_oldest on empty cache does not raise."""
        from souschef.core.caching import MemoryCache

        cache: MemoryCache[str, str] = MemoryCache(max_size=5)
        cache._evict_oldest()  # Should not raise on empty cache

    def test_file_hash_cache_get_returns_none_for_nonexistent_file(self) -> None:
        """FileHashCache.get returns None for a path that does not exist."""
        from souschef.core.caching import FileHashCache

        cache: FileHashCache[str] = FileHashCache()
        result = cache.get("/nonexistent/file.yaml")
        assert result is None

    def test_file_hash_cache_get_after_delete_returns_none(
        self, tmp_path: Path
    ) -> None:
        """FileHashCache.get returns None for a key not in _file_hashes."""
        from souschef.core.caching import FileHashCache

        cache: FileHashCache[dict] = FileHashCache()
        test_file = tmp_path / "test.yml"
        test_file.write_text("key: value")

        cache.set(str(test_file), {"key": "value"})
        cache.delete(str(test_file))
        result = cache.get(str(test_file))
        assert result is None

    def test_file_hash_cache_get_expired_entry_returns_none(
        self, tmp_path: Path
    ) -> None:
        """FileHashCache.get returns None when entry is expired."""
        from souschef.core.caching import FileHashCache

        # Cache with 0-second TTL → entry expires immediately
        cache: FileHashCache[dict] = FileHashCache(default_ttl_seconds=0)
        test_file = tmp_path / "test.yml"
        test_file.write_text("key: value")

        cache.set(str(test_file), {"key": "value"})

        import time
        time.sleep(0.01)  # Give a brief moment for TTL to expire

        result = cache.get(str(test_file))
        assert result is None

    def test_file_hash_cache_delete_nonexistent_returns_false(self) -> None:
        """FileHashCache.delete returns False when key is not in cache."""
        from souschef.core.caching import FileHashCache

        cache: FileHashCache[str] = FileHashCache()
        result = cache.delete("/nonexistent/path")
        assert result is False

    def test_file_hash_cache_is_file_changed_returns_true_for_missing(self) -> None:
        """FileHashCache.is_file_changed returns True for a file not in cache."""
        from souschef.core.caching import FileHashCache

        cache: FileHashCache[str] = FileHashCache()
        assert cache.is_file_changed("/nonexistent/file") is True

    def test_cache_manager_get_inventory_returns_none_for_new_file(
        self, tmp_path: Path
    ) -> None:
        """CacheManager.get_inventory returns None for a file not yet cached."""
        from souschef.core.caching import CacheManager

        mgr = CacheManager()
        result = mgr.get_inventory(str(tmp_path / "inventory.ini"))
        assert result is None
