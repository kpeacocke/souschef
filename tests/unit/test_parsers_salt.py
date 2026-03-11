"""Tests for souschef/parsers/salt.py."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.parsers.salt import (
    _extract_grains,
    _extract_pillars,
    _extract_state_id_and_module,
    _list_sls_files,
    _parse_sls_states,
    _parse_sls_yaml,
    _summarise_states,
    parse_salt_directory,
    parse_salt_pillar,
    parse_salt_sls,
    parse_salt_top,
)


# ---------------------------------------------------------------------------
# _parse_sls_yaml
# ---------------------------------------------------------------------------


def test_parse_sls_yaml_simple_dict() -> None:
    """Simple YAML dict is parsed correctly."""
    content = "key: value\nnested:\n  a: 1\n"
    result = _parse_sls_yaml(content)
    assert result["key"] == "value"
    assert result["nested"]["a"] == 1


def test_parse_sls_yaml_strips_jinja_blocks() -> None:
    """Jinja2 block tags are stripped before YAML parsing."""
    content = "{% if true %}\nkey: value\n{% endif %}\n"
    result = _parse_sls_yaml(content)
    assert "key" in result


def test_parse_sls_yaml_replaces_jinja_expressions() -> None:
    """Jinja2 inline expressions are replaced with a placeholder string."""
    content = "name: {{ pillar['mykey'] }}\n"
    result = _parse_sls_yaml(content)
    assert "name" in result


def test_parse_sls_yaml_invalid_returns_empty() -> None:
    """Invalid YAML returns an empty dict."""
    content = "{{{{ totally: invalid: yaml"
    result = _parse_sls_yaml(content)
    assert result == {}


def test_parse_sls_yaml_non_dict_returns_empty() -> None:
    """YAML that parses to a non-dict returns empty dict."""
    content = "- item1\n- item2\n"
    result = _parse_sls_yaml(content)
    assert result == {}


# ---------------------------------------------------------------------------
# _extract_state_id_and_module
# ---------------------------------------------------------------------------


def test_extract_state_id_simple_pkg_installed() -> None:
    """Simple pkg.installed state is extracted correctly (list format)."""
    state_def = [{"pkg.installed": [{"name": "nginx"}]}]
    entries = _extract_state_id_and_module("nginx_pkg", state_def)
    assert len(entries) == 1
    assert entries[0]["module"] == "pkg"
    assert entries[0]["function"] == "installed"
    assert entries[0]["category"] == "package"
    assert entries[0]["args"]["name"] == "nginx"


def test_extract_state_id_dict_format() -> None:
    """Simple SLS dict format (pkg.installed as dict key) is supported."""
    state_def = {"pkg.installed": [{"name": "nginx"}]}
    entries = _extract_state_id_and_module("nginx_pkg", state_def)
    assert len(entries) == 1
    assert entries[0]["module"] == "pkg"
    assert entries[0]["function"] == "installed"
    assert entries[0]["args"]["name"] == "nginx"


def test_extract_state_id_service_running() -> None:
    """service.running state is extracted correctly."""
    state_def = [{"service.running": [{"name": "nginx"}, {"enable": True}]}]
    entries = _extract_state_id_and_module("nginx_service", state_def)
    assert len(entries) == 1
    assert entries[0]["module"] == "service"
    assert entries[0]["function"] == "running"


def test_extract_state_id_non_list_non_dict_ignored() -> None:
    """Non-list, non-dict state_def (e.g. string) returns empty list."""
    assert _extract_state_id_and_module("x", "not a list or dict") == []


def test_extract_state_id_non_dict_items_skipped() -> None:
    """Non-dict items inside state list are skipped."""
    state_def = ["string_item", {"file.managed": []}]
    entries = _extract_state_id_and_module("myid", state_def)
    assert len(entries) == 1
    assert entries[0]["module"] == "file"


def test_extract_state_id_no_dot_in_key_skipped() -> None:
    """Items without dot notation in key are skipped."""
    state_def = [{"not_a_module": []}]
    entries = _extract_state_id_and_module("myid", state_def)
    assert entries == []


def test_extract_state_id_dict_args() -> None:
    """Dict-style args (not list) are handled correctly."""
    state_def = [{"cmd.run": {"name": "echo hello"}}]
    entries = _extract_state_id_and_module("run_cmd", state_def)
    assert len(entries) == 1
    assert entries[0]["args"]["name"] == "echo hello"


def test_extract_state_id_unknown_module_category() -> None:
    """Unknown module gets 'unknown' category."""
    state_def = [{"custom.state": []}]
    entries = _extract_state_id_and_module("custom_id", state_def)
    assert entries[0]["category"] == "unknown"


# ---------------------------------------------------------------------------
# _extract_pillars
# ---------------------------------------------------------------------------


def test_extract_pillars_direct_access() -> None:
    """pillar['key'] pattern is detected."""
    content = "name: {{ pillar['db_password'] }}"
    pillars = _extract_pillars(content)
    assert "db_password" in pillars
    assert pillars["db_password"]["access"] == "direct"


def test_extract_pillars_get_with_default() -> None:
    """pillar.get('key', 'default') pattern is detected."""
    content = "name: {{ pillar.get('port', '5432') }}"
    pillars = _extract_pillars(content)
    assert "port" in pillars
    assert pillars["port"]["default"] == "5432"


def test_extract_pillars_salt_call() -> None:
    """salt['pillar.get']('key') pattern is detected."""
    content = "{{ salt['pillar.get']('redis_host', 'localhost') }}"
    pillars = _extract_pillars(content)
    assert "redis_host" in pillars
    assert pillars["redis_host"]["access"] == "salt_call"
    assert pillars["redis_host"]["default"] == "localhost"


def test_extract_pillars_empty_content() -> None:
    """Empty content returns empty dict."""
    assert _extract_pillars("") == {}


def test_extract_pillars_no_default() -> None:
    """pillar.get without default returns None default."""
    content = "{{ pillar.get('key') }}"
    pillars = _extract_pillars(content)
    assert "key" in pillars
    assert pillars["key"]["default"] is None


# ---------------------------------------------------------------------------
# _extract_grains
# ---------------------------------------------------------------------------


def test_extract_grains_direct() -> None:
    """grains['key'] pattern is detected."""
    content = "{{ grains['os'] }}"
    grains = _extract_grains(content)
    assert "os" in grains


def test_extract_grains_get() -> None:
    """grains.get('key') pattern is detected."""
    content = "{{ grains.get('os_family') }}"
    grains = _extract_grains(content)
    assert "os_family" in grains


def test_extract_grains_deduplicates() -> None:
    """Duplicate grain keys are deduplicated."""
    content = "{{ grains['os'] }} {{ grains.get('os') }}"
    grains = _extract_grains(content)
    assert grains.count("os") == 1


def test_extract_grains_empty() -> None:
    """Empty content returns empty list."""
    assert _extract_grains("") == []


# ---------------------------------------------------------------------------
# _summarise_states
# ---------------------------------------------------------------------------


def test_summarise_states_counts_by_category() -> None:
    """States are counted by category correctly."""
    states = [
        {"category": "package"},
        {"category": "package"},
        {"category": "service"},
    ]
    summary = _summarise_states(states)
    assert summary["package"] == 2
    assert summary["service"] == 1


def test_summarise_states_empty() -> None:
    """Empty states list returns empty summary."""
    assert _summarise_states([]) == {}


# ---------------------------------------------------------------------------
# _parse_sls_states
# ---------------------------------------------------------------------------


def test_parse_sls_states_full_sls() -> None:
    """Parses a realistic SLS file into state list."""
    content = """
