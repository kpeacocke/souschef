"""Helper tests for ai_settings page module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, Mock, patch

import pytest


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


def test_get_model_options():
    from souschef.ui.pages.ai_settings import (
        ANTHROPIC_PROVIDER,
        LIGHTSPEED_PROVIDER,
        OPENAI_PROVIDER,
        WATSON_PROVIDER,
        _get_model_options,
    )

    assert "gpt-4o" in _get_model_options(OPENAI_PROVIDER)
    assert "claude-3-5-sonnet-20241022" in _get_model_options(ANTHROPIC_PROVIDER)
    assert "meta-llama/llama-3-70b-instruct" in _get_model_options(WATSON_PROVIDER)
    assert "codellama/CodeLlama-34b-Instruct-hf" in _get_model_options(
        LIGHTSPEED_PROVIDER
    )
    assert _get_model_options("Other") == ["local-model"]


@patch("souschef.ui.pages.ai_settings.st")
def test_render_api_configuration_local(mock_st):
    from souschef.ui.pages.ai_settings import LOCAL_PROVIDER, _render_api_configuration

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.text_input.side_effect = ["https://localhost:11434", "llama3"]

    model, base_url, project_id = _render_api_configuration(LOCAL_PROVIDER)
    assert model == "llama3"
    assert base_url == "https://localhost:11434"
    assert project_id == ""


@patch("souschef.ui.pages.ai_settings.st")
def test_render_api_configuration_watson(mock_st):
    from souschef.ui.pages.ai_settings import WATSON_PROVIDER, _render_api_configuration

    mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
    mock_st.text_input.side_effect = [
        "api",
        "project",
        "https://us-south.ml.cloud.ibm.com",
    ]

    api_key, base_url, project_id = _render_api_configuration(WATSON_PROVIDER)
    assert api_key == "api"
    assert base_url == "https://us-south.ml.cloud.ibm.com"
    assert project_id == "project"


@patch("souschef.ui.pages.ai_settings.st")
def test_render_api_configuration_lightspeed(mock_st):
    from souschef.ui.pages.ai_settings import (
        LIGHTSPEED_PROVIDER,
        _render_api_configuration,
    )

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.text_input.side_effect = ["api", "https://api.redhat.com"]

    api_key, base_url, project_id = _render_api_configuration(LIGHTSPEED_PROVIDER)
    assert api_key == "api"
    assert base_url == "https://api.redhat.com"
    assert project_id == ""


@patch("souschef.ui.pages.ai_settings.st")
def test_render_api_configuration_openai_branch(mock_st):
    from souschef.ui.pages.ai_settings import OPENAI_PROVIDER, _render_api_configuration

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.text_input.side_effect = ["api-key", "https://api.openai.com/v1"]

    api_key, base_url, project_id = _render_api_configuration(OPENAI_PROVIDER)
    assert api_key == "api-key"
    assert base_url == "https://api.openai.com/v1"
    assert project_id == ""


@patch("souschef.ui.pages.ai_settings.st")
def test_render_advanced_settings(mock_st):
    from souschef.ui.pages.ai_settings import _render_advanced_settings

    mock_st.expander.return_value = _ctx()
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.slider.return_value = 0.9
    mock_st.number_input.return_value = 2048

    temperature, max_tokens = _render_advanced_settings()
    assert temperature == pytest.approx(0.9)
    assert max_tokens == 2048


@patch("souschef.ui.pages.ai_settings.st")
def test_render_validation_section_buttons(mock_st):
    from souschef.ui.pages.ai_settings import _render_validation_section

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.side_effect = [True, True]

    with (
        patch("souschef.ui.pages.ai_settings.validate_ai_configuration") as validate,
        patch("souschef.ui.pages.ai_settings.save_ai_settings") as save,
    ):
        _render_validation_section(
            "OpenAI (GPT)",
            "key",
            "gpt-4o",
            "https://api.openai.com/v1",
            "",
            0.7,
            4000,
        )

    validate.assert_called_once()
    save.assert_called_once()


@patch("souschef.ui.pages.ai_settings.validate_user_provided_url")
def test_sanitize_lightspeed_base_url(mock_validate):
    from souschef.ui.pages.ai_settings import _sanitize_lightspeed_base_url

    mock_validate.return_value = "https://api.redhat.com"
    result = _sanitize_lightspeed_base_url("https://api.redhat.com/path")

    assert result == "https://api.redhat.com"
    mock_validate.assert_called_once()


@patch("souschef.ui.pages.ai_settings.st")
def test_validate_ai_configuration_missing_api_key(mock_st):
    from souschef.ui.pages.ai_settings import (
        ANTHROPIC_PROVIDER,
        validate_ai_configuration,
    )

    validate_ai_configuration(ANTHROPIC_PROVIDER, "", "claude-3-5-sonnet-20241022")
    mock_st.error.assert_called_once()


@patch("souschef.ui.pages.ai_settings.st")
def test_validate_ai_configuration_unknown_provider(mock_st):
    from souschef.ui.pages.ai_settings import validate_ai_configuration

    mock_st.spinner.return_value = _ctx()
    validate_ai_configuration("Unknown", "k", "m")

    mock_st.error.assert_called_once()


def test_validate_local_model_config_requests_missing():
    from souschef.ui.pages.ai_settings import (
        REQUESTS_NOT_INSTALLED_MESSAGE,
        validate_local_model_config,
    )

    with patch("souschef.ui.pages.ai_settings.requests", None):
        success, message = validate_local_model_config(
            "https://localhost:11434", "llama"
        )

    assert not success
    assert message == REQUESTS_NOT_INSTALLED_MESSAGE


def test_validate_anthropic_config_library_missing():
    from souschef.ui.pages.ai_settings import validate_anthropic_config

    with patch("souschef.ui.pages.ai_settings.anthropic", None):
        success, message = validate_anthropic_config("key", "model")

    assert not success
    assert "not installed" in message


def test_validate_openai_config_library_missing():
    from souschef.ui.pages.ai_settings import validate_openai_config

    with patch("souschef.ui.pages.ai_settings.openai", None):
        success, message = validate_openai_config("key", "model")

    assert not success
    assert "not installed" in message


def test_validate_watson_config_library_missing():
    from souschef.ui.pages.ai_settings import validate_watson_config

    with patch("souschef.ui.pages.ai_settings.APIClient", None):
        success, message = validate_watson_config("key", "project")

    assert not success
    assert "not installed" in message


def test_validate_lightspeed_config_requests_missing():
    from souschef.ui.pages.ai_settings import validate_lightspeed_config

    with patch("souschef.ui.pages.ai_settings.requests", None):
        success, message = validate_lightspeed_config("key", "model")

    assert not success
    assert "not installed" in message


def test_check_ollama_server_paths():
    from souschef.ui.pages.ai_settings import _check_ollama_server

    response_ok = MagicMock(status_code=200)
    response_ok.json.return_value = {"models": [{"name": "llama2"}]}

    with patch("souschef.ui.pages.ai_settings.requests.get", return_value=response_ok):
        success, message = _check_ollama_server("https://localhost:11434", "llama2")
    assert success
    assert "found" in message.lower()

    response_empty = MagicMock(status_code=200)
    response_empty.json.return_value = {"models": []}
    with patch(
        "souschef.ui.pages.ai_settings.requests.get", return_value=response_empty
    ):
        success2, message2 = _check_ollama_server("https://localhost:11434", "")
    assert not success2
    assert "no models" in message2.lower()


def test_check_openai_compatible_server_paths():
    from souschef.ui.pages.ai_settings import _check_openai_compatible_server

    response_ok = MagicMock(status_code=200)
    response_ok.json.return_value = {"data": [{"id": "gpt-4o"}]}
    with patch("souschef.ui.pages.ai_settings.requests.get", return_value=response_ok):
        success, _ = _check_openai_compatible_server("https://localhost:8000", "gpt-4o")
    assert success

    response_bad = MagicMock(status_code=500)
    with patch("souschef.ui.pages.ai_settings.requests.get", return_value=response_bad):
        success2, message2 = _check_openai_compatible_server(
            "https://localhost:8000", "gpt-4o"
        )
    assert not success2
    assert "not responding" in message2.lower()


def test_validate_local_model_config_exception_paths():
    import requests

    from souschef.ui.pages.ai_settings import validate_local_model_config

    with (
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            return_value="https://localhost:11434",
        ),
        patch(
            "souschef.ui.pages.ai_settings._check_ollama_server",
            side_effect=requests.exceptions.Timeout(),
        ),
    ):
        success, message = validate_local_model_config(
            "https://localhost:11434", "llama2"
        )
    assert not success
    assert "timed out" in message.lower()

    with (
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            return_value="https://localhost:11434",
        ),
        patch(
            "souschef.ui.pages.ai_settings._check_ollama_server",
            side_effect=requests.exceptions.ConnectionError(),
        ),
    ):
        success2, message2 = validate_local_model_config(
            "https://localhost:11434", "llama2"
        )
    assert not success2
    assert "cannot reach" in message2.lower()


def test_validate_openai_config_success_and_invalid_base_url():
    from souschef.ui.pages.ai_settings import validate_openai_config

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = {"ok": True}

    with (
        patch("souschef.ui.pages.ai_settings.openai.OpenAI", return_value=mock_client),
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            return_value="https://api.openai.com/v1",
        ),
    ):
        success, _ = validate_openai_config("k", "gpt-4o", "https://api.openai.com/v1")
    assert success

    with patch(
        "souschef.ui.pages.ai_settings.validate_user_provided_url",
        side_effect=ValueError("bad url"),
    ):
        success2, message2 = validate_openai_config("k", "gpt-4o", "bad")
    assert not success2
    assert "invalid base url" in message2.lower()


def test_validate_lightspeed_config_failure_status():
    from souschef.ui.pages.ai_settings import validate_lightspeed_config

    response = MagicMock(status_code=401, text="unauthorized")
    with (
        patch(
            "souschef.ui.pages.ai_settings._sanitize_lightspeed_base_url",
            return_value="https://api.redhat.com",
        ),
        patch("souschef.ui.pages.ai_settings.requests.post", return_value=response),
    ):
        success, message = validate_lightspeed_config(
            "k", "model", "https://api.redhat.com"
        )
    assert not success
    assert "status 401" in message


def test_validate_watson_config_success_and_invalid_url():
    from souschef.ui.pages.ai_settings import validate_watson_config

    client = MagicMock()
    client.foundation_models.get_model_specs.return_value = [1, 2]

    with (
        patch("souschef.ui.pages.ai_settings.APIClient", return_value=client),
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            return_value="https://us-south.ml.cloud.ibm.com",
        ),
    ):
        success, _ = validate_watson_config(
            "k", "p", "https://us-south.ml.cloud.ibm.com"
        )
    assert success

    with (
        patch("souschef.ui.pages.ai_settings.APIClient", return_value=client),
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            side_effect=ValueError("bad"),
        ),
    ):
        success2, message2 = validate_watson_config("k", "p", "bad")
    assert not success2
    assert "invalid base url" in message2.lower()


@patch("souschef.ui.pages.ai_settings.st")
def test_save_ai_settings(mock_st, tmp_path):
    from souschef.ui.pages.ai_settings import save_ai_settings

    mock_st.session_state = SessionState({"timestamp": "now"})

    with patch("souschef.ui.pages.ai_settings.Path.home", return_value=tmp_path):
        save_ai_settings(
            provider="OpenAI (GPT)",
            api_key="secret",
            model="gpt-4o",
            base_url="",
            temperature=0.7,
            max_tokens=4096,
            project_id="",
        )

    config_file = tmp_path / ".souschef" / "ai_config.json"
    assert config_file.exists()
    data = json.loads(config_file.read_text())
    assert data["model"] == "gpt-4o"
    mock_st.success.assert_called_once()


@patch("souschef.ui.pages.ai_settings.st")
def test_load_ai_settings_priority(mock_st, tmp_path):
    from souschef.ui.pages.ai_settings import load_ai_settings

    mock_st.session_state = SessionState({"ai_config": {"provider": "Session"}})

    # File config wins over session config
    config_dir = tmp_path / ".souschef"
    config_dir.mkdir()
    (config_dir / "ai_config.json").write_text('{"provider": "File"}')

    with patch("souschef.ui.pages.ai_settings.Path.home", return_value=tmp_path):
        loaded = load_ai_settings()

    assert loaded["provider"] == "File"


@patch("souschef.ui.pages.ai_settings.st")
def test_display_current_settings_with_config(mock_st):
    from souschef.ui.pages.ai_settings import display_current_settings

    mock_st.columns.return_value = [_ctx(), _ctx()]

    with patch(
        "souschef.ui.pages.ai_settings.load_ai_settings",
        return_value={
            "provider": "OpenAI (GPT)",
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4000,
            "api_key": "secret",
            "last_updated": "now",
        },
    ):
        display_current_settings()

    assert mock_st.metric.call_count == 4
    mock_st.info.assert_called()


@patch("souschef.ui.pages.ai_settings.st")
def test_display_current_settings_empty(mock_st):
    from souschef.ui.pages.ai_settings import display_current_settings

    with patch("souschef.ui.pages.ai_settings.load_ai_settings", return_value={}):
        display_current_settings()

    mock_st.info.assert_called_once()


@patch("souschef.ui.pages.ai_settings.st")
def test_show_ai_settings_page_smoke(mock_st):
    from souschef.ui.pages.ai_settings import show_ai_settings_page

    mock_st.session_state = SessionState()
    mock_st.columns.side_effect = lambda spec: [
        _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
    ]
    mock_st.selectbox.side_effect = ["OpenAI (GPT)", "gpt-4o"]
    mock_st.button.return_value = False

    with (
        patch(
            "souschef.ui.pages.ai_settings._render_api_configuration",
            return_value=("key", "", ""),
        ),
        patch(
            "souschef.ui.pages.ai_settings._render_advanced_settings",
            return_value=(0.7, 4000),
        ),
        patch("souschef.ui.pages.ai_settings._render_validation_section"),
        patch("souschef.ui.pages.ai_settings.display_current_settings"),
    ):
        show_ai_settings_page()

    mock_st.subheader.assert_called()


def test_load_ai_settings_from_env(monkeypatch):
    from souschef.ui.pages.ai_settings import _load_ai_settings_from_env

    monkeypatch.setenv("SOUSCHEF_AI_PROVIDER", "OpenAI (GPT)")
    monkeypatch.setenv("SOUSCHEF_AI_MODEL", "gpt-4o")
    monkeypatch.setenv("SOUSCHEF_AI_TEMPERATURE", "0.5")
    monkeypatch.setenv("SOUSCHEF_AI_MAX_TOKENS", "2048")

    cfg = _load_ai_settings_from_env()
    assert cfg["provider"] == "OpenAI (GPT)"
    assert cfg["temperature"] == pytest.approx(0.5)
    assert cfg["max_tokens"] == 2048


@patch("souschef.ui.pages.ai_settings.st")
def test_render_api_configuration_default_non_openai_provider(mock_st):
    from souschef.ui.pages.ai_settings import _render_api_configuration

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.text_input.return_value = "key"

    api_key, base_url, project_id = _render_api_configuration("Some Provider")
    assert api_key == "key"
    assert base_url == ""
    assert project_id == ""


@patch("souschef.ui.pages.ai_settings.st")
def test_show_ai_settings_page_back_button(mock_st):
    from souschef.ui.pages.ai_settings import show_ai_settings_page

    mock_st.session_state = SessionState()
    mock_st.columns.side_effect = lambda spec: [
        _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
    ]
    mock_st.selectbox.side_effect = ["OpenAI (GPT)", "gpt-4o"]
    mock_st.button.side_effect = [True, False]

    with (
        patch(
            "souschef.ui.pages.ai_settings._render_api_configuration",
            return_value=("key", "", ""),
        ),
        patch(
            "souschef.ui.pages.ai_settings._render_advanced_settings",
            return_value=(0.7, 4000),
        ),
        patch("souschef.ui.pages.ai_settings._render_validation_section"),
        patch("souschef.ui.pages.ai_settings.display_current_settings"),
    ):
        show_ai_settings_page()

    assert mock_st.session_state.current_page == "Dashboard"
    mock_st.rerun.assert_called_once()


@patch("souschef.ui.pages.ai_settings.st")
def test_validate_ai_configuration_watson_requires_project_id(mock_st):
    from souschef.ui.pages.ai_settings import WATSON_PROVIDER, validate_ai_configuration

    validate_ai_configuration(WATSON_PROVIDER, "api-key", "model", "", "")
    mock_st.error.assert_called_once()


@patch("souschef.ui.pages.ai_settings.st")
def test_validate_ai_configuration_provider_routes_and_result_handling(mock_st):
    from souschef.ui.pages.ai_settings import (
        ANTHROPIC_PROVIDER,
        LIGHTSPEED_PROVIDER,
        LOCAL_PROVIDER,
        OPENAI_PROVIDER,
        WATSON_PROVIDER,
        validate_ai_configuration,
    )

    mock_st.spinner.return_value = _ctx()

    with (
        patch(
            "souschef.ui.pages.ai_settings.validate_anthropic_config",
            return_value=(True, "ok"),
        ) as anthropic_validate,
        patch(
            "souschef.ui.pages.ai_settings.validate_openai_config",
            return_value=(False, "bad"),
        ) as openai_validate,
        patch(
            "souschef.ui.pages.ai_settings.validate_watson_config",
            return_value=(True, "ok"),
        ) as watson_validate,
        patch(
            "souschef.ui.pages.ai_settings.validate_lightspeed_config",
            return_value=(False, "bad"),
        ) as lightspeed_validate,
        patch(
            "souschef.ui.pages.ai_settings.validate_local_model_config",
            return_value=(True, "ok"),
        ) as local_validate,
    ):
        validate_ai_configuration(ANTHROPIC_PROVIDER, "k", "m")
        validate_ai_configuration(OPENAI_PROVIDER, "k", "m", "https://base")
        validate_ai_configuration(WATSON_PROVIDER, "k", "m", "https://base", "p")
        validate_ai_configuration(LIGHTSPEED_PROVIDER, "k", "m", "https://base")
        validate_ai_configuration(LOCAL_PROVIDER, "", "m", "https://local")

    anthropic_validate.assert_called_once_with("k", "m")
    openai_validate.assert_called_once_with("k", "m", "https://base")
    watson_validate.assert_called_once_with("k", "p", "https://base")
    lightspeed_validate.assert_called_once_with("k", "m", "https://base")
    local_validate.assert_called_once_with("https://local", "m")
    assert mock_st.success.call_count == 3
    assert mock_st.error.call_count >= 2


@patch("souschef.ui.pages.ai_settings.st")
def test_validate_ai_configuration_exception_path(mock_st):
    from souschef.ui.pages.ai_settings import (
        ANTHROPIC_PROVIDER,
        validate_ai_configuration,
    )

    mock_st.spinner.return_value = _ctx()
    with patch(
        "souschef.ui.pages.ai_settings.validate_anthropic_config",
        side_effect=RuntimeError("boom"),
    ):
        validate_ai_configuration(ANTHROPIC_PROVIDER, "k", "m")

    mock_st.error.assert_called_once()


def test_check_ollama_server_additional_branches():
    from souschef.ui.pages.ai_settings import _check_ollama_server

    with patch("souschef.ui.pages.ai_settings.requests", None):
        success, message = _check_ollama_server("https://localhost:11434", "m")
    assert not success
    assert "not installed" in message

    response_with_models = MagicMock(status_code=200)
    response_with_models.json.return_value = {
        "models": [{"name": "m1"}, {"name": "m2"}]
    }
    with patch(
        "souschef.ui.pages.ai_settings.requests.get",
        return_value=response_with_models,
    ):
        success2, message2 = _check_ollama_server("https://localhost:11434", "")
    assert success2
    assert "models" in message2.lower()

    response_not_ok = MagicMock(status_code=503)
    with patch(
        "souschef.ui.pages.ai_settings.requests.get", return_value=response_not_ok
    ):
        success3, message3 = _check_ollama_server("https://localhost:11434", "m")
    assert not success3
    assert "not responding" in message3.lower()


def test_check_openai_compatible_server_additional_branches():
    from souschef.ui.pages.ai_settings import _check_openai_compatible_server

    with patch("souschef.ui.pages.ai_settings.requests", None):
        success, message = _check_openai_compatible_server(
            "https://localhost:8000", "m"
        )
    assert not success
    assert "not installed" in message

    response_with_models = MagicMock(status_code=200)
    response_with_models.json.return_value = {"data": [{"id": "m1"}]}
    with patch(
        "souschef.ui.pages.ai_settings.requests.get",
        return_value=response_with_models,
    ):
        success2, message2 = _check_openai_compatible_server(
            "https://localhost:8000", ""
        )
    assert success2
    assert "openai-compatible" in message2.lower()

    response_no_models = MagicMock(status_code=200)
    response_no_models.json.return_value = {"data": []}
    with patch(
        "souschef.ui.pages.ai_settings.requests.get",
        return_value=response_no_models,
    ):
        success3, message3 = _check_openai_compatible_server(
            "https://localhost:8000", ""
        )
    assert not success3
    assert "no models" in message3.lower()


def test_validate_local_model_config_additional_branches():
    import requests as real_requests

    from souschef.ui.pages.ai_settings import validate_local_model_config

    with (
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            side_effect=ValueError("bad url"),
        ),
        patch("souschef.ui.pages.ai_settings.requests", MagicMock()),
    ):
        success, message = validate_local_model_config("bad", "m")
    assert not success
    assert "invalid local model server url" in message.lower()

    with (
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            return_value="https://localhost:11434",
        ),
        patch(
            "souschef.ui.pages.ai_settings._check_ollama_server",
            return_value=(False, "Ollama API not responding"),
        ),
        patch(
            "souschef.ui.pages.ai_settings._check_openai_compatible_server",
            return_value=(False, "OpenAI API not responding"),
        ),
        patch("souschef.ui.pages.ai_settings.requests", MagicMock()),
    ):
        success2, message2 = validate_local_model_config("", "m")
    assert not success2
    assert "cannot connect" in message2.lower()

    with (
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            return_value="https://localhost:11434",
        ),
        patch(
            "souschef.ui.pages.ai_settings._check_ollama_server",
            return_value=(False, "Ollama server found but no models available"),
        ),
        patch("souschef.ui.pages.ai_settings.requests", real_requests),
    ):
        success3, message3 = validate_local_model_config("", "m")
    assert not success3
    assert "at https://localhost:11434" in message3

    with (
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            return_value="https://localhost:11434",
        ),
        patch(
            "souschef.ui.pages.ai_settings._check_ollama_server",
            return_value=(False, "Ollama API not responding"),
        ),
        patch(
            "souschef.ui.pages.ai_settings._check_openai_compatible_server",
            return_value=(True, "OpenAI-compatible server running"),
        ),
        patch("souschef.ui.pages.ai_settings.requests", real_requests),
    ):
        success4, message4 = validate_local_model_config("", "m")
    assert success4
    assert "openai-compatible" in message4.lower()

    with (
        patch(
            "souschef.ui.pages.ai_settings.validate_user_provided_url",
            return_value="https://localhost:11434",
        ),
        patch(
            "souschef.ui.pages.ai_settings._check_ollama_server",
            side_effect=RuntimeError("boom"),
        ),
        patch("souschef.ui.pages.ai_settings.requests", real_requests),
    ):
        success5, message5 = validate_local_model_config("", "m")
    assert not success5
    assert "error validating" in message5.lower()


def test_validate_anthropic_config_success_and_exception():
    from souschef.ui.pages.ai_settings import validate_anthropic_config

    anthropic_mod = MagicMock()
    anthropic_mod.Anthropic.return_value.messages.create.return_value = {"ok": True}
    with patch("souschef.ui.pages.ai_settings.anthropic", anthropic_mod):
        success, message = validate_anthropic_config("k", "m")
    assert success
    assert "successfully connected" in message.lower()

    anthropic_fail = MagicMock()
    anthropic_fail.Anthropic.side_effect = RuntimeError("fail")
    with patch("souschef.ui.pages.ai_settings.anthropic", anthropic_fail):
        success2, message2 = validate_anthropic_config("k", "m")
    assert not success2
    assert "connection failed" in message2.lower()


def test_validate_openai_config_exception_path():
    from souschef.ui.pages.ai_settings import validate_openai_config

    with patch(
        "souschef.ui.pages.ai_settings.openai.OpenAI", side_effect=RuntimeError("x")
    ):
        success, message = validate_openai_config("k", "m")
    assert not success
    assert "connection failed" in message.lower()


def test_validate_lightspeed_config_success_and_exception():
    from souschef.ui.pages.ai_settings import validate_lightspeed_config

    response_ok = MagicMock(status_code=200)
    with (
        patch(
            "souschef.ui.pages.ai_settings._sanitize_lightspeed_base_url",
            return_value="https://api.redhat.com",
        ),
        patch("souschef.ui.pages.ai_settings.requests.post", return_value=response_ok),
    ):
        success, message = validate_lightspeed_config(
            "k", "m", "https://api.redhat.com"
        )
    assert success
    assert "successfully connected" in message.lower()

    with (
        patch(
            "souschef.ui.pages.ai_settings._sanitize_lightspeed_base_url",
            return_value="https://api.redhat.com",
        ),
        patch(
            "souschef.ui.pages.ai_settings.requests.post",
            side_effect=RuntimeError("fail"),
        ),
    ):
        success2, message2 = validate_lightspeed_config(
            "k", "m", "https://api.redhat.com"
        )
    assert not success2
    assert "connection failed" in message2.lower()


def test_validate_watson_config_no_models_and_exception():
    from souschef.ui.pages.ai_settings import validate_watson_config

    client = MagicMock()
    client.foundation_models.get_model_specs.return_value = []
    with patch("souschef.ui.pages.ai_settings.APIClient", return_value=client):
        success, message = validate_watson_config("k", "p")
    assert not success
    assert "no models" in message.lower()

    with patch(
        "souschef.ui.pages.ai_settings.APIClient", side_effect=RuntimeError("x")
    ):
        success2, message2 = validate_watson_config("k", "p")
    assert not success2
    assert "connection failed" in message2.lower()


@patch("souschef.ui.pages.ai_settings.st")
def test_save_ai_settings_exception(mock_st, tmp_path):
    from souschef.ui.pages.ai_settings import save_ai_settings

    mock_st.session_state = SessionState({"timestamp": "now"})
    with (
        patch("souschef.ui.pages.ai_settings.Path.home", return_value=tmp_path),
        patch("pathlib.Path.open", side_effect=OSError("denied")),
    ):
        save_ai_settings("OpenAI (GPT)", "secret", "gpt-4o", "", 0.7, 4096)

    mock_st.error.assert_called_once()


@patch("souschef.ui.pages.ai_settings.st")
def test_display_current_settings_no_api_key_warning(mock_st):
    from souschef.ui.pages.ai_settings import display_current_settings

    mock_st.columns.return_value = [_ctx(), _ctx()]
    with patch(
        "souschef.ui.pages.ai_settings.load_ai_settings",
        return_value={
            "provider": "OpenAI (GPT)",
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4000,
            "api_key": None,
        },
    ):
        display_current_settings()

    mock_st.warning.assert_called_once()


@patch("souschef.ui.pages.ai_settings.st")
def test_load_ai_settings_session_env_and_empty_paths(mock_st):
    from souschef.ui.pages.ai_settings import load_ai_settings

    mock_st.session_state = SessionState({"ai_config": {"provider": "Session"}})
    with (
        patch(
            "souschef.ui.pages.ai_settings._load_ai_settings_from_file", return_value={}
        ),
        patch(
            "souschef.ui.pages.ai_settings._load_ai_settings_from_env",
            return_value={"provider": "Env"},
        ),
    ):
        loaded = load_ai_settings()
    assert loaded["provider"] == "Session"

    mock_st.session_state = SessionState({"ai_config": {}})
    with (
        patch(
            "souschef.ui.pages.ai_settings._load_ai_settings_from_file", return_value={}
        ),
        patch(
            "souschef.ui.pages.ai_settings._load_ai_settings_from_env",
            return_value={"provider": "Env"},
        ),
    ):
        loaded2 = load_ai_settings()
    assert loaded2["provider"] == "Env"

    mock_st.session_state = SessionState({"ai_config": {}})
    with (
        patch(
            "souschef.ui.pages.ai_settings._load_ai_settings_from_file", return_value={}
        ),
        patch(
            "souschef.ui.pages.ai_settings._load_ai_settings_from_env", return_value={}
        ),
    ):
        loaded3 = load_ai_settings()
    assert loaded3 == {}


@patch("souschef.ui.pages.ai_settings.st")
def test_load_ai_settings_from_file_exception(mock_st, tmp_path):
    from souschef.ui.pages.ai_settings import _load_ai_settings_from_file

    config_dir = tmp_path / ".souschef"
    config_dir.mkdir()
    config_file = config_dir / "ai_config.json"
    config_file.write_text("{bad json")

    with patch("souschef.ui.pages.ai_settings.Path.home", return_value=tmp_path):
        result = _load_ai_settings_from_file()

    assert result == {}
    mock_st.warning.assert_called_once()


def test_module_optional_import_fallbacks_via_reimport():
    import builtins
    import importlib
    import sys

    module_name = "souschef.ui.pages.ai_settings"
    original_module = sys.modules.get(module_name)
    if module_name in sys.modules:
        del sys.modules[module_name]

    original_import = builtins.__import__

    def blocked_import(
        name, module_globals=None, module_locals=None, fromlist=(), level=0
    ):
        blocked = {
            "streamlit",
            "anthropic",
            "requests",
            "openai",
            "ibm_watsonx_ai",
        }
        if name in blocked:
            raise ImportError(f"blocked import: {name}")
        return original_import(name, module_globals, module_locals, fromlist, level)

    try:
        with patch("builtins.__import__", side_effect=blocked_import):
            mod = importlib.import_module(module_name)
            assert mod.st is None
            assert mod.anthropic is None
            assert mod.requests is None
            assert mod.openai is None
            assert mod.APIClient is None
    finally:
        if module_name in sys.modules:
            del sys.modules[module_name]
        if original_module is not None:
            sys.modules[module_name] = original_module
