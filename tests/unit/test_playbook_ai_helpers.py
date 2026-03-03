"""Tests for playbook AI helper functions."""

from unittest.mock import MagicMock

import pytest

from souschef.converters import playbook as playbook_module
from souschef.core.constants import ERROR_PREFIX


def test_initialize_ai_client_github_copilot_error() -> None:
    """GitHub Copilot provider should return error message."""
    result = playbook_module._initialize_ai_client("github_copilot", "key")
    assert isinstance(result, str)
    assert result.startswith(ERROR_PREFIX)


def test_initialize_ai_client_watson_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Watsonx provider should fail when APIClient is unavailable."""
    monkeypatch.setattr(playbook_module, "APIClient", None)
    result = playbook_module._initialize_ai_client("watson", "key")
    assert isinstance(result, str)
    assert result.startswith(ERROR_PREFIX)


def test_initialize_ai_client_lightspeed_invalid_url() -> None:
    """Invalid Lightspeed URL should return error message."""
    result = playbook_module._initialize_ai_client(
        "lightspeed", "key", base_url="not a url"
    )
    assert isinstance(result, str)
    assert result.startswith(ERROR_PREFIX)


def test_call_lightspeed_api_requests_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lightspeed API should fail when requests is missing."""
    monkeypatch.setattr(playbook_module, "requests", None)
    result = playbook_module._call_lightspeed_api(
        {"api_key": "key", "base_url": "https://api.redhat.com"},
        "prompt",
        "model",
        0.2,
        100,
    )
    assert result.startswith(ERROR_PREFIX)


def test_call_github_copilot_api_requests_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub Copilot API should fail when requests is missing."""
    monkeypatch.setattr(playbook_module, "requests", None)
    result = playbook_module._call_github_copilot_api(
        {"api_key": "key", "base_url": "https://api.github.com"},
        "prompt",
        "model",
        0.2,
        100,
    )
    assert result.startswith(ERROR_PREFIX)


def test_call_github_copilot_api_error_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """GitHub Copilot API should return error on non-200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_response
    monkeypatch.setattr(playbook_module, "requests", mock_requests)

    result = playbook_module._call_github_copilot_api(
        {"api_key": "key", "base_url": "https://api.github.com"},
        "prompt",
        "model",
        0.2,
        100,
    )
    assert result.startswith(ERROR_PREFIX)
    assert "400" in result


def test_call_ai_api_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI API dispatcher should call provider-specific function."""
    monkeypatch.setattr(
        playbook_module, "_call_github_copilot_api", lambda *args, **kwargs: "ok"
    )
    result = playbook_module._call_ai_api(
        {"api_key": "key", "base_url": "https://api.github.com"},
        "github_copilot",
        "prompt",
        "model",
        0.2,
        100,
    )
    assert result == "ok"


def test_create_ai_conversion_prompt_with_context() -> None:
    """Prompt should include project context and recommendations."""
    project_recommendations = {
        "project_complexity": "High",
        "migration_strategy": "phased",
        "project_effort_days": 10.0,
        "dependency_density": 1.5,
        "recommendations": ["Start with base roles", "Add CI checks"],
        "migration_order": [
            {
                "cookbook": "default",
                "phase": "phase 1",
                "complexity": "low",
                "dependencies": ["base"],
                "reason": "foundation",
            }
        ],
    }
    prompt = playbook_module._create_ai_conversion_prompt(
        "raw", "parsed", "default.rb", project_recommendations
    )
    assert "PROJECT CONTEXT" in prompt
    assert "PROJECT MIGRATION RECOMMENDATIONS" in prompt
    assert "MIGRATION CONTEXT" in prompt


def test_find_recipe_position_in_migration_order() -> None:
    """Recipe name should resolve to migration order entry."""
    order = [{"cookbook": "web", "phase": "phase 2"}]
    result = playbook_module._find_recipe_position_in_migration_order(
        order, "recipes/web.rb"
    )
    assert result == order[0]
