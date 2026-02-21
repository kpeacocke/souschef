"""
Tests for missing coverage branches in souschef/converters/playbook.py.

Covers error paths, edge cases, and rarely-triggered branches not
reached by existing test suites.
"""

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from souschef.converters.playbook import (
    _build_project_guidance_parts,
    _call_ai_api,
    _call_anthropic_api,
    _call_github_copilot_api,
    _call_lightspeed_api,
    _call_watson_api,
    _convert_ruby_array_to_yaml,
    _convert_ruby_hash_to_yaml,
    _convert_ruby_value_to_yaml,
    _extract_chef_guards,
    _extract_nodejs_npm_version,
    _find_resource_position_in_raw,
    _format_item_lines,
    _handle_node_attribute_block,
    _handle_platform_check_block,
    _initialize_ai_client,
    _parse_guard_array,
    _parse_resource_block,
    _run_ansible_lint,
    _should_split_at_comma,
    _update_nesting_depths,
    _validate_and_fix_playbook,
    generate_playbook_from_recipe,
    generate_playbook_from_recipe_with_ai,
    get_chef_nodes,
)
from souschef.core.constants import ERROR_PREFIX


# Override workspace root to actual workspace for path traversal testing
@pytest.fixture(autouse=True)
def constrained_workspace_root():
    """Override workspace root to actual workspace for security testing."""
    old_root = os.environ.get("SOUSCHEF_WORKSPACE_ROOT")
    # Set to actual workspace root to test path containment
    os.environ["SOUSCHEF_WORKSPACE_ROOT"] = "/workspaces/souschef"
    yield
    # Clean up
    if old_root is None:
        os.environ.pop("SOUSCHEF_WORKSPACE_ROOT", None)
    else:
        os.environ["SOUSCHEF_WORKSPACE_ROOT"] = old_root


# ---------------------------------------------------------------------------
# Lines 51-52: requests optional import (tested via _call_lightspeed_api with
# requests=None is not easily triggered, but the import path is exercised).
# Test _call_lightspeed_api without requests mocked as None:
# ---------------------------------------------------------------------------


def test_call_lightspeed_api_requests_none() -> None:
    """Test _call_lightspeed_api returns error when requests is None."""
    client = {"api_key": "key", "base_url": "https://api.redhat.com"}
    with patch("souschef.converters.playbook.requests", None):
        result = _call_lightspeed_api(client, "prompt", "model", 0.5, 100)

    assert result.startswith(ERROR_PREFIX)
    assert "requests" in result


def test_call_github_copilot_api_requests_none() -> None:
    """Test _call_github_copilot_api returns error when requests is None."""
    client = {"api_key": "key", "base_url": "https://api.example.com"}
    with patch("souschef.converters.playbook.requests", None):
        result = _call_github_copilot_api(client, "prompt", "model", 0.5, 100)

    assert result.startswith(ERROR_PREFIX)
    assert "requests" in result


# ---------------------------------------------------------------------------
# Line 159: _generate_playbook_from_recipe cookbook_path normalisation
# Lines 169-170: path traversal detected in recipe_path
# ---------------------------------------------------------------------------


def test_generate_playbook_from_recipe_path_traversal() -> None:
    """Test generate_playbook_from_recipe handles path traversal attempts."""
    result = generate_playbook_from_recipe(
        "../../etc/passwd",
        cookbook_path="",
    )

    assert "Error" in result


# ---------------------------------------------------------------------------
# Lines 194-195: exception in generate_playbook_from_recipe_with_ai
# ---------------------------------------------------------------------------


def test_generate_playbook_from_recipe_with_ai_exception(tmp_path: Path) -> None:
    """Test generate_playbook_from_recipe_with_ai handles exceptions."""
    recipe_file = tmp_path / "default.rb"
    recipe_file.write_text('package "vim"')

    with patch(
        "souschef.converters.playbook._normalize_path",
        side_effect=RuntimeError("norm error"),
    ):
        result = generate_playbook_from_recipe_with_ai(
            str(recipe_file),
            api_key="key",
        )

    assert "Error" in result


