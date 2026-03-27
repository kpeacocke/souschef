"""
Tests for coverage gaps in souschef/parsers/salt.py.

Covers: line 440, lines 544-557, lines 629-893 (all complexity-analysis
and dependency-detection functions, plus assess_salt_complexity).
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.parsers.salt import (
    _arg_count_penalty,
    _base_complexity_for_module,
    _collect_state_dependencies,
    _command_function_penalty,
    _count_jinja_markers,
    _dependency_items_to_tokens,
    _detect_salt_dependencies,
    _extract_dependency_arg_dicts,
    _extract_include_dependencies,
    _flatten_dict_to_dot_notation,
    _jinja_penalty,
    _list_sls_files,
    _score_state_complexity,
    assess_salt_complexity,
)

# ---------------------------------------------------------------------------
# _flatten_dict_to_dot_notation — line 440
# ---------------------------------------------------------------------------


def test_flatten_dict_non_dict_input_returns_empty() -> None:
    """Non-dict input hits the early return on line 440."""
    assert _flatten_dict_to_dot_notation("not a dict") == {}
    assert _flatten_dict_to_dot_notation(42) == {}
    assert _flatten_dict_to_dot_notation(["a", "b"]) == {}


def test_flatten_dict_with_prefix_prepends_dot() -> None:
    """Prefix is joined with dot separator."""
    result = _flatten_dict_to_dot_notation({"b": 1}, prefix="a")
    assert result == {"a.b": 1}


# ---------------------------------------------------------------------------
# _list_sls_files — lines 544-546, 548-549, 555-557
# ---------------------------------------------------------------------------


def test_list_sls_files_commonpath_os_error_re_raises(tmp_path: Path) -> None:
    """os.path.commonpath raising ValueError is wrapped and re-raised (lines 544-546)."""
    with (
        patch("os.path.commonpath", side_effect=ValueError("different drives")),
        pytest.raises(
            ValueError,
            match="Path traversal attempt",
        ),
    ):
        _list_sls_files(tmp_path, tmp_path)


def test_list_sls_files_directory_outside_base_raises(tmp_path: Path) -> None:
    """Directory that escapes base_path raises ValueError (lines 548-549)."""
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    dir_b = tmp_path / "b"
    dir_b.mkdir()
    with pytest.raises(ValueError, match="Path traversal attempt"):
        _list_sls_files(dir_a, dir_b)


def test_list_sls_files_relative_to_failure_skips_file(tmp_path: Path) -> None:
    """Paths that fail relative_to are silently skipped (lines 555-557)."""
    # Yield a path that is NOT under tmp_path so relative_to raises
    outside_sls = Path("/some/other/location/not_under_tmp.sls")
    with patch.object(Path, "rglob", return_value=iter([outside_sls])):
        result = _list_sls_files(tmp_path, tmp_path)
    assert result == []


# ---------------------------------------------------------------------------
# _score_state_complexity — lines 629-638
# ---------------------------------------------------------------------------


def test_score_state_complexity_simple_pkg_state() -> None:
    """Simple pkg.installed state scores 0.1 (lines 629-638)."""
    state = {"module": "pkg", "function": "installed", "args": {"name": "nginx"}}
    score = _score_state_complexity(state)
    assert score == pytest.approx(0.1)


def test_score_state_complexity_cmd_run_with_many_jinja_args_capped() -> None:
    """cmd.run with many Jinja args produces score capped at 1.0."""
    args = {f"k{i}": "__JINJA2__" for i in range(6)}
    state = {"module": "cmd", "function": "run", "args": args}
    score = _score_state_complexity(state)
    assert score == pytest.approx(1.0)


def test_score_state_complexity_empty_state_returns_float() -> None:
    """Empty state dict returns a float within [0.0, 1.0]."""
    score = _score_state_complexity({})
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# _base_complexity_for_module — lines 643-649
# ---------------------------------------------------------------------------


def test_base_complexity_complex_modules_return_0_4() -> None:
    """Complex modules return 0.4 (lines 643-646)."""
    for mod in ("cmd", "git", "archive", "mount", "firewall", "sysctl"):
        assert _base_complexity_for_module(mod) == pytest.approx(0.4)


def test_base_complexity_simple_modules_return_0_1() -> None:
    """Simple modules return 0.1 (lines 647-648)."""
    assert _base_complexity_for_module("pkg") == pytest.approx(0.1)
    assert _base_complexity_for_module("service") == pytest.approx(0.1)


def test_base_complexity_unknown_module_returns_0_2() -> None:
    """Unknown modules fall through to return 0.2 (line 649)."""
    assert _base_complexity_for_module("file") == pytest.approx(0.2)
    assert _base_complexity_for_module("custom_module") == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# _command_function_penalty — lines 654-656
# ---------------------------------------------------------------------------


def test_command_function_penalty_cmd_run_script_call() -> None:
    """cmd.run/script/call return 0.2 penalty (lines 654-655)."""
    assert _command_function_penalty("cmd", "run") == pytest.approx(0.2)
    assert _command_function_penalty("cmd", "script") == pytest.approx(0.2)
    assert _command_function_penalty("cmd", "call") == pytest.approx(0.2)


def test_command_function_penalty_no_penalty_cases() -> None:
    """Non-cmd and non-run functions return 0.0 (line 656)."""
    assert _command_function_penalty("pkg", "installed") == pytest.approx(0.0)
    assert _command_function_penalty("cmd", "wait") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _count_jinja_markers — lines 661-667
# ---------------------------------------------------------------------------


def test_count_jinja_markers_string_with_marker() -> None:
    """String containing __JINJA2__ returns 1 (lines 661-662)."""
    assert _count_jinja_markers("__JINJA2__value") == 1


def test_count_jinja_markers_string_without_marker() -> None:
    """String without __JINJA2__ returns 0."""
    assert _count_jinja_markers("plain string") == 0


def test_count_jinja_markers_list_with_markers() -> None:
    """List returns count of items containing __JINJA2__ (lines 663-666)."""
    assert _count_jinja_markers(["__JINJA2__a", "plain", "__JINJA2__b"]) == 2


def test_count_jinja_markers_list_without_markers() -> None:
    """List with no markers returns 0."""
    assert _count_jinja_markers(["a", "b"]) == 0


def test_count_jinja_markers_other_type_returns_zero() -> None:
    """Non-str/list returns 0 (line 667)."""
    assert _count_jinja_markers(42) == 0
    assert _count_jinja_markers(None) == 0


# ---------------------------------------------------------------------------
# _jinja_penalty — lines 672-675
# ---------------------------------------------------------------------------


def test_jinja_penalty_non_dict_returns_zero() -> None:
    """Non-dict args return 0.0 (lines 672-673)."""
    assert _jinja_penalty("not a dict") == pytest.approx(0.0)
    assert _jinja_penalty(None) == pytest.approx(0.0)


def test_jinja_penalty_two_markers() -> None:
    """Two Jinja2 markers produce 0.2 penalty (line 675)."""
    args = {"a": "__JINJA2__x", "b": "__JINJA2__y"}
    assert _jinja_penalty(args) == pytest.approx(0.2)


def test_jinja_penalty_capped_at_0_3() -> None:
    """Penalty is capped at 0.3 regardless of marker count."""
    args = {f"k{i}": "__JINJA2__v" for i in range(10)}
    assert _jinja_penalty(args) == pytest.approx(0.3)


def test_jinja_penalty_no_markers_returns_zero() -> None:
    """Dict with no Jinja markers returns 0.0."""
    assert _jinja_penalty({"a": "plain", "b": "value"}) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _arg_count_penalty — lines 680-687
# ---------------------------------------------------------------------------


def test_arg_count_penalty_non_dict_returns_zero() -> None:
    """Non-dict returns 0.0 (lines 680-681)."""
    assert _arg_count_penalty("not a dict") == pytest.approx(0.0)


def test_arg_count_penalty_up_to_three_args_returns_zero() -> None:
    """0–3 args returns 0.0 (line 687)."""
    assert _arg_count_penalty({}) == pytest.approx(0.0)
    assert _arg_count_penalty({"a": 1, "b": 2, "c": 3}) == pytest.approx(0.0)


def test_arg_count_penalty_four_to_five_args_returns_0_1() -> None:
    """4–5 args returns 0.1 (lines 685-686)."""
    assert _arg_count_penalty({f"k{i}": i for i in range(4)}) == pytest.approx(0.1)
    assert _arg_count_penalty({f"k{i}": i for i in range(5)}) == pytest.approx(0.1)


def test_arg_count_penalty_six_plus_args_returns_0_2() -> None:
    """6+ args returns 0.2 (lines 683-684)."""
    assert _arg_count_penalty({f"k{i}": i for i in range(6)}) == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# _detect_salt_dependencies — lines 705-717
# ---------------------------------------------------------------------------


def test_detect_salt_dependencies_require_dep() -> None:
    """Detects require dependency and maps it to module:id token (lines 705-717)."""
    content = (
        "nginx:\n"
        "  pkg.installed:\n"
        "    - name: nginx\n"
        "nginx_service:\n"
        "  service.running:\n"
        "    - name: nginx\n"
        "    - require:\n"
        "      - pkg: nginx\n"
    )
    deps = _detect_salt_dependencies(content)
    assert "nginx_service" in deps
    assert "pkg:nginx" in deps["nginx_service"]


def test_detect_salt_dependencies_include_key() -> None:
    """Detects include statements via __include__ key."""
    content = "include:\n  - common.ntp\n  - common.users\n"
    deps = _detect_salt_dependencies(content)
    assert "__include__" in deps
    assert "common.ntp" in deps["__include__"]


def test_detect_salt_dependencies_extend_is_skipped() -> None:
    """Extend clause is skipped entirely (lines 709-710)."""
    content = "extend:\n  nginx:\n    service.running:\n      - watch:\n        - pkg: nginx\n"
    deps = _detect_salt_dependencies(content)
    assert "extend" not in deps


def test_detect_salt_dependencies_no_deps_for_simple_state() -> None:
    """State without dependency keywords returns empty entries."""
    content = "nginx:\n  pkg.installed:\n    - name: nginx\n"
    deps = _detect_salt_dependencies(content)
    assert "nginx" not in deps


# ---------------------------------------------------------------------------
# _extract_include_dependencies — lines 722-726
# ---------------------------------------------------------------------------


def test_extract_include_dependencies_list_creates_key() -> None:
    """List under include key creates __include__ entry (lines 722-726)."""
    data = {"include": ["common.base", "common.users"]}
    deps = _extract_include_dependencies(data)
    assert deps == {"__include__": ["common.base", "common.users"]}


def test_extract_include_dependencies_no_include_returns_empty() -> None:
    """No include key returns empty dict."""
    deps = _extract_include_dependencies({"nginx": {}})
    assert deps == {}


def test_extract_include_dependencies_non_list_value_ignored() -> None:
    """Non-list include value is ignored."""
    deps = _extract_include_dependencies({"include": "not_a_list"})
    assert deps == {}


# ---------------------------------------------------------------------------
# _extract_dependency_arg_dicts — lines 731-748
# ---------------------------------------------------------------------------


def test_extract_dependency_arg_dicts_dict_format_extracts_items() -> None:
    """Dict-format state def extracts arg dicts from list values (lines 734-735)."""
    state_def = {
        "service.running": [
            {"name": "nginx"},
            {"require": [{"pkg": "nginx"}]},
        ]
    }
    result = _extract_dependency_arg_dicts(state_def)
    assert {"name": "nginx"} in result
    assert {"require": [{"pkg": "nginx"}]} in result


def test_extract_dependency_arg_dicts_list_format_extracts_items() -> None:
    """List-format state def extracts arg dicts from nested values (lines 736-741)."""
    state_def = [{"pkg.installed": [{"name": "nginx"}]}]
    result = _extract_dependency_arg_dicts(state_def)
    assert {"name": "nginx"} in result


def test_extract_dependency_arg_dicts_other_type_returns_empty() -> None:
    """Non-dict/list returns empty list (line 741)."""
    assert _extract_dependency_arg_dicts("not a state") == []
    assert _extract_dependency_arg_dicts(42) == []


def test_extract_dependency_arg_dicts_non_list_value_skipped() -> None:
    """Dict values that are not lists are skipped (lines 744-745)."""
    state_def = {"pkg.installed": "not a list"}
    result = _extract_dependency_arg_dicts(state_def)
    assert result == []


# ---------------------------------------------------------------------------
# _collect_state_dependencies — lines 753-763
# ---------------------------------------------------------------------------


def test_collect_state_dependencies_require_keyword() -> None:
    """Require dep produces pkg:nginx token (lines 753-763)."""
    arg_dicts = [{"require": [{"pkg": "nginx"}]}]
    deps = _collect_state_dependencies(arg_dicts)
    assert "pkg:nginx" in deps


def test_collect_state_dependencies_watch_keyword() -> None:
    """Watch dep produces service:myservice token."""
    arg_dicts = [{"watch": [{"service": "myservice"}]}]
    deps = _collect_state_dependencies(arg_dicts)
    assert "service:myservice" in deps


def test_collect_state_dependencies_non_list_value_skipped() -> None:
    """Non-list dep value is skipped (lines 759-760)."""
    arg_dicts = [{"require": "not a list"}]
    deps = _collect_state_dependencies(arg_dicts)
    assert deps == []


def test_collect_state_dependencies_empty_arg_dicts() -> None:
    """Empty arg dicts list returns empty dependencies."""
    assert _collect_state_dependencies([]) == []


# ---------------------------------------------------------------------------
# _dependency_items_to_tokens — lines 768-775
# ---------------------------------------------------------------------------


def test_dependency_items_to_tokens_produces_colon_tokens() -> None:
    """Dep items are converted to module:id format (lines 768-775)."""
    dep_items = [{"pkg": "nginx"}, {"service": "apache"}]
    tokens = _dependency_items_to_tokens(dep_items)
    assert "pkg:nginx" in tokens
    assert "service:apache" in tokens


def test_dependency_items_to_tokens_non_dict_items_skipped() -> None:
    """Non-dict items are skipped (lines 770-771)."""
    dep_items = ["not a dict", {"pkg": "nginx"}]
    tokens = _dependency_items_to_tokens(dep_items)
    assert tokens == ["pkg:nginx"]


def test_dependency_items_to_tokens_empty_input() -> None:
    """Empty list returns empty tokens."""
    assert _dependency_items_to_tokens([]) == []


# ---------------------------------------------------------------------------
# assess_salt_complexity — lines 804-893
# ---------------------------------------------------------------------------


def test_assess_salt_complexity_nonexistent_dir(tmp_path: Path) -> None:
    """Returns error JSON for non-existent directory (lines 814-815)."""
    result = json.loads(assess_salt_complexity(str(tmp_path / "nonexistent")))
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_assess_salt_complexity_file_path_is_error(tmp_path: Path) -> None:
    """Returns error when path points to a file not a directory (lines 816-817)."""
    f = tmp_path / "test.sls"
    f.write_text("base:")
    result = json.loads(assess_salt_complexity(str(f)))
    assert "error" in result
    assert "not a directory" in result["error"].lower()


def test_assess_salt_complexity_permission_error(tmp_path: Path) -> None:
    """Returns error JSON for PermissionError (lines 819-820)."""
    with patch("souschef.parsers.salt._normalize_path", side_effect=PermissionError()):
        result = json.loads(assess_salt_complexity(str(tmp_path)))
    assert "error" in result
    assert "Permission denied" in result["error"]


def test_assess_salt_complexity_value_error(tmp_path: Path) -> None:
    """Returns error JSON for ValueError (e.g. traversal) (lines 821-822)."""
    with patch(
        "souschef.parsers.salt._ensure_within_base_path",
        side_effect=ValueError("traversal"),
    ):
        result = json.loads(assess_salt_complexity(str(tmp_path)))
    assert "error" in result
    assert "traversal" in result["error"]


def test_assess_salt_complexity_empty_directory(tmp_path: Path) -> None:
    """Empty directory produces zero-file summary (line 872 else branch)."""
    result = json.loads(assess_salt_complexity(str(tmp_path)))
    assert result["summary"]["total_files"] == 0
    assert result["summary"]["total_states"] == 0
    assert "complexity_score" in result["summary"]


def test_assess_salt_complexity_with_sls_file(tmp_path: Path) -> None:
    """Valid SLS file produces non-empty file report (lines 831-869)."""
    (tmp_path / "nginx.sls").write_text(
        "nginx:\n"
        "  pkg.installed:\n"
        "    - name: nginx\n"
        "nginx_service:\n"
        "  service.running:\n"
        "    - name: nginx\n"
        "    - require:\n"
        "      - pkg: nginx\n"
    )
    result = json.loads(assess_salt_complexity(str(tmp_path)))
    assert result["summary"]["total_files"] == 1
    assert result["summary"]["total_states"] >= 1
    assert len(result["files"]) == 1
    assert "complexity_score" in result["files"][0]


def test_assess_salt_complexity_oserror_on_read_skips_file(tmp_path: Path) -> None:
    """OSError when reading an SLS file skips it gracefully (lines 835-836)."""
    (tmp_path / "nginx.sls").write_text("nginx:\n  pkg.installed:\n    - name: nginx\n")
    with patch(
        "souschef.parsers.salt.safe_read_text",
        side_effect=OSError("permission denied"),
    ):
        result = json.loads(assess_salt_complexity(str(tmp_path)))
    assert result["summary"]["total_files"] == 1
    assert result["summary"]["total_states"] == 0


def test_assess_salt_complexity_high_complexity_file(tmp_path: Path) -> None:
    """cmd.run states with Jinja expressions score high complexity (lines 857-858)."""
    content = (
        "run_deploy:\n"
        "  cmd.run:\n"
        "    - name: {{ pillar.cmd }}\n"
        "    - cwd: {{ pillar.workdir }}\n"
        "    - user: {{ pillar.user }}\n"
    )
    (tmp_path / "deploy.sls").write_text(content)
    result = json.loads(assess_salt_complexity(str(tmp_path)))
    assert result["summary"]["total_files"] == 1
    assert len(result["files"]) == 1
    # Score should be in [0, 100] range
    assert 0.0 <= result["files"][0]["complexity_score"] <= 100.0
