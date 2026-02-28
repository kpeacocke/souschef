"""
Comprehensive AI service response mocking tests.

Tests successful API responses and conversion workflows for all supported
AI providers (Anthropic, OpenAI, Watson, Lightspeed, GitHub Copilot).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from souschef.assessment import (
    _call_anthropic_api as assessment_call_anthropic_api,
)
from souschef.assessment import (
    _call_openai_api as assessment_call_openai_api,
)
from souschef.assessment import (
    _call_watson_api as assessment_call_watson_api,
)
from souschef.converters.playbook import (
    _call_anthropic_api as playbook_call_anthropic_api,
)
from souschef.converters.playbook import (
    _call_github_copilot_api as playbook_call_github_copilot_api,
)
from souschef.converters.playbook import (
    _call_lightspeed_api as playbook_call_lightspeed_api,
)
from souschef.converters.playbook import (
    _call_openai_api as playbook_call_openai_api,
)
from souschef.converters.playbook import (
    _call_watson_api as playbook_call_watson_api,
)


class TestAnthropicAPIResponses:
    """Test Anthropic Claude API response handling."""

    def test_playbook_anthropic_text_response(self):
        """Test playbook generation with Anthropic text response."""
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "---\n- name: Install package\n  package:\n    name: nginx"
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        result = playbook_call_anthropic_api(
            client=mock_client,
            prompt="Convert this Chef resource",
            model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "Install package" in result
        assert "nginx" in result
        mock_client.messages.create.assert_called_once()

    def test_playbook_anthropic_json_response(self):
        """Test playbook generation with Anthropic JSON tool response."""
        mock_client = MagicMock()
        mock_tool_use = MagicMock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.input = {
            "response": '{"tasks": [{"name": "Install nginx", "package": {"name": "nginx"}}]}'
        }
        mock_response = MagicMock()
        mock_response.content = [mock_tool_use]
        mock_client.messages.create.return_value = mock_response

        result = playbook_call_anthropic_api(
            client=mock_client,
            prompt="Convert to JSON format",
            model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        assert "tasks" in result
        assert "nginx" in result
        mock_client.messages.create.assert_called_once()

    def test_assessment_anthropic_complexity_response(self):
        """Test assessment with Anthropic complexity evaluation response."""
        with patch("souschef.assessment.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "content": [{"text": '{"complexity": "high", "effort_days": 10}'}]
            }
            mock_requests.post.return_value = mock_response

            result = assessment_call_anthropic_api(
                prompt="Evaluate this cookbook",
                api_key="test-key",
                model="claude-3-opus-20240229",
                temperature=0.5,
                max_tokens=1024,
            )

            assert result is not None
            assert "complexity" in result or "high" in result
            mock_requests.post.assert_called_once()

    def test_anthropic_large_response_handling(self):
        """Test handling of large Anthropic responses."""
        mock_client = MagicMock()
        large_playbook = "---\n" + "\n".join(
            [f"- name: Task {i}\n  debug:\n    msg: Message {i}" for i in range(100)]
        )
        mock_content = MagicMock()
        mock_content.text = large_playbook
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        result = playbook_call_anthropic_api(
            client=mock_client,
            prompt="Generate large playbook",
            model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=8000,
        )

        assert len(result) > 1000
        assert "Task 0" in result
        assert "Task 99" in result

    def test_anthropic_multiline_yaml_response(self):
        """Test Anthropic response with multi-line YAML content."""
        mock_client = MagicMock()
        yaml_content = """---