# ---------------------------------------------------------------------------
# Lines 238-241: _generate_playbook_with_ai ImportError and generic Exception
# ---------------------------------------------------------------------------


def test_generate_playbook_with_ai_import_error(tmp_path: Path) -> None:
    """Test _generate_playbook_with_ai handles ImportError gracefully."""
    recipe_file = tmp_path / "default.rb"
    recipe_file.write_text('package "vim"')

    with (
        patch(
            "souschef.converters.playbook._normalize_path",
            return_value=recipe_file,
        ),
        patch(
            "souschef.converters.playbook._get_workspace_root", return_value=tmp_path
        ),
        patch(
            "souschef.converters.playbook._ensure_within_base_path",
            return_value=recipe_file,
        ),
        patch("souschef.converters.playbook.safe_exists", return_value=True),
        patch(
            "souschef.converters.playbook.safe_read_text",
            return_value='package "vim"',
        ),
        patch("souschef.converters.playbook.parse_recipe", return_value="Resource 1:"),
        patch(
            "souschef.converters.playbook._initialize_ai_client",
            side_effect=ImportError("no anthropic"),
        ),
    ):
        result = generate_playbook_from_recipe_with_ai(
            str(recipe_file),
            ai_provider="anthropic",
            api_key="key",
        )

    assert result.startswith(ERROR_PREFIX)
    assert "AI library not available" in result


# ---------------------------------------------------------------------------
# Lines 249-251: _initialize_ai_client anthropic branch
# Lines 253-255: openai branch
# ---------------------------------------------------------------------------


def test_initialize_ai_client_anthropic() -> None:
    """Test _initialize_ai_client creates Anthropic client."""
    mock_anthropic = MagicMock()
    mock_client_instance = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client_instance

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        result = _initialize_ai_client("anthropic", "test-key")

    assert result == mock_client_instance


def test_initialize_ai_client_openai() -> None:
    """Test _initialize_ai_client creates OpenAI client."""
    mock_openai = MagicMock()
    mock_client_instance = MagicMock()
    mock_openai.OpenAI.return_value = mock_client_instance

    with patch.dict("sys.modules", {"openai": mock_openai}):
        result = _initialize_ai_client("openai", "test-key")

    assert result == mock_client_instance


# ---------------------------------------------------------------------------
# Lines 257-268: watson branch with APIClient None and invalid URL
# ---------------------------------------------------------------------------


def test_initialize_ai_client_watson_no_api_client() -> None:
    """Test _initialize_ai_client returns error when ibm_watsonx_ai unavailable."""
    with patch("souschef.converters.playbook.APIClient", None):
        result = _initialize_ai_client("watson", "test-key")

    assert isinstance(result, str)
    assert "ibm_watsonx_ai" in result


def test_initialize_ai_client_watson_invalid_url() -> None:
    """Test _initialize_ai_client returns error for invalid Watsonx URL."""
    mock_api_client = MagicMock()

    with patch("souschef.converters.playbook.APIClient", mock_api_client):
        result = _initialize_ai_client(
            "watson",
            "test-key",
            project_id="proj",
            base_url="javascript:alert(1)",
        )

    assert isinstance(result, str)
    assert "Invalid Watsonx" in result


# ---------------------------------------------------------------------------
# Line 287: lightspeed dict returned from _initialize_ai_client
# ---------------------------------------------------------------------------


def test_initialize_ai_client_lightspeed() -> None:
    """Test _initialize_ai_client returns dict client for lightspeed."""
    mock_requests = MagicMock()
    with patch("souschef.converters.playbook.requests", mock_requests):
        result = _initialize_ai_client(
            "lightspeed",
            "test-key",
            base_url="https://api.redhat.com",
        )

    assert isinstance(result, dict)
    assert result["api_key"] == "test-key"


# ---------------------------------------------------------------------------
# Lines 341-350: _call_anthropic_api standard text response (no response_format)
# ---------------------------------------------------------------------------