nginx:
  pkg.installed:
    - name: nginx
nginx_service:
  service.running:
    - name: nginx
    - enable: true
"""
    states = _parse_sls_states(content)
    modules = [s["module"] for s in states]
    assert "pkg" in modules
    assert "service" in modules


def test_parse_sls_states_skips_include() -> None:
    """Top-level 'include' key is skipped."""
    content = "include:\n  - common\n"
    states = _parse_sls_states(content)
    assert states == []


def test_parse_sls_states_skips_extend() -> None:
    """Top-level 'extend' key is skipped."""
    content = "extend:\n  nginx:\n    pkg.installed:\n      - name: nginx\n"
    states = _parse_sls_states(content)
    assert states == []


# ---------------------------------------------------------------------------
# _list_sls_files
# ---------------------------------------------------------------------------


def test_list_sls_files(tmp_path: Path) -> None:
    """SLS files are listed recursively."""
    (tmp_path / "states").mkdir()
    (tmp_path / "states" / "init.sls").write_text("# sls", encoding="utf-8")
    (tmp_path / "states" / "sub").mkdir()
    (tmp_path / "states" / "sub" / "install.sls").write_text("# sls", encoding="utf-8")
    files = _list_sls_files(tmp_path)
    assert len(files) == 2
    assert all(f.endswith(".sls") for f in files)


def test_list_sls_files_empty_dir(tmp_path: Path) -> None:
    """Empty directory returns empty list."""
    assert _list_sls_files(tmp_path) == []


# ---------------------------------------------------------------------------
# parse_salt_sls (integration via tmp_path)
# ---------------------------------------------------------------------------


def test_parse_salt_sls_valid_file(tmp_path: Path) -> None:
    """Valid SLS file is parsed and returns JSON result."""
    sls = tmp_path / "init.sls"
    sls.write_text(
        "nginx:\n  pkg.installed:\n    - name: nginx\n",
        encoding="utf-8",
    )

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=sls),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=sls),
        patch("souschef.parsers.salt.safe_read_text", return_value=sls.read_text()),
    ):
        result_str = parse_salt_sls(str(sls))

    result = json.loads(result_str)
    assert result["summary"]["total_states"] == 1
    assert result["summary"]["by_category"]["package"] == 1


def test_parse_salt_sls_file_not_found(tmp_path: Path) -> None:
    """Missing SLS file returns file-not-found error."""
    missing = tmp_path / "missing.sls"

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=missing),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=missing),
    ):
        result = parse_salt_sls(str(missing))

    assert "Error" in result or "not found" in result.lower()


def test_parse_salt_sls_directory_path(tmp_path: Path) -> None:
    """Directory path returns is-directory error."""
    with (
        patch("souschef.parsers.salt._normalize_path", return_value=tmp_path),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=tmp_path),
    ):
        result = parse_salt_sls(str(tmp_path))

    assert "Error" in result or "directory" in result.lower()


def test_parse_salt_sls_permission_error(tmp_path: Path) -> None:
    """Permission error is handled gracefully."""
    sls = tmp_path / "secret.sls"
    with (
        patch("souschef.parsers.salt._normalize_path", return_value=sls),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.parsers.salt._ensure_within_base_path",
            side_effect=PermissionError("denied"),
        ),
    ):
        result = parse_salt_sls(str(sls))

    assert "Error" in result or "permission" in result.lower()


def test_parse_salt_sls_value_error(tmp_path: Path) -> None:
    """ValueError from path validation is returned as error string."""
    with patch(
        "souschef.parsers.salt._normalize_path",
        side_effect=ValueError("bad path"),
    ):
        result = parse_salt_sls("bad_path")

    assert "Error" in result or "bad path" in result


def test_parse_salt_sls_with_pillars(tmp_path: Path) -> None:
    """Pillar references are extracted into provenance mapping."""
    content = (
        "web:\n"
        "  pkg.installed:\n"
        "    - name: {{ pillar['web_package'] }}\n"
    )
    sls = tmp_path / "web.sls"
    sls.write_text(content, encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=sls),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=sls),
        patch("souschef.parsers.salt.safe_read_text", return_value=content),
    ):
        result_str = parse_salt_sls(str(sls))

    result = json.loads(result_str)
    assert "web_package" in result["summary"]["pillar_keys"]


def test_parse_salt_sls_multiple_states(tmp_path: Path) -> None:
    """Multiple state types are parsed correctly."""
    content = """