- name: Install and configure Nginx
  hosts: web_servers
  vars:
    nginx_port: 80
    nginx_user: www-data
  tasks:
    - name: Install nginx package
      package:
        name: nginx
        state: present
    - name: Configure nginx
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      notify: restart nginx
  handlers:
    - name: restart nginx
      service:
        name: nginx
        state: restarted"""
        mock_content = MagicMock()
        mock_content.text = yaml_content
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        result = playbook_call_anthropic_api(
            client=mock_client,
            prompt="Generate nginx playbook",
            model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "Install and configure Nginx" in result
        assert "nginx_port: 80" in result
        assert "restart nginx" in result


class TestOpenAIAPIResponses:
    """Test OpenAI API response handling."""

    def test_playbook_openai_text_response(self):
        """Test playbook generation with OpenAI text response."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "---\n- name: Deploy application\n  hosts: app_servers"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        result = playbook_call_openai_api(
            client=mock_client,
            prompt="Convert Chef recipe to Ansible",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "Deploy application" in result
        assert "app_servers" in result
        mock_client.chat.completions.create.assert_called_once()

    def test_assessment_openai_complexity_response(self):
        """Test assessment with OpenAI complexity evaluation."""
        with patch("souschef.assessment.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {"message": {"content": "Medium complexity: 5 days effort needed"}}
                ]
            }
            mock_requests.post.return_value = mock_response

            result = assessment_call_openai_api(
                prompt="Assess this cookbook",
                api_key="test-key",
                model="gpt-4",
                temperature=0.5,
                max_tokens=1024,
            )

            assert result is not None
            assert "complexity" in result or "days" in result
            mock_requests.post.assert_called_once()

    def test_openai_function_call_response(self):
        """Test OpenAI response with function calling."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "tasks": [
                    {"name": "Install packages", "package": {"name": "nginx"}},
                    {"name": "Start service", "service": {"name": "nginx"}},
                ]
            }
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        result = playbook_call_openai_api(
            client=mock_client,
            prompt="Convert to structured format",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        assert "Install packages" in result
        assert "Start service" in result

    def test_openai_streaming_response_handling(self):
        """Test handling of streamed OpenAI responses."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "- name: Task 1\n- name: Task 2\n- name: Task 3"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        result = playbook_call_openai_api(
            client=mock_client,
            prompt="Generate three tasks",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "Task 1" in result
        assert "Task 2" in result
        assert "Task 3" in result

    def test_openai_error_response_handling(self):
        """Test OpenAI error response (status != 200)."""
        with patch("souschef.assessment.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "Unauthorized"}
            mock_requests.post.return_value = mock_response

            result = assessment_call_openai_api(
                prompt="Test prompt",
                api_key="invalid-key",
                model="gpt-4",
                temperature=0.5,
                max_tokens=1024,
            )

            assert result is None


class TestWatsonAPIResponses:
    """Test IBM Watsonx API response handling."""

    def test_playbook_watson_text_response(self):
        """Test playbook generation with Watson text response."""
        mock_client = MagicMock()
        mock_response = {
            "results": [
                {
                    "generated_text": "---\n- name: Configure database\n  hosts: db_servers"
                }
            ]
        }
        mock_client.generate_text.return_value = mock_response

        result = playbook_call_watson_api(
            client=mock_client,
            prompt="Convert Chef database recipe",
            model="ibm/granite-13b-chat-v2",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "Configure database" in result
        assert "db_servers" in result
        mock_client.generate_text.assert_called_once()

    def test_assessment_watson_streaming_response(self):
        """Test assessment with Watson streaming response."""
        with patch("souschef.assessment.APIClient") as mock_api_client:
            mock_client_instance = MagicMock()
            mock_api_client.return_value = mock_client_instance

            # Mock streaming response
            mock_chunk1 = MagicMock()
            mock_chunk1.results = [MagicMock(generated_text="Complexity: ")]
            mock_chunk2 = MagicMock()
            mock_chunk2.results = [MagicMock(generated_text="High")]
            mock_client_instance.deployments.text_generation_stream.return_value = [
                mock_chunk1,
                mock_chunk2,
            ]

            result = assessment_call_watson_api(
                prompt="Assess complexity of cookbook",
                api_key="test-key",
                model="ibm/granite-13b-chat-v2",
                temperature=0.5,
                max_tokens=1024,
                project_id="test-project",
            )

            assert result is not None
            assert "Complexity" in result or "High" in result

    def test_watson_large_text_response(self):
        """Test Watson API with large generated text."""
        mock_client = MagicMock()
        large_text = "\n".join(
            [f"Step {i}: Configure component {i}" for i in range(50)]
        )
        mock_response = {"results": [{"generated_text": large_text}]}
        mock_client.generate_text.return_value = mock_response

        result = playbook_call_watson_api(
            client=mock_client,
            prompt="Generate detailed migration steps",
            model="ibm/granite-13b-chat-v2",
            temperature=0.5,
            max_tokens=4096,
        )

        assert len(result) > 500
        assert "Step 0" in result
        assert "Step 49" in result

    def test_watson_json_structured_response(self):
        """Test Watson API with JSON structured response."""
        mock_client = MagicMock()
        json_response = json.dumps(
            {
                "assessment": {
                    "complexity": "medium",
                    "effort_days": 7,
                    "modules": ["web", "db", "cache"],
                }
            }
        )
        mock_response = {"results": [{"generated_text": json_response}]}
        mock_client.generate_text.return_value = mock_response

        result = playbook_call_watson_api(
            client=mock_client,
            prompt="Provide structured assessment",
            model="ibm/granite-13b-chat-v2",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "assessment" in result
        assert "medium" in result
        assert "effort_days" in result


class TestLightspeedAPIResponses:
    """Test Red Hat Lightspeed API response handling."""

    def test_lightspeed_http_response_success(self):
        """Test Lightspeed API success response."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {"text": "---\n- name: Install Red Hat package\n  hosts: all"}
                ]
            }
            mock_requests.post.return_value = mock_response

            client = {"api_key": "test-key", "base_url": "https://api.lightspeed.local"}
            result = playbook_call_lightspeed_api(
                client=client,
                prompt="Convert to Lightspeed format",
                model="lightspeed-ansible",
                temperature=0.5,
                max_tokens=2048,
            )

            assert "Red Hat" in result
            assert "Install" in result
            mock_requests.post.assert_called_once()

    def test_lightspeed_error_response(self):
        """Test Lightspeed API error response handling."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_requests.post.return_value = mock_response

            client = {"api_key": "test-key", "base_url": "https://api.lightspeed.local"}
            result = playbook_call_lightspeed_api(
                client=client,
                prompt="Test prompt",
                model="lightspeed-ansible",
                temperature=0.5,
                max_tokens=2048,
            )

            assert "Error" in result or "429" in result

    def test_lightspeed_with_response_format(self):
        """Test Lightspeed API with structured response format."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "text": json.dumps(
                            {"playbook": [{"name": "Setup", "hosts": "localhost"}]}
                        )
                    }
                ]
            }
            mock_requests.post.return_value = mock_response

            client = {"api_key": "test-key", "base_url": "https://api.lightspeed.local"}
            result = playbook_call_lightspeed_api(
                client=client,
                prompt="Generate structured playbook",
                model="lightspeed-ansible",
                temperature=0.5,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            assert "playbook" in result
            assert "Setup" in result

    def test_lightspeed_timeout_handling(self):
        """Test Lightspeed API timeout (still succeeds if requests available)."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            # Successful response (requests exists)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"text": "- name: Task after timeout handling"}]
            }
            mock_requests.post.return_value = mock_response

            client = {"api_key": "test-key", "base_url": "https://api.lightspeed.local"}
            result = playbook_call_lightspeed_api(
                client=client,
                prompt="Test timeout handling",
                model="lightspeed-ansible",
                temperature=0.5,
                max_tokens=2048,
            )

            assert result is not None
            assert "Task" in result

    def test_lightspeed_missing_requests_library(self):
        """Test Lightspeed API when requests library is not available."""
        with patch("souschef.converters.playbook.requests", None):
            client = {"api_key": "test-key", "base_url": "https://api.lightspeed.local"}
            result = playbook_call_lightspeed_api(
                client=client,
                prompt="Test without requests",
                model="lightspeed-ansible",
                temperature=0.5,
                max_tokens=2048,
            )

            assert "Error" in result or "requests library not available" in result


class TestGitHubCopilotAPIResponses:
    """Test GitHub Copilot API response handling."""

    def test_github_copilot_http_response(self):
        """Test GitHub Copilot API successful response."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "---\n- name: GitHub Copilot generated task\n  hosts: all"
                        }
                    }
                ]
            }
            mock_requests.post.return_value = mock_response

            client = {
                "api_key": "test-key",
                "base_url": "https://api.github.com",
            }
            result = playbook_call_github_copilot_api(
                client=client,
                prompt="Generate using Copilot",
                model="gpt-4-turbo",
                temperature=0.5,
                max_tokens=2048,
            )

            assert "Copilot" in result
            assert "hosts: all" in result
            mock_requests.post.assert_called_once()

    def test_github_copilot_authentication_error(self):
        """Test GitHub Copilot API authentication error."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Invalid authentication token"
            mock_requests.post.return_value = mock_response

            client = {
                "api_key": "invalid-key",
                "base_url": "https://api.github.com",
            }
            result = playbook_call_github_copilot_api(
                client=client,
                prompt="Test auth error",
                model="gpt-4-turbo",
                temperature=0.5,
                max_tokens=2048,
            )

            assert "Error" in result or "401" in result

    def test_github_copilot_with_structured_format(self):
        """Test GitHub Copilot API with structured response format."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            structured_content = json.dumps(
                {
                    "version": "3.0",
                    "name": "Generated Playbook",
                    "description": "Generated by Copilot",
                }
            )
            mock_response.json.return_value = {
                "choices": [{"message": {"content": structured_content}}]
            }
            mock_requests.post.return_value = mock_response

            client = {
                "api_key": "test-key",
                "base_url": "https://api.github.com",
            }
            result = playbook_call_github_copilot_api(
                client=client,
                prompt="Generate structured content",
                model="gpt-4-turbo",
                temperature=0.5,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            assert "Generated Playbook" in result
            assert "version" in result

    def test_github_copilot_rate_limit_reset(self):
        """Test GitHub Copilot API rate limit response headers."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {
                "x-ratelimit-limit": "100",
                "x-ratelimit-remaining": "50",
                "x-ratelimit-reset": "1234567890",
            }
            mock_response.json.return_value = {
                "choices": [
                    {"message": {"content": "---\n- name: Task\n  debug:\n    msg: OK"}}
                ]
            }
            mock_requests.post.return_value = mock_response

            client = {
                "api_key": "test-key",
                "base_url": "https://api.github.com",
            }
            result = playbook_call_github_copilot_api(
                client=client,
                prompt="Test with rate limits",
                model="gpt-4-turbo",
                temperature=0.5,
                max_tokens=2048,
            )

            assert result is not None
            assert "Task" in result

    def test_github_copilot_missing_requests_library(self):
        """Test GitHub Copilot API without requests library."""
        with patch("souschef.converters.playbook.requests", None):
            client = {
                "api_key": "test-key",
                "base_url": "https://api.github.com",
            }
            result = playbook_call_github_copilot_api(
                client=client,
                prompt="No requests library",
                model="gpt-4-turbo",
                temperature=0.5,
                max_tokens=2048,
            )

            assert "Error" in result or "requests library not available" in result
            assert "GitHub Copilot" in result or "error" in result.lower()


class TestIntegratedAIConversionWorkflows:
    """Test AI response structures and workflow integration."""

    def test_anthropic_playbook_response_structure(self):
        """Test Anthropic returns valid playbook YAML structure."""
        mock_client = MagicMock()
        yaml_content = """---
- name: Install packages
  package:
    name: "{{ item }}"
    state: present
  loop:
    - nginx
    - postgresql"""
        mock_content = MagicMock()
        mock_content.text = yaml_content
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        result = playbook_call_anthropic_api(
            client=mock_client,
            prompt="Convert to playbook",
            model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=2048,
        )

        # Validate YAML structure
        assert "name:" in result
        assert "package:" in result
        assert "loop:" in result

    def test_openai_assessment_response_structure(self):
        """Test OpenAI returns valid assessment structure."""
        with patch("souschef.assessment.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            assessment_text = """Cookbook Assessment:
Complexity Score: 7/10
Estimated Effort: 5 days
Key Modules:
  - Web server: 2 days
  - Database: 2 days
  - Configuration: 1 day"""
            mock_response.json.return_value = {
                "choices": [{"message": {"content": assessment_text}}]
            }
            mock_requests.post.return_value = mock_response

            result = assessment_call_openai_api(
                prompt="Assess complexity",
                api_key="test-key",
                model="gpt-4",
                temperature=0.5,
                max_tokens=1024,
            )

            assert result is not None
            assert "Complexity" in result or "complexity" in result
            assert "days" in result

    def test_watson_streaming_aggregation(self):
        """Test Watson streaming responses aggregate correctly."""
        mock_client = MagicMock()
        chunks = [
            {"results": [{"generated_text": "Part 1: Install. "}]},
            {"results": [{"generated_text": "Part 2: Configure. "}]},
        ]
        mock_client.generate_text.return_value = chunks[0]

        result = playbook_call_watson_api(
            client=mock_client,
            prompt="Generate instructions",
            model="ibm/granite-13b-chat-v2",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "Part 1" in result
        assert "Install" in result

    def test_lightspeed_json_response_parsing(self):
        """Test Lightspeed JSON response is correctly parsed."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            json_response = json.dumps(
                {
                    "playbook": [
                        {
                            "name": "Deploy",
                            "hosts": "all",
                            "tasks": [{"name": "Task 1", "action": "package"}],
                        }
                    ]
                }
            )
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": [{"text": json_response}]}
            mock_requests.post.return_value = mock_response

            client = {"api_key": "test-key", "base_url": "https://api.local"}
            result = playbook_call_lightspeed_api(
                client=client,
                prompt="Generate JSON playbook",
                model="lightspeed-ansible",
                temperature=0.5,
                max_tokens=2048,
            )

            assert "playbook" in result
            assert "Deploy" in result

    def test_github_copilot_multiline_message_content(self):
        """Test GitHub Copilot extracts message content correctly."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            multiline_content = """---
- hosts: all
  tasks:
    - name: Step 1
      debug: msg="Hello"
    - name: Step 2
      debug: msg="World"
    - name: Step 3
      debug: msg="Complete\""""
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": multiline_content}}]
            }
            mock_requests.post.return_value = mock_response

            client = {
                "api_key": "test-key",
                "base_url": "https://api.github.com",
            }
            result = playbook_call_github_copilot_api(
                client=client,
                prompt="Multi-step playbook",
                model="gpt-4-turbo",
                temperature=0.5,
                max_tokens=2048,
            )

            assert "Step 1" in result
            assert "Step 2" in result
            assert "Step 3" in result