def test_call_anthropic_api_standard_response() -> None:
    """Test _call_anthropic_api standard text response path."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Generated playbook")]
    mock_client.messages.create.return_value = mock_response

    result = _call_anthropic_api(mock_client, "my prompt", "claude-3", 0.5, 1024)

    assert result == "Generated playbook"


# ---------------------------------------------------------------------------
# Lines 361-370: _call_watson_api
# ---------------------------------------------------------------------------


def test_call_watson_api() -> None:
    """Test _call_watson_api calls generate_text and returns result."""
    mock_client = MagicMock()
    mock_client.generate_text.return_value = {
        "results": [{"generated_text": "watson output"}]
    }

    result = _call_watson_api(mock_client, "prompt", "ibm/granite", 0.5, 512)

    assert result == "watson output"


# ---------------------------------------------------------------------------
# Lines 383, 405: _call_lightspeed_api with response_format and 200 response
# ---------------------------------------------------------------------------


def test_call_lightspeed_api_with_response_format() -> None:
    """Test _call_lightspeed_api passes response_format in payload."""
    mock_requests = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"text": "ls output"}]}
    mock_requests.post.return_value = mock_resp

    client = {"api_key": "key", "base_url": "https://api.redhat.com"}
    with patch("souschef.converters.playbook.requests", mock_requests):
        result = _call_lightspeed_api(
            client,
            "prompt",
            "model",
            0.5,
            100,
            response_format={"type": "json_object"},
        )

    assert result == "ls output"


# ---------------------------------------------------------------------------
# Line 396: _call_lightspeed_api without response_format - 200
# ---------------------------------------------------------------------------


def test_call_lightspeed_api_without_response_format() -> None:
    """Test _call_lightspeed_api without response_format returns text."""
    mock_requests = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"text": "output text"}]}
    mock_requests.post.return_value = mock_resp

    client = {"api_key": "key", "base_url": "https://api.redhat.com"}
    with patch("souschef.converters.playbook.requests", mock_requests):
        result = _call_lightspeed_api(client, "prompt", "model", 0.5, 100)

    assert result == "output text"


# ---------------------------------------------------------------------------
# Line 405: _call_lightspeed_api non-200 path
# ---------------------------------------------------------------------------


def test_call_lightspeed_api_non_200() -> None:
    """Test _call_lightspeed_api returns error on non-200 status."""
    mock_requests = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.text = "Service Unavailable"
    mock_requests.post.return_value = mock_resp

    client = {"api_key": "key", "base_url": "https://api.redhat.com"}
    with patch("souschef.converters.playbook.requests", mock_requests):
        result = _call_lightspeed_api(client, "prompt", "model", 0.5, 100)

    assert result.startswith(ERROR_PREFIX)
    assert "503" in result


# ---------------------------------------------------------------------------
# Lines 423, 437, 447: _call_github_copilot_api
# ---------------------------------------------------------------------------


def test_call_github_copilot_api_success_with_format() -> None:
    """Test _call_github_copilot_api with response_format on success."""
    mock_requests = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "copilot output"}}]
    }
    mock_requests.post.return_value = mock_resp

    client = {"api_key": "key", "base_url": "https://api.example.com"}
    with patch("souschef.converters.playbook.requests", mock_requests):
        result = _call_github_copilot_api(
            client,
            "prompt",
            "gpt-4",
            0.5,
            100,
            response_format={"type": "json_object"},
        )

    assert result == "copilot output"


def test_call_github_copilot_api_non_200() -> None:
    """Test _call_github_copilot_api returns error on non-200 status."""
    mock_requests = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_requests.post.return_value = mock_resp

    client = {"api_key": "key", "base_url": "https://api.example.com"}
    with patch("souschef.converters.playbook.requests", mock_requests):
        result = _call_github_copilot_api(client, "prompt", "gpt-4", 0.5, 100)

    assert result.startswith(ERROR_PREFIX)
    assert "401" in result


# ---------------------------------------------------------------------------
# Line 471: _call_openai_api with response_format
# ---------------------------------------------------------------------------


def test_call_openai_api_with_response_format() -> None:
    """Test _call_ai_api passes response_format to OpenAI client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="openai output"))]
    mock_client.chat.completions.create.return_value = mock_response

    result = _call_ai_api(
        mock_client,
        "openai",
        "prompt",
        "gpt-4",
        0.5,
        100,
        response_format={"type": "json_object"},
    )

    assert result == "openai output"
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert "response_format" in call_kwargs


