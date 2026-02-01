"""Tests for AI-enhanced template conversion."""

from unittest.mock import MagicMock, patch

from souschef.converters.template import (
    _enhance_template_with_ai,
    convert_template_with_ai,
)


class TestAIEnhancedTemplateConversion:
    """Test AI-enhanced template conversion functionality."""

    @patch("souschef.converters.template.convert_template_file")
    def test_convert_without_ai_service(self, mock_convert):
        """Test conversion without AI service uses rule-based only."""
        mock_convert.return_value = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }

        result = convert_template_with_ai("/path/to/template.erb", ai_service=None)

        assert result["conversion_method"] == "rule-based"
        assert result["success"] is True
        mock_convert.assert_called_once_with("/path/to/template.erb")

    @patch("souschef.converters.template.convert_template_file")
    @patch("souschef.converters.template._enhance_template_with_ai")
    def test_convert_with_ai_service_success(self, mock_enhance, mock_convert):
        """Test conversion with AI service enhancement."""
        mock_convert.return_value = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }
        mock_enhance.return_value = {
            "success": True,
            "jinja2_template": "{{ variable | default('value') }}",
            "conversion_method": "ai-enhanced",
            "ai_improved": True,
        }

        ai_service = MagicMock()
        result = convert_template_with_ai(
            "/path/to/template.erb", ai_service=ai_service
        )

        assert result["conversion_method"] == "ai-enhanced"
        assert result["ai_improved"] is True
        mock_enhance.assert_called_once()

    @patch("souschef.converters.template.convert_template_file")
    @patch("souschef.converters.template._enhance_template_with_ai")
    def test_convert_with_ai_service_failure(self, mock_enhance, mock_convert):
        """Test AI enhancement failure falls back to rule-based."""
        mock_convert.return_value = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }
        mock_enhance.side_effect = Exception("AI service error")

        ai_service = MagicMock()
        result = convert_template_with_ai(
            "/path/to/template.erb", ai_service=ai_service
        )

        assert result["conversion_method"] == "rule-based-fallback"
        assert "ai_enhancement_error" in result
        assert "AI service error" in result["ai_enhancement_error"]

    @patch("souschef.converters.template.convert_template_file")
    def test_convert_with_failed_conversion(self, mock_convert):
        """Test AI enhancement skipped when rule-based conversion fails."""
        mock_convert.return_value = {
            "success": False,
            "error": "Parse error",
        }

        ai_service = MagicMock()
        result = convert_template_with_ai(
            "/path/to/template.erb", ai_service=ai_service
        )

        assert result["conversion_method"] == "rule-based"
        assert result["success"] is False