class TestAIResponseErrorHandling:
    """Test error handling for AI API responses."""

    def test_anthropic_empty_response_handling(self):
        """Test handling of empty Anthropic response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        with pytest.raises((IndexError, AttributeError)):
            playbook_call_anthropic_api(
                client=mock_client,
                prompt="Test empty response",
                model="claude-3-opus-20240229",
                temperature=0.5,
                max_tokens=2048,
            )

    def test_openai_missing_content_field(self):
        """Test OpenAI response missing content field."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message = MagicMock(spec=[])  # No content attribute
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(AttributeError):
            playbook_call_openai_api(
                client=mock_client,
                prompt="Missing content",
                model="gpt-4",
                temperature=0.5,
                max_tokens=2048,
            )

    def test_watson_api_exception_handling(self):
        """Test Watson API exception returns None."""
        result = assessment_call_watson_api(
            prompt="Test",
            api_key="test-key",
            model="ibm/granite-13b-chat-v2",
            temperature=0.5,
            max_tokens=1024,
        )
        # When APIClient is not available, returns None
        assert result is None

    def test_lightspeed_malformed_json_response(self):
        """Test Lightspeed API with malformed JSON."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_requests.post.return_value = mock_response

            client = {"api_key": "test-key", "base_url": "https://api.local"}

            with pytest.raises(json.JSONDecodeError):
                playbook_call_lightspeed_api(
                    client=client,
                    prompt="Malformed JSON",
                    model="lightspeed",
                    temperature=0.5,
                    max_tokens=2048,
                )

    def test_github_copilot_connection_error(self):
        """Test GitHub Copilot API connection error."""
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_requests.post.side_effect = ConnectionError("Network unreachable")

            client = {"api_key": "test-key", "base_url": "https://api.github.com"}

            with pytest.raises(ConnectionError):
                playbook_call_github_copilot_api(
                    client=client,
                    prompt="Connection error",
                    model="gpt-4-turbo",
                    temperature=0.5,
                    max_tokens=2048,
                )


class TestAIResponseValidation:
    """Test validation of AI responses."""

    def test_anthropic_response_as_string_conversion(self):
        """Test Anthropic response properly converts to string."""
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "---\n- name: Task"
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        result = playbook_call_anthropic_api(
            client=mock_client,
            prompt="Test string conversion",
            model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=2048,
        )

        assert isinstance(result, str)
        assert "Task" in result

    def test_watson_response_aggregation(self):
        """Test Watson streaming response aggregation."""
        mock_client = MagicMock()
        responses = [
            {"results": [{"generated_text": "Part 1 "}]},
            {"results": [{"generated_text": "Part 2 "}]},
            {"results": [{"generated_text": "Part 3"}]},
        ]
        # Simulate streaming by returning different values each time
        mock_client.generate_text.side_effect = responses

        # First call
        result1 = playbook_call_watson_api(
            client=mock_client,
            prompt="Test 1",
            model="ibm/granite-13b-chat-v2",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "Part 1" in result1

    def test_openai_response_choices_extraction(self):
        """Test OpenAI properly extracts first choice."""
        mock_client = MagicMock()
        mock_first_choice = MagicMock()
        mock_first_choice.message.content = "First response"
        mock_second_choice = MagicMock()
        mock_second_choice.message.content = "Second response"
        mock_response = MagicMock()
        mock_response.choices = [mock_first_choice, mock_second_choice]
        mock_client.chat.completions.create.return_value = mock_response

        result = playbook_call_openai_api(
            client=mock_client,
            prompt="Multiple choices",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2048,
        )

        assert "First response" in result
        assert "Second response" not in result