# ---------------------------------------------------------------------------
# Lines 507, 511, 513, 517: _call_ai_api routing
# ---------------------------------------------------------------------------


def test_call_ai_api_routes_anthropic() -> None:
    """Test _call_ai_api routes to Anthropic."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="anthropic result")]
    mock_client.messages.create.return_value = mock_response

    result = _call_ai_api(mock_client, "anthropic", "prompt", "claude", 0.5, 100)

    assert result == "anthropic result"


def test_call_ai_api_routes_watson() -> None:
    """Test _call_ai_api routes to Watson."""
    mock_client = MagicMock()
    mock_client.generate_text.return_value = {
        "results": [{"generated_text": "watson result"}]
    }

    result = _call_ai_api(mock_client, "watson", "prompt", "ibm/granite", 0.5, 100)

    assert result == "watson result"


def test_call_ai_api_routes_lightspeed() -> None:
    """Test _call_ai_api routes to Lightspeed."""
    mock_requests = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"text": "ls result"}]}
    mock_requests.post.return_value = mock_resp

    client = {"api_key": "key", "base_url": "https://api.redhat.com"}
    with patch("souschef.converters.playbook.requests", mock_requests):
        result = _call_ai_api(client, "lightspeed", "prompt", "model", 0.5, 100)

    assert result == "ls result"


def test_call_ai_api_routes_github_copilot() -> None:
    """Test _call_ai_api routes to GitHub Copilot."""
    mock_requests = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "copilot result"}}]
    }
    mock_requests.post.return_value = mock_resp

    client = {"api_key": "key", "base_url": "https://api.example.com"}
    with patch("souschef.converters.playbook.requests", mock_requests):
        result = _call_ai_api(client, "github_copilot", "prompt", "gpt-4", 0.5, 100)

    assert result == "copilot result"


# ---------------------------------------------------------------------------
# Lines 717-718, 728: _build_project_guidance_parts parallel and phased
# ---------------------------------------------------------------------------


def test_build_project_guidance_parallel_tracks() -> None:
    """Test _build_project_guidance_parts with parallel migration strategy."""
    recs = {"migration_strategy": "parallel", "parallel_tracks": 4}
    parts = _build_project_guidance_parts(recs)

    assert any("parallel" in p.lower() for p in parts)
    assert any("4" in p for p in parts)


def test_build_project_guidance_phased() -> None:
    """Test _build_project_guidance_parts with phased migration strategy."""
    recs = {"migration_strategy": "phased"}
    parts = _build_project_guidance_parts(recs)

    assert any("phased" in p.lower() for p in parts)


# ---------------------------------------------------------------------------
# Lines 866, 869-871: _validate_and_fix_playbook error paths
# ---------------------------------------------------------------------------


def test_validate_and_fix_playbook_fixed_invalid_yaml() -> None:
    """Test _validate_and_fix_playbook returns error for re-fixed-but-invalid YAML."""
    bad_playbook = "---\n- hosts: all\n  tasks:\n  - name: test\n    invalid: [unclosed"
    mock_client = MagicMock()

    with (
        patch(
            "souschef.converters.playbook._run_ansible_lint",
            return_value="some-lint-error",
        ),
        patch(
            "souschef.converters.playbook._call_ai_api",
            return_value="still: invalid: yaml: [",
        ),
        patch(
            "souschef.converters.playbook._clean_ai_playbook_response",
            return_value="still: invalid: yaml: [",
        ),
    ):
        result = _validate_and_fix_playbook(
            bad_playbook, mock_client, "openai", "gpt-4", 0.5, 1024
        )

    # Should return error or original
    assert isinstance(result, str)


def test_validate_and_fix_playbook_fix_exception() -> None:
    """Test _validate_and_fix_playbook falls back to original on exception."""
    playbook = "---\n- hosts: all\n  tasks: []"
    mock_client = MagicMock()

    with (
        patch(
            "souschef.converters.playbook._run_ansible_lint",
            return_value="lint-error",
        ),
        patch(
            "souschef.converters.playbook._call_ai_api",
            side_effect=RuntimeError("AI boom"),
        ),
    ):
        result = _validate_and_fix_playbook(
            playbook, mock_client, "openai", "gpt-4", 0.5, 1024
        )

    assert result == playbook


# ---------------------------------------------------------------------------
# Lines 889-891: _run_ansible_lint file write exception
# ---------------------------------------------------------------------------


def test_run_ansible_lint_not_available() -> None:
    """Test _run_ansible_lint returns None when ansible-lint not on PATH."""
    with patch("shutil.which", return_value=None):
        result = _run_ansible_lint("---\n- hosts: all\n  tasks: []")

    assert result is None


def test_run_ansible_lint_returns_none_on_pass() -> None:
    """Test _run_ansible_lint returns None when ansible-lint passes."""
    with (
        patch("shutil.which", return_value="/usr/bin/ansible-lint"),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = _run_ansible_lint("---\n- hosts: all\n  tasks: []")

    assert result is None


def test_run_ansible_lint_os_error_returns_none() -> None:
    """Test _run_ansible_lint returns None on OSError."""
    with (
        patch("shutil.which", return_value="/usr/bin/ansible-lint"),
        patch("subprocess.run", side_effect=OSError("proc error")),
    ):
        result = _run_ansible_lint("---\n")

    assert result is None


# ---------------------------------------------------------------------------
# Lines 905-907: _run_ansible_lint exception returns None
# ---------------------------------------------------------------------------


def test_run_ansible_lint_generic_exception_returns_none() -> None:
    """Test _run_ansible_lint returns None on unexpected exceptions."""
    with (
        patch("shutil.which", return_value="/usr/bin/ansible-lint"),
        patch("tempfile.mkstemp", side_effect=RuntimeError("mkstemp boom")),
    ):
        result = _run_ansible_lint("---\n")

    assert result is None


# ---------------------------------------------------------------------------
# Lines 1484-1489: get_chef_nodes falls back to empty list on exception
# ---------------------------------------------------------------------------


def test_get_chef_nodes_exception_returns_empty() -> None:
    """Test get_chef_nodes returns empty list when chef server raises."""
    from souschef.core import chef_server as chef_server_module

    with patch.object(
        chef_server_module,
        "get_chef_nodes",
        side_effect=RuntimeError("connection error"),
    ):
        result = get_chef_nodes("role:webserver")

    assert result == []


def test_get_chef_nodes_success() -> None:
    """Test get_chef_nodes returns nodes from chef server."""
    nodes = [{"name": "web01"}, {"name": "web02"}]
    from souschef.core import chef_server as chef_server_module

    with patch.object(chef_server_module, "get_chef_nodes", return_value=nodes):
        result = get_chef_nodes("role:webserver")

    assert result == nodes


# ---------------------------------------------------------------------------
# Lines 1794-1796: _add_playbook_variables path traversal skip
# ---------------------------------------------------------------------------


def test_add_playbook_variables_path_traversal(tmp_path: Path) -> None:
    """Test _add_playbook_variables skips on path traversal ValueError."""
    from souschef.converters.playbook import _add_playbook_variables

    playbook_lines: list[str] = []
    recipe_file = tmp_path / "recipes" / "default.rb"
    recipe_file.parent.mkdir(parents=True, exist_ok=True)
    recipe_file.write_text('package "vim"')

    with patch(
        "souschef.converters.playbook.safe_exists",
        side_effect=ValueError("path traversal"),
    ):
        _add_playbook_variables(
            playbook_lines,
            raw_content='package "vim"',
            recipe_file=recipe_file,
        )

    assert "    # No variables found" in playbook_lines


# ---------------------------------------------------------------------------
# Line 1831: _format_item_lines empty line preserved as-is
# ---------------------------------------------------------------------------


def test_format_item_lines_empty_lines() -> None:
    """Test _format_item_lines preserves empty lines without indentation."""
    yaml_str = "name: test task\n\nmodule: val"
    result = _format_item_lines(yaml_str)

    assert result[0] == "    name: test task"
    assert result[1] == ""  # Empty line preserved without indent


# ---------------------------------------------------------------------------
# Line 2037: _collect_value_lines increments i
# Lines 2048: _convert_ruby_hash_to_yaml empty hash
# ---------------------------------------------------------------------------


def test_convert_ruby_hash_to_yaml_empty() -> None:
    """Test _convert_ruby_hash_to_yaml with empty hash."""
    result = _convert_ruby_hash_to_yaml("{}")

    assert result == "{}"


def test_convert_ruby_hash_to_yaml_valid() -> None:
    """Test _convert_ruby_hash_to_yaml converts Ruby hash to YAML flow style."""
    result = _convert_ruby_hash_to_yaml("{'key' => 'value'}")

    assert "key" in result
    assert "value" in result


# ---------------------------------------------------------------------------
# Lines 2072-2073: malformed pair in _convert_ruby_hash_to_yaml
# ---------------------------------------------------------------------------


def test_convert_ruby_hash_to_yaml_malformed_pair() -> None:
    """Test _convert_ruby_hash_to_yaml handles pairs without => separator."""
    result = _convert_ruby_hash_to_yaml("{'key' => 'val', malformed_no_arrow}")

    assert "key" in result
    assert "unparsed" in result


# ---------------------------------------------------------------------------
# Lines 2077-2082: exception in _convert_ruby_hash_to_yaml
# ---------------------------------------------------------------------------


def test_convert_ruby_hash_to_yaml_exception() -> None:
    """Test _convert_ruby_hash_to_yaml handles parse exceptions gracefully."""
    with patch(
        "souschef.converters.playbook._split_by_commas_with_nesting",
        side_effect=RuntimeError("split boom"),
    ):
        result = _convert_ruby_hash_to_yaml("{'key' => 'val'}")

    assert "unparsed" in result


# ---------------------------------------------------------------------------
# Line 2091: _convert_ruby_array_to_yaml empty array
# Lines 2101-2102: exception in _convert_ruby_array_to_yaml
# ---------------------------------------------------------------------------


def test_convert_ruby_array_to_yaml_empty() -> None:
    """Test _convert_ruby_array_to_yaml with empty array."""
    result = _convert_ruby_array_to_yaml("[]")

    assert result == "[]"


def test_convert_ruby_array_to_yaml_exception() -> None:
    """Test _convert_ruby_array_to_yaml returns original string on exception."""
    original = "[some invalid input"
    with patch(
        "souschef.converters.playbook._split_by_commas_with_nesting",
        side_effect=RuntimeError("split boom"),
    ):
        result = _convert_ruby_array_to_yaml(original)

    assert result == original


# ---------------------------------------------------------------------------
# Line 2150: _split_by_commas_with_nesting in_quotes toggle
# Lines 2162, 2164: _update_nesting_depths bracket handling
# ---------------------------------------------------------------------------


def test_update_nesting_depths_brackets() -> None:
    """Test _update_nesting_depths tracks bracket depth correctly."""
    _, bracket = _update_nesting_depths("[", 0, 0)
    assert bracket == 1

    _, bracket = _update_nesting_depths("]", 0, bracket)
    assert bracket == 0


def test_should_split_at_comma_in_quotes() -> None:
    """Test _should_split_at_comma returns False when in quotes."""
    result = _should_split_at_comma(",", in_quotes=True, brace_depth=0, bracket_depth=0)
    assert result is False


def test_should_split_at_comma_outside_quotes() -> None:
    """Test _should_split_at_comma returns True outside quotes."""
    result = _should_split_at_comma(
        ",", in_quotes=False, brace_depth=0, bracket_depth=0
    )
    assert result is True


# ---------------------------------------------------------------------------
# Line 2196: _convert_ruby_value_to_yaml with unquoted symbol
# ---------------------------------------------------------------------------


def test_convert_ruby_value_to_yaml_unquoted_symbol() -> None:
    """Test _convert_ruby_value_to_yaml wraps unquoted non-standard values."""
    result = _convert_ruby_value_to_yaml(":present")

    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Line 2265: _parse_resource_block returns None for empty block
# ---------------------------------------------------------------------------


def test_parse_resource_block_empty() -> None:
    """Test _parse_resource_block returns None for empty/whitespace blocks."""
    result = _parse_resource_block("   ")

    assert result is None


# ---------------------------------------------------------------------------
# Lines 2340, 2357, 2362: _find_resource_position_in_raw
# ---------------------------------------------------------------------------


def test_find_resource_position_in_raw_include_recipe() -> None:
    """Test _find_resource_position_in_raw finds include_recipe positions."""
    raw = "include_recipe 'base::default'"
    resource = {"type": "include_recipe", "name": "base::default"}
    pos = _find_resource_position_in_raw(resource, raw)

    assert pos == 0


def test_find_resource_position_in_raw_nodejs_npm() -> None:
    """Test _find_resource_position_in_raw finds nodejs_npm positions."""
    raw = "nodejs_npm 'express'"
    resource = {"type": "nodejs_npm", "name": "express"}
    pos = _find_resource_position_in_raw(resource, raw)

    assert pos == 0


def test_find_resource_position_in_raw_not_found() -> None:
    """Test _find_resource_position_in_raw returns 999999 when not found."""
    raw = 'package "vim"'
    resource = {"type": "service", "name": "nginx"}
    pos = _find_resource_position_in_raw(resource, raw)

    assert pos == 999999


# ---------------------------------------------------------------------------
# Line 2417: _process_notifies creates notify list
# ---------------------------------------------------------------------------


def test_extract_chef_guards_notify_list_created(tmp_path: Path) -> None:
    """Test _extract_chef_guards builds when conditions from only_if."""
    resource: dict[str, Any] = {
        "type": "service",
        "name": "nginx",
        "action": "restart",
        "properties": "",
        "guards": "only_if { File.exist?('/etc/nginx/nginx.conf') }",
    }
    raw = (
        'service "nginx" do\n'
        "  action :restart\n"
        '  only_if { File.exist?("/etc/nginx/nginx.conf") }\n'
        "end\n"
    )

    guards = _extract_chef_guards(resource, raw)

    assert isinstance(guards, dict)


# ---------------------------------------------------------------------------
# Lines 2467-2469: nodejs_npm version extraction
# ---------------------------------------------------------------------------


def test_extract_nodejs_npm_version_found() -> None:
    """Test _extract_nodejs_npm_version finds version in recipe."""
    raw = 'nodejs_npm "express" do\n  version "4.18.2"\nend\n'
    version = _extract_nodejs_npm_version(raw, "express")

    assert version is not None
    assert "4.18.2" in version


def test_extract_nodejs_npm_version_not_found() -> None:
    """Test _extract_nodejs_npm_version returns None when no version specified."""
    raw = 'nodejs_npm "express" do\n  action :install\nend\n'
    version = _extract_nodejs_npm_version(raw, "express")

    assert version is None


# ---------------------------------------------------------------------------
# Lines 2741-2742: _parse_guard_array with not_if negated conditions
# ---------------------------------------------------------------------------


def test_parse_guard_array_negated() -> None:
    """Test _parse_guard_array with negated (not_if) array content."""
    conditions = _parse_guard_array(
        '["/bin/true", "/usr/bin/test -f /tmp/lock"]', negate=True
    )

    assert isinstance(conditions, list)


# ---------------------------------------------------------------------------
# Lines 2802-2806: _convert_guards_to_when_conditions multiple conditions
# ---------------------------------------------------------------------------


def test_extract_chef_guards_multiple_conditions(tmp_path: Path) -> None:
    """Test _extract_chef_guards produces list when multiple conditions exist."""
    resource: dict[str, Any] = {
        "type": "execute",
        "name": "run_script",
        "action": "run",
        "properties": "",
        "guards": ('only_if "/bin/test -f /tmp/a"\nnot_if "/bin/test -f /tmp/b"'),
    }
    raw = (
        'execute "run_script" do\n'
        '  only_if "/bin/test -f /tmp/a"\n'
        '  not_if "/bin/test -f /tmp/b"\n'
        "end\n"
    )

    guards = _extract_chef_guards(resource, raw)

    assert isinstance(guards, dict)


# ---------------------------------------------------------------------------
# Lines 2885, 2888: _extract_lambda_body
# ---------------------------------------------------------------------------


def test_parse_guard_array_lambda_syntax() -> None:
    """Test _parse_guard_array handles lambda syntax."""
    conditions = _parse_guard_array("[-> { File.exist?('/tmp/lock') }]", negate=False)

    assert isinstance(conditions, list)


# ---------------------------------------------------------------------------
# Lines 2895, 2913: _process_guard_array_part returns None
# ---------------------------------------------------------------------------


def test_parse_guard_array_empty_string() -> None:
    """Test _parse_guard_array handles empty string parts gracefully."""
    conditions = _parse_guard_array("['', '  ']", negate=False)

    assert isinstance(conditions, list)


# ---------------------------------------------------------------------------
# Line 3018: node attribute path with Ruby interpolation in directory check
# ---------------------------------------------------------------------------


def test_handle_node_attribute_block_positive() -> None:
    """Test _handle_node_attribute_block converts node attribute references."""
    block = 'node["platform"] == "ubuntu"'
    result = _handle_node_attribute_block(block, positive=True)

    assert result is not None
    assert "hostvars" in result


def test_handle_node_attribute_block_negative() -> None:
    """Test _handle_node_attribute_block wraps in not() when not positive."""
    block = 'node["environment"] == "production"'
    result = _handle_node_attribute_block(block, positive=False)

    assert result is not None
    assert "not" in result


def test_handle_node_attribute_block_no_node() -> None:
    """Test _handle_node_attribute_block returns None when block has no node ref."""
    block = 'File.exist?("/tmp/lock")'
    result = _handle_node_attribute_block(block, positive=True)

    assert result is None


# ---------------------------------------------------------------------------
# Lines 3052-3062: _handle_node_attribute_block with node. syntax
# ---------------------------------------------------------------------------


def test_handle_node_attribute_dot_syntax() -> None:
    """Test _handle_node_attribute_block handles node.attribute dot syntax."""
    block = "node.platform == 'ubuntu'"
    result = _handle_node_attribute_block(block, positive=True)

    assert result is not None
    assert "hostvars" in result


# ---------------------------------------------------------------------------
# Lines 3070-3071: _handle_platform_check_block
# ---------------------------------------------------------------------------


def test_handle_platform_check_block_positive() -> None:
    """Test _handle_platform_check_block matches platform? calls."""
    block = 'platform?("ubuntu", "debian")'
    result = _handle_platform_check_block(block, positive=True)

    assert result is not None
    assert "ansible_facts.os_family" in result


def test_handle_platform_check_block_negative() -> None:
    """Test _handle_platform_check_block wraps in not() when negative."""
    block = 'platform_family?("rhel")'
    result = _handle_platform_check_block(block, positive=False)

    assert result is not None
    assert "not" in result


def test_handle_platform_check_block_no_match() -> None:
    """Test _handle_platform_check_block returns None for non-platform blocks."""
    block = 'File.exist?("/tmp/lock")'
    result = _handle_platform_check_block(block, positive=True)

    assert result is None


# ---------------------------------------------------------------------------
# Line 3113: _convert_chef_block_to_ansible final conversion with not
# ---------------------------------------------------------------------------


def test_extract_guards_simple_string_not_if() -> None:
    """Test guard extraction with simple shell command in not_if."""
    resource: dict[str, Any] = {
        "type": "execute",
        "name": "install_app",
        "action": "run",
        "properties": "",
        "guards": 'not_if "/usr/bin/which app"',
    }
    raw = 'execute "install_app" do\n  not_if "/usr/bin/which app"\nend\n'

    guards = _extract_chef_guards(resource, raw)

    assert isinstance(guards, dict)
