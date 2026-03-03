"""Tests for playbook conversion helpers."""

import textwrap

from souschef.converters import playbook as playbook_helpers
from souschef.core.constants import ERROR_PREFIX


def test_clean_ai_playbook_response_empty() -> None:
    """Test cleaning empty AI response returns error prefix."""
    result = playbook_helpers._clean_ai_playbook_response("   ")

    assert result.startswith(ERROR_PREFIX)


def test_clean_ai_playbook_response_strips_code_fence() -> None:
    """Test cleaning removes markdown fences."""
    response = """```yaml
---
- name: Test
  hosts: all
  tasks: []
```"""

    result = playbook_helpers._clean_ai_playbook_response(response)

    assert result.startswith("---")
    assert "```" not in result


def test_clean_ai_playbook_response_invalid_yaml() -> None:
    """Test invalid YAML shape returns error prefix."""
    response = "not a playbook"

    result = playbook_helpers._clean_ai_playbook_response(response)

    assert result.startswith(ERROR_PREFIX)


def test_validate_playbook_yaml_ok() -> None:
    """Test valid YAML returns no error."""
    playbook = """---
- name: Test
  hosts: all
  tasks: []
"""

    assert playbook_helpers._validate_playbook_yaml(playbook) is None


def test_validate_playbook_yaml_error() -> None:
    """Test invalid YAML returns error message."""
    playbook = "---\n- name: [unterminated"

    error = playbook_helpers._validate_playbook_yaml(playbook)

    assert isinstance(error, str)
    assert error


def test_validate_and_fix_playbook_passes_when_valid(monkeypatch) -> None:
    """Test validator returns original when playbook is valid."""
    playbook = """---
- name: Test
  hosts: all
  tasks: []
"""

    monkeypatch.setattr(playbook_helpers, "_run_ansible_lint", lambda *_: None)

    result = playbook_helpers._validate_and_fix_playbook(
        playbook,
        client=object(),
        ai_provider="openai",
        model="test",
        temperature=0.1,
        max_tokens=256,
    )

    assert result == playbook


def test_validate_and_fix_playbook_fallback_on_bad_fix(monkeypatch) -> None:
    """Test validator falls back when AI fix is invalid."""
    playbook = """---
- name: Test
  hosts: all
  tasks: []
"""

    monkeypatch.setattr(playbook_helpers, "_run_ansible_lint", lambda *_: "lint error")
    monkeypatch.setattr(playbook_helpers, "_call_ai_api", lambda *_: "not yaml")

    result = playbook_helpers._validate_and_fix_playbook(
        playbook,
        client=object(),
        ai_provider="openai",
        model="test",
        temperature=0.1,
        max_tokens=256,
    )

    assert result == playbook


def test_validate_and_fix_playbook_accepts_fixed(monkeypatch) -> None:
    """Test validator uses AI fix when valid YAML returned."""
    playbook = """---
- name: Test
  hosts: all
  tasks:
    - debug:
        msg: "hello"
"""
    fixed_playbook = textwrap.dedent(
        """
        ---
        - name: Fixed
          hosts: all
          tasks: []
        """
    ).strip()

    monkeypatch.setattr(playbook_helpers, "_run_ansible_lint", lambda *_: "lint error")
    monkeypatch.setattr(playbook_helpers, "_call_ai_api", lambda *_: fixed_playbook)

    result = playbook_helpers._validate_and_fix_playbook(
        playbook,
        client=object(),
        ai_provider="openai",
        model="test",
        temperature=0.1,
        max_tokens=256,
    )

    assert result == fixed_playbook


def test_build_project_context_parts_with_recommendations() -> None:
    """Test project context parts include recommendations and dependencies."""
    recommendations = {
        "project_complexity": "High",
        "migration_strategy": "phased",
        "project_effort_days": 12.5,
        "dependency_density": 1.2,
        "recommendations": ["Use collections"],
        "migration_order": [
            {
                "cookbook": "web",
                "phase": "1",
                "complexity": "Medium",
                "dependencies": ["base"],
                "reason": "Critical",
            }
        ],
    }

    parts = playbook_helpers._build_project_context_parts(
        recommendations,
        "web.rb",
    )

    joined = "\n".join(parts)
    assert "PROJECT MIGRATION RECOMMENDATIONS" in joined
    assert "MIGRATION CONTEXT FOR THIS RECIPE" in joined
    assert "Dependencies: base" in joined


def test_build_project_context_parts_without_match() -> None:
    """Test project context when recipe is not in migration order."""
    recommendations = {
        "project_complexity": "Low",
        "migration_strategy": "single",
        "project_effort_days": 1.0,
        "dependency_density": 0.0,
        "migration_order": [{"cookbook": "other"}],
    }

    parts = playbook_helpers._build_project_context_parts(
        recommendations,
        "missing.rb",
    )

    joined = "\n".join(parts)
    assert "MIGRATION CONTEXT FOR THIS RECIPE" not in joined


def test_create_ai_conversion_prompt_includes_context() -> None:
    """Test AI prompt includes project context when provided."""
    prompt = playbook_helpers._create_ai_conversion_prompt(
        raw_content="package 'vim'",
        parsed_content="Resource 1:\n  Type: package",
        recipe_name="web.rb",
        project_recommendations={"project_complexity": "Low"},
    )

    assert "PROJECT CONTEXT" in prompt


def test_create_ai_conversion_prompt_no_context() -> None:
    """Test AI prompt without project context."""
    prompt = playbook_helpers._create_ai_conversion_prompt(
        raw_content="package 'vim'",
        parsed_content="Resource 1:\n  Type: package",
        recipe_name="web.rb",
        project_recommendations=None,
    )

    assert "PROJECT CONTEXT" not in prompt