class TestEnhanceTemplateWithAI:
    """Test AI enhancement of template conversions."""

    @patch("souschef.converters.template.Path")
    def test_enhance_with_anthropic_api(self, mock_path):
        """Test AI enhancement using Anthropic API."""
        # Mock file reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "<%= @variable %>"
        mock_path_instance = MagicMock()
        mock_path_instance.open.return_value = mock_file
        mock_path.return_value = mock_path_instance

        # Mock Anthropic response
        mock_ai_service = MagicMock()
        mock_content = MagicMock()
        mock_content.text = '{"valid": true, "issues": [], "improvements": ["Add default filter"], "security_concerns": [], "improved_template": "{{ variable | default(\\"value\\") }}"}'
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_ai_service.messages.create.return_value = mock_response

        rule_based_result = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }

        result = _enhance_template_with_ai(
            rule_based_result, "/path/to/template.erb", mock_ai_service
        )

        assert result["ai_validation"]["valid"] is True
        assert "improvements" in result["ai_validation"]
        assert result.get("ai_improved") is True

    @patch("souschef.converters.template.Path")
    def test_enhance_with_openai_api(self, mock_path):
        """Test AI enhancement using OpenAI API."""
        # Mock file reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "<%= @variable %>"
        mock_path_instance = MagicMock()
        mock_path_instance.open.return_value = mock_file
        mock_path.return_value = mock_path_instance

        # Mock OpenAI response
        mock_ai_service = MagicMock()
        mock_ai_service.messages = None  # Not Anthropic
        mock_message = MagicMock()
        mock_message.content = '{"valid": true, "issues": [], "improvements": [], "security_concerns": [], "improved_template": "{{ variable }}"}'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_ai_service.chat.completions.create.return_value = mock_response

        rule_based_result = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }

        result = _enhance_template_with_ai(
            rule_based_result, "/path/to/template.erb", mock_ai_service
        )

        assert result["ai_validation"]["valid"] is True
        assert "improvements" in result["ai_validation"]

    @patch("souschef.converters.template.Path")
    def test_enhance_with_markdown_wrapped_json(self, mock_path):
        """Test AI enhancement with markdown-wrapped JSON response."""
        # Mock file reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "<%= @variable %>"
        mock_path_instance = MagicMock()
        mock_path_instance.open.return_value = mock_file
        mock_path.return_value = mock_path_instance

        mock_ai_service = MagicMock()
        mock_content = MagicMock()
        mock_content.text = '```json\n{"valid": true, "issues": [], "improvements": [], "security_concerns": []}\n```'
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_ai_service.messages.create.return_value = mock_response

        rule_based_result = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }

        result = _enhance_template_with_ai(
            rule_based_result, "/path/to/template.erb", mock_ai_service
        )

        assert result["ai_validation"]["valid"] is True

    @patch("souschef.converters.template.Path")
    def test_enhance_with_invalid_json(self, mock_path):
        """Test AI enhancement with invalid JSON response."""
        # Mock file reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "<%= @variable %>"
        mock_path_instance = MagicMock()
        mock_path_instance.open.return_value = mock_file
        mock_path.return_value = mock_path_instance

        mock_ai_service = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "This is not JSON"
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_ai_service.messages.create.return_value = mock_response

        rule_based_result = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }

        result = _enhance_template_with_ai(
            rule_based_result, "/path/to/template.erb", mock_ai_service
        )

        assert "ai_feedback_raw" in result
        assert result["ai_feedback_raw"] == "This is not JSON"

    @patch("souschef.converters.template.Path")
    def test_enhance_with_unsupported_ai_service(self, mock_path):
        """Test AI enhancement with unsupported AI service."""
        # Mock file reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "<%= @variable %>"
        mock_path_instance = MagicMock()
        mock_path_instance.open.return_value = mock_file
        mock_path.return_value = mock_path_instance

        mock_ai_service = MagicMock()
        # Remove attributes that identify known AI services
        mock_ai_service.messages = None
        mock_ai_service.chat = None

        rule_based_result = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }

        result = _enhance_template_with_ai(
            rule_based_result, "/path/to/template.erb", mock_ai_service
        )

        # Should return original result unchanged
        assert result == rule_based_result

    @patch("souschef.converters.template.Path")
    def test_enhance_with_security_concerns(self, mock_path):
        """Test AI enhancement detecting security concerns."""
        # Mock file reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "<%= @variable %>"
        mock_path_instance = MagicMock()
        mock_path_instance.open.return_value = mock_file
        mock_path.return_value = mock_path_instance

        mock_ai_service = MagicMock()
        mock_content = MagicMock()
        mock_content.text = '{"valid": true, "issues": [], "improvements": [], "security_concerns": ["Unescaped variable could lead to XSS"]}'
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_ai_service.messages.create.return_value = mock_response

        rule_based_result = {
            "success": True,
            "jinja2_template": "{{ variable }}",
        }

        result = _enhance_template_with_ai(
            rule_based_result, "/path/to/template.erb", mock_ai_service
        )

        assert len(result["ai_validation"]["security_concerns"]) > 0
        assert "XSS" in result["ai_validation"]["security_concerns"][0]
