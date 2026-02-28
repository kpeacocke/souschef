"""Tests for playbook lint helper utilities."""

from unittest.mock import MagicMock, patch

from souschef.converters.playbook import _run_ansible_lint


def test_run_ansible_lint_when_not_installed() -> None:
    """Test lint helper returns None when ansible-lint is unavailable."""
    with patch("souschef.converters.playbook.shutil.which", return_value=None):
        result = _run_ansible_lint("---\n- name: Test\n  hosts: all")

    assert result is None


def test_run_ansible_lint_success() -> None:
    """Test lint helper returns None for a clean playbook."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with (
        patch("souschef.converters.playbook.shutil.which", return_value="ansible-lint"),
        patch("souschef.converters.playbook.subprocess.run", return_value=mock_result),
    ):
        result = _run_ansible_lint("---\n- name: Test\n  hosts: all")

    assert result is None


def test_run_ansible_lint_failure_output() -> None:
    """Test lint helper returns combined stdout and stderr on failure."""
    mock_result = MagicMock()
    mock_result.returncode = 2
    mock_result.stdout = "lint error one"
    mock_result.stderr = "lint error two"

    with (
        patch("souschef.converters.playbook.shutil.which", return_value="ansible-lint"),
        patch("souschef.converters.playbook.subprocess.run", return_value=mock_result),
    ):
        result = _run_ansible_lint("---\n- name: Bad playbook\n  hosts: all")

    assert result is not None
    assert "lint error one" in result
    assert "lint error two" in result