install_nginx:
  pkg.installed:
    - name: nginx
start_nginx:
  service.running:
    - name: nginx
nginx_config:
  file.managed:
    - name: /etc/nginx/nginx.conf
    - source: salt://nginx/nginx.conf
run_test:
  cmd.run:
    - name: nginx -t
create_user:
  user.present:
    - name: webmaster
create_group:
  group.present:
    - name: webmasters
"""
    sls = tmp_path / "nginx.sls"
    sls.write_text(content, encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=sls),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=sls),
        patch("souschef.parsers.salt.safe_read_text", return_value=content),
    ):
        result_str = parse_salt_sls(str(sls))

    result = json.loads(result_str)
    assert result["summary"]["total_states"] == 6
    by_cat = result["summary"]["by_category"]
    assert by_cat["package"] == 1
    assert by_cat["service"] == 1
    assert by_cat["file"] == 1
    assert by_cat["command"] == 1
    assert by_cat["user"] == 1
    assert by_cat["group"] == 1


# ---------------------------------------------------------------------------
# parse_salt_pillar
# ---------------------------------------------------------------------------


def test_parse_salt_pillar_valid(tmp_path: Path) -> None:
    """Valid pillar file is parsed and variables are extracted."""
    content = "db:\n  host: localhost\n  port: 5432\n"
    pillar = tmp_path / "db.sls"
    pillar.write_text(content, encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=pillar),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=pillar),
        patch("souschef.parsers.salt.safe_read_text", return_value=content),
    ):
        result_str = parse_salt_pillar(str(pillar))

    result = json.loads(result_str)
    assert "db.host" in result["flattened"]
    assert result["flattened"]["db.host"] == "localhost"
    assert result["summary"]["total_keys"] == 2


def test_parse_salt_pillar_file_not_found(tmp_path: Path) -> None:
    """Missing pillar file returns error."""
    missing = tmp_path / "nope.sls"

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=missing),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=missing),
    ):
        result = parse_salt_pillar(str(missing))

    assert "Error" in result or "not found" in result.lower()


def test_parse_salt_pillar_directory(tmp_path: Path) -> None:
    """Directory path returns is-directory error."""
    with (
        patch("souschef.parsers.salt._normalize_path", return_value=tmp_path),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=tmp_path),
    ):
        result = parse_salt_pillar(str(tmp_path))

    assert "Error" in result or "directory" in result.lower()


def test_parse_salt_pillar_permission_error(tmp_path: Path) -> None:
    """Permission error is handled gracefully."""
    pillar = tmp_path / "secret.sls"
    with (
        patch("souschef.parsers.salt._normalize_path", return_value=pillar),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.parsers.salt._ensure_within_base_path",
            side_effect=PermissionError("denied"),
        ),
    ):
        result = parse_salt_pillar(str(pillar))

    assert "Error" in result or "permission" in result.lower()


def test_parse_salt_pillar_value_error(tmp_path: Path) -> None:
    """ValueError from path validation is returned as error string."""
    with patch(
        "souschef.parsers.salt._normalize_path",
        side_effect=ValueError("bad path"),
    ):
        result = parse_salt_pillar("bad_path")

    assert "Error" in result or "bad path" in result


def test_parse_salt_pillar_flat_values(tmp_path: Path) -> None:
    """Flat (non-nested) pillar values are extracted correctly."""
    content = "port: 8080\nhost: localhost\n"
    pillar = tmp_path / "flat.sls"
    pillar.write_text(content, encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=pillar),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=pillar),
        patch("souschef.parsers.salt.safe_read_text", return_value=content),
    ):
        result_str = parse_salt_pillar(str(pillar))

    result = json.loads(result_str)
    assert "port" in result["flattened"]
    assert result["summary"]["total_keys"] == 2


# ---------------------------------------------------------------------------
# parse_salt_top
# ---------------------------------------------------------------------------


def test_parse_salt_top_valid(tmp_path: Path) -> None:
    """Valid top.sls file is parsed with environment and target mappings."""
    content = "base:\n  '*':\n    - common\n    - webserver\n"
    top = tmp_path / "top.sls"
    top.write_text(content, encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=top),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=top),
        patch("souschef.parsers.salt.safe_read_text", return_value=content),
    ):
        result_str = parse_salt_top(str(top))

    result = json.loads(result_str)
    assert "base" in result["environments"]
    assert "common" in result["summary"]["unique_states"]
    assert "webserver" in result["summary"]["unique_states"]
    assert result["summary"]["total_targets"] >= 1


def test_parse_salt_top_file_not_found(tmp_path: Path) -> None:
    """Missing top file returns error."""
    missing = tmp_path / "top.sls"

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=missing),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=missing),
    ):
        result = parse_salt_top(str(missing))

    assert "Error" in result or "not found" in result.lower()


def test_parse_salt_top_directory(tmp_path: Path) -> None:
    """Directory path returns is-directory error."""
    with (
        patch("souschef.parsers.salt._normalize_path", return_value=tmp_path),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=tmp_path),
    ):
        result = parse_salt_top(str(tmp_path))

    assert "Error" in result or "directory" in result.lower()


def test_parse_salt_top_permission_error(tmp_path: Path) -> None:
    """Permission error is handled gracefully."""
    top = tmp_path / "top.sls"
    with (
        patch("souschef.parsers.salt._normalize_path", return_value=top),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.parsers.salt._ensure_within_base_path",
            side_effect=PermissionError("denied"),
        ),
    ):
        result = parse_salt_top(str(top))

    assert "Error" in result or "permission" in result.lower()


def test_parse_salt_top_value_error(tmp_path: Path) -> None:
    """ValueError from path validation is returned as error string."""
    with patch(
        "souschef.parsers.salt._normalize_path",
        side_effect=ValueError("bad path"),
    ):
        result = parse_salt_top("bad_path")

    assert "Error" in result or "bad path" in result


def test_parse_salt_top_string_state(tmp_path: Path) -> None:
    """Top file with single string state (not list) is handled."""
    content = "base:\n  'web*':\n    - webserver\n"
    top = tmp_path / "top.sls"
    top.write_text(content, encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=top),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=top),
        patch("souschef.parsers.salt.safe_read_text", return_value=content),
    ):
        result_str = parse_salt_top(str(top))

    result = json.loads(result_str)
    assert "webserver" in result["summary"]["unique_states"]


def test_parse_salt_top_non_dict_env_skipped(tmp_path: Path) -> None:
    """Non-dict environment values are silently skipped."""
    content = "base:\n  - not_a_dict\n"
    top = tmp_path / "top.sls"
    top.write_text(content, encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=top),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=top),
        patch("souschef.parsers.salt.safe_read_text", return_value=content),
    ):
        result_str = parse_salt_top(str(top))

    result = json.loads(result_str)
    assert result["summary"]["total_targets"] == 0


# ---------------------------------------------------------------------------
# parse_salt_directory
# ---------------------------------------------------------------------------


def test_parse_salt_directory_valid(tmp_path: Path) -> None:
    """Valid directory with SLS files is scanned correctly."""
    (tmp_path / "top.sls").write_text("base:\n  '*':\n    - common\n", encoding="utf-8")
    (tmp_path / "common.sls").write_text("vim:\n  pkg.installed:\n", encoding="utf-8")
    pillar_dir = tmp_path / "pillar"
    pillar_dir.mkdir()
    (pillar_dir / "webserver.sls").write_text("port: 80\n", encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=tmp_path),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=tmp_path),
    ):
        result_str = parse_salt_directory(str(tmp_path))

    result = json.loads(result_str)
    assert result["summary"]["total_files"] == 3
    assert result["summary"]["top_files"] == 1


def test_parse_salt_directory_not_found(tmp_path: Path) -> None:
    """Missing directory returns error."""
    missing = tmp_path / "nonexistent"

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=missing),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=missing),
    ):
        result = parse_salt_directory(str(missing))

    assert "Error" in result or "not found" in result.lower()


def test_parse_salt_directory_file_path(tmp_path: Path) -> None:
    """File path (not directory) returns appropriate error."""
    sls = tmp_path / "init.sls"
    sls.write_text("# sls", encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=sls),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=sls),
    ):
        result = parse_salt_directory(str(sls))

    assert "Error" in result or "directory" in result.lower()


def test_parse_salt_directory_permission_error(tmp_path: Path) -> None:
    """Permission error is handled gracefully."""
    with (
        patch("souschef.parsers.salt._normalize_path", return_value=tmp_path),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.parsers.salt._ensure_within_base_path",
            side_effect=PermissionError("denied"),
        ),
    ):
        result = parse_salt_directory(str(tmp_path))

    assert "Error" in result or "permission" in result.lower()


def test_parse_salt_directory_value_error(tmp_path: Path) -> None:
    """ValueError from path validation is returned as error string."""
    with patch(
        "souschef.parsers.salt._normalize_path",
        side_effect=ValueError("bad path"),
    ):
        result = parse_salt_directory("bad_path")

    assert "Error" in result or "bad path" in result


def test_parse_salt_directory_empty(tmp_path: Path) -> None:
    """Empty directory returns zero counts."""
    with (
        patch("souschef.parsers.salt._normalize_path", return_value=tmp_path),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=tmp_path),
    ):
        result_str = parse_salt_directory(str(tmp_path))

    result = json.loads(result_str)
    assert result["summary"]["total_files"] == 0


def test_extract_state_id_dict_value_in_list_format() -> None:
    """Dict args inside list-format state entry are handled correctly."""
    # List format where each item has a dict value (not list)
    state_def = [{"cmd.run": {"name": "echo test", "cwd": "/opt"}}]
    entries = _extract_state_id_and_module("run_cmd", state_def)
    assert len(entries) == 1
    assert entries[0]["args"]["name"] == "echo test"
    assert entries[0]["args"]["cwd"] == "/opt"


def test_parse_salt_top_single_string_state_value(tmp_path: Path) -> None:
    """Top file where env value has a single string state (not a list) is handled."""
    # This directly tests the elif isinstance(states, str) branch
    content = "base:\n  'web*': webserver\n"
    top = tmp_path / "top.sls"
    top.write_text(content, encoding="utf-8")

    with (
        patch("souschef.parsers.salt._normalize_path", return_value=top),
        patch("souschef.parsers.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.parsers.salt._ensure_within_base_path", return_value=top),
        patch("souschef.parsers.salt.safe_read_text", return_value=content),
    ):
        result_str = parse_salt_top(str(top))

    result = json.loads(result_str)
    assert "webserver" in result["summary"]["unique_states"]


def test_extract_state_id_dict_format_with_dict_args() -> None:
    """Dict format where the module value is a dict (not list) of args."""
    # Dict format: {module.function: {arg_dict}} instead of {module.function: [arg_list]}
    state_def = {"cmd.run": {"name": "echo test", "cwd": "/opt"}}
    entries = _extract_state_id_and_module("run_cmd", state_def)
    assert len(entries) == 1
    assert entries[0]["args"]["name"] == "echo test"
    assert entries[0]["args"]["cwd"] == "/opt"
