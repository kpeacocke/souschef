"""Tests for AI playbook validation and repair."""

from unittest.mock import patch

from souschef.converters import playbook as playbook_converter


def test_validate_and_fix_playbook_repairs_invalid_yaml() -> None:
    """Ensure invalid YAML triggers AI repair and returns valid YAML."""
    invalid_playbook = """---
- name: Bad playbook
  hosts: all
  tasks:
    - name: Bad task
      when: ansible.builtin.stat:
"""

    fixed_playbook = """---
- name: Repaired playbook
  hosts: all
  tasks:
    - name: Check file
      ansible.builtin.stat:
        path: /tmp/file
      register: file_stat
    - name: Do work
      ansible.builtin.command:
        cmd: echo ok
      when: file_stat.stat.exists
"""

    with (
        patch.object(
            playbook_converter,
            "_call_ai_api",
            return_value=fixed_playbook,
        ) as mock_call,
        patch.object(playbook_converter, "_run_ansible_lint", return_value=None),
    ):
        result = playbook_converter._validate_and_fix_playbook(
            invalid_playbook,
            client=object(),
            ai_provider="openai",
            model="gpt-test",
            temperature=0.2,
            max_tokens=200,
        )

    assert result == fixed_playbook.strip()
    assert mock_call.called
