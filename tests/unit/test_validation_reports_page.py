"""Unit tests for validation_reports page helpers."""

from __future__ import annotations

import importlib
import subprocess
import sys
from unittest.mock import MagicMock, Mock, patch


class SessionState(dict):
    """Session-state helper with attribute and dict access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    return ctx


def _columns_side_effect(spec):
    count = spec if isinstance(spec, int) else len(spec)
    return [_ctx() for _ in range(count)]


def test_run_ansible_lint_success_and_failure():
    from souschef.ui.pages.validation_reports import _run_ansible_lint

    ok = MagicMock(returncode=0, stdout="ok", stderr="")
    with patch("souschef.ui.pages.validation_reports.subprocess.run", return_value=ok):
        success, output = _run_ansible_lint("playbook.yml")
    assert success
    assert output == "ok"

    bad = MagicMock(returncode=2, stdout="", stderr="failed")
    with patch("souschef.ui.pages.validation_reports.subprocess.run", return_value=bad):
        success2, output2 = _run_ansible_lint("playbook.yml")
    assert not success2
    assert output2 == "failed"


def test_run_ansible_lint_timeout_and_exception():
    from souschef.ui.pages.validation_reports import _run_ansible_lint

    with patch(
        "souschef.ui.pages.validation_reports.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="x", timeout=30),
    ):
        success, output = _run_ansible_lint("playbook.yml")
    assert not success
    assert "timeout" in output.lower()

    with patch(
        "souschef.ui.pages.validation_reports.subprocess.run",
        side_effect=RuntimeError("boom"),
    ):
        success2, output2 = _run_ansible_lint("playbook.yml")
    assert not success2
    assert "error running ansible-lint" in output2.lower()


def test_validate_playbooks_in_directory_branches(tmp_path):
    from souschef.ui.pages.validation_reports import _validate_playbooks_in_directory

    missing = _validate_playbooks_in_directory(str(tmp_path / "missing"))
    assert "error" in missing

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    no_playbooks = _validate_playbooks_in_directory(str(empty_dir))
    assert "no_playbooks" in no_playbooks

    playbook1 = empty_dir / "a.yml"
    playbook2 = empty_dir / "b.yaml"
    playbook1.write_text("---\n- hosts: all\n")
    playbook2.write_text("---\n- hosts: all\n")

    with patch(
        "souschef.ui.pages.validation_reports._run_ansible_lint",
        side_effect=[(True, "ok"), (False, "bad")],
    ):
        results = _validate_playbooks_in_directory(str(empty_dir))

    assert results["a.yml"] == (True, "ok")
    assert results["b.yaml"] == (False, "bad")


def test_parse_ansible_lint_output():
    from souschef.ui.pages.validation_reports import _parse_ansible_lint_output

    parsed = _parse_ansible_lint_output("warning: x\nerror: y\ninfo: z\n\n")
    assert parsed["warnings"] == 1
    assert parsed["errors"] == 1
    assert parsed["info"] == 1
    assert len(parsed["details"]) == 3


def test_generate_validation_report():
    from souschef.ui.pages.validation_reports import _generate_validation_report

    report = _generate_validation_report(
        {
            "good.yml": (True, "all good"),
            "bad.yml": (False, "lint issue"),
            "empty.yml": (True, ""),
        }
    )

    assert "ANSIBLE PLAYBOOK VALIDATION REPORT" in report
    assert "Total Playbooks: 3" in report
    assert "Passed: 2" in report
    assert "Failed: 1" in report
    assert "Playbook: empty.yml" in report
    assert "(No output)" in report


@patch("souschef.ui.pages.validation_reports.st")
def test_display_validation_result_variants(mock_st):
    from souschef.ui.pages.validation_reports import _display_validation_result

    mock_st.expander.return_value = _ctx()

    _display_validation_result("good.yml", True, "ok")
    mock_st.success.assert_called_once()
    mock_st.code.assert_called_once()

    mock_st.reset_mock()
    mock_st.expander.return_value = _ctx()

    _display_validation_result("bad.yml", False, "")
    mock_st.error.assert_called_once()
    mock_st.info.assert_called_once()


@patch("souschef.ui.pages.validation_reports.st")
def test_show_validation_reports_page_no_converted_path(mock_st):
    from souschef.ui.pages.validation_reports import show_validation_reports_page

    mock_st.session_state = SessionState()
    mock_st.columns.side_effect = _columns_side_effect
    mock_st.button.return_value = False

    show_validation_reports_page()

    mock_st.info.assert_called_once()


@patch("souschef.ui.pages.validation_reports.st")
def test_show_validation_reports_page_missing_directory(mock_st):
    from souschef.ui.pages.validation_reports import show_validation_reports_page

    mock_st.session_state = SessionState(
        {"converted_playbooks_path": "/does/not/exist"}
    )
    mock_st.columns.side_effect = _columns_side_effect
    mock_st.button.return_value = False

    show_validation_reports_page()

    mock_st.warning.assert_called_once()


@patch("souschef.ui.pages.validation_reports.st")
def test_show_validation_reports_page_empty_results(mock_st, tmp_path):
    from souschef.ui.pages.validation_reports import show_validation_reports_page

    valid_dir = tmp_path / "out"
    valid_dir.mkdir()

    mock_st.session_state = SessionState({"converted_playbooks_path": str(valid_dir)})
    mock_st.columns.side_effect = _columns_side_effect
    mock_st.button.return_value = False
    mock_st.spinner.return_value = _ctx()

    with patch(
        "souschef.ui.pages.validation_reports._validate_playbooks_in_directory",
        return_value={},
    ):
        show_validation_reports_page()

    mock_st.warning.assert_called_once_with("No playbooks found to validate")


@patch("souschef.ui.pages.validation_reports.st")
@patch("souschef.ui.pages.validation_reports._display_validation_result")
def test_show_validation_reports_page_multi_results_and_export(
    mock_display_result,
    mock_st,
    tmp_path,
):
    from souschef.ui.pages.validation_reports import show_validation_reports_page

    valid_dir = tmp_path / "out"
    valid_dir.mkdir()

    mock_st.session_state = SessionState({"converted_playbooks_path": str(valid_dir)})
    mock_st.columns.side_effect = _columns_side_effect
    mock_st.spinner.return_value = _ctx()
    mock_st.tabs.return_value = [_ctx(), _ctx()]
    mock_st.button.side_effect = [False, True]

    with (
        patch(
            "souschef.ui.pages.validation_reports._validate_playbooks_in_directory",
            return_value={"a.yml": (True, "ok"), "b.yml": (False, "bad")},
        ),
        patch(
            "souschef.ui.pages.validation_reports._generate_validation_report",
            return_value="REPORT",
        ),
    ):
        show_validation_reports_page()

    assert mock_display_result.call_count == 2
    mock_st.download_button.assert_called_once()


@patch("souschef.ui.pages.validation_reports.st")
@patch("souschef.ui.pages.validation_reports._display_validation_result")
def test_show_validation_reports_page_single_result_all_passed(
    mock_display_result,
    mock_st,
    tmp_path,
):
    from souschef.ui.pages.validation_reports import show_validation_reports_page

    valid_dir = tmp_path / "out"
    valid_dir.mkdir()

    mock_st.session_state = SessionState({"converted_playbooks_path": str(valid_dir)})
    mock_st.columns.side_effect = _columns_side_effect
    mock_st.spinner.return_value = _ctx()
    mock_st.button.side_effect = [False, False]

    with patch(
        "souschef.ui.pages.validation_reports._validate_playbooks_in_directory",
        return_value={"a.yml": (True, "ok")},
    ):
        show_validation_reports_page()

    mock_st.success.assert_called()
    mock_display_result.assert_called_once_with("a.yml", True, "ok")


@patch("souschef.ui.pages.validation_reports.st")
def test_show_validation_reports_page_back_button(mock_st, tmp_path):
    from souschef.ui.pages.validation_reports import show_validation_reports_page

    valid_dir = tmp_path / "out"
    valid_dir.mkdir()

    mock_st.session_state = SessionState({"converted_playbooks_path": str(valid_dir)})
    mock_st.columns.side_effect = _columns_side_effect
    mock_st.spinner.return_value = _ctx()
    mock_st.button.side_effect = [True, False]

    with patch(
        "souschef.ui.pages.validation_reports._validate_playbooks_in_directory",
        return_value={"a.yml": (True, "ok")},
    ):
        show_validation_reports_page()

    assert mock_st.session_state.current_page == "Dashboard"
    mock_st.rerun.assert_called_once()


def test_module_import_streamlit_fallback():
    module_name = "souschef.ui.pages.validation_reports"
    original_module = sys.modules.get(module_name)
    if module_name in sys.modules:
        del sys.modules[module_name]

    import builtins

    original_import = builtins.__import__

    def blocked_import(
        name, module_globals=None, module_locals=None, fromlist=(), level=0
    ):
        if name == "streamlit":
            raise ImportError("blocked streamlit")
        return original_import(name, module_globals, module_locals, fromlist, level)

    try:
        with patch("builtins.__import__", side_effect=blocked_import):
            module = importlib.import_module(module_name)
            assert module.st is None
    finally:
        if module_name in sys.modules:
            del sys.modules[module_name]
        if original_module is not None:
            sys.modules[module_name] = original_module
        else:
            importlib.import_module(module_name)
