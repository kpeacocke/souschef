"""Chef ERB template to Jinja2 converter."""

from pathlib import Path
from typing import Any

from souschef.parsers.template import (
    _convert_erb_to_jinja2,
    _extract_template_variables,
)


def convert_template_file(erb_path: str) -> dict:
    """
    Convert an ERB template file to Jinja2 format.

    Args:
        erb_path: Path to the ERB template file.

    Returns:
        Dictionary containing:
            - success: bool, whether conversion succeeded
            - original_file: str, path to original ERB file
            - jinja2_file: str, suggested path for .j2 file
            - jinja2_content: str, converted Jinja2 template content
            - variables: list, variables found in template
            - error: str (optional), error message if conversion failed

    """
    try:
        file_path = Path(erb_path).resolve()

        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {erb_path}",
                "original_file": erb_path,
            }

        if not file_path.is_file():
            return {
                "success": False,
                "error": f"Path is not a file: {erb_path}",
                "original_file": erb_path,
            }

        # Read ERB template
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": f"Unable to decode {erb_path} as UTF-8 text",
                "original_file": str(file_path),
            }

        # Extract variables
        variables = _extract_template_variables(content)

        # Convert ERB to Jinja2
        jinja2_content = _convert_erb_to_jinja2(content)

        # Determine output file name
        jinja2_file = str(file_path).replace(".erb", ".j2")

        return {
            "success": True,
            "original_file": str(file_path),
            "jinja2_file": jinja2_file,
            "jinja2_content": jinja2_content,
            "variables": sorted(variables),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Conversion failed: {e}",
            "original_file": erb_path,
        }


def convert_cookbook_templates(cookbook_path: str) -> dict:
    """
    Convert all ERB templates in a cookbook to Jinja2.

    Args:
        cookbook_path: Path to the cookbook directory.

    Returns:
        Dictionary containing:
            - success: bool, whether all conversions succeeded
            - templates_converted: int, number of templates successfully converted
            - templates_failed: int, number of templates that failed conversion
            - results: list of dict, individual template conversion results
            - error: str (optional), error message if cookbook not found

    """
    try:
        cookbook_dir = Path(cookbook_path).resolve()

        if not cookbook_dir.exists():
            return {
                "success": False,
                "error": f"Cookbook directory not found: {cookbook_path}",
                "templates_converted": 0,
                "templates_failed": 0,
                "results": [],
            }

        # Find all .erb files in the cookbook
        erb_files = list(cookbook_dir.glob("**/*.erb"))

        if not erb_files:
            return {
                "success": True,
                "templates_converted": 0,
                "templates_failed": 0,
                "results": [],
                "message": "No ERB templates found in cookbook",
            }

        results = []
        templates_converted = 0
        templates_failed = 0

        for erb_file in erb_files:
            result = convert_template_file(str(erb_file))
            results.append(result)

            if result["success"]:
                templates_converted += 1
            else:
                templates_failed += 1

        return {
            "success": templates_failed == 0,
            "templates_converted": templates_converted,
            "templates_failed": templates_failed,
            "results": results,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to convert cookbook templates: {e}",
            "templates_converted": 0,
            "templates_failed": 0,
            "results": [],
        }


def convert_template_with_ai(erb_path: str, ai_service=None) -> dict:
    """
    Convert an ERB template to Jinja2 using AI assistance for complex conversions.

    This function first attempts rule-based conversion, then optionally uses AI
    for validation or complex Ruby logic that can't be automatically converted.

    Args:
        erb_path: Path to the ERB template file.
        ai_service: Optional AI service instance for complex conversions.

    Returns:
        Dictionary with conversion results (same format as convert_template_file).

    """
    # Start with rule-based conversion
    result = convert_template_file(erb_path)

    # Add conversion method metadata
    result["conversion_method"] = "rule-based"

    # Use AI service to validate and improve complex conversions
    if ai_service is not None and result.get("success"):
        try:
            # Enhanced AI validation for template conversion
            result = _enhance_template_with_ai(result, erb_path, ai_service)
            result["conversion_method"] = "ai-enhanced"
        except Exception as e:
            # If AI enhancement fails, return the rule-based result
            result["ai_enhancement_error"] = str(e)
            result["conversion_method"] = "rule-based-fallback"

    return result


def _enhance_template_with_ai(
    rule_based_result: dict, erb_path: str, ai_service: Any
) -> dict:
    """
    Enhance rule-based template conversion using AI validation.

    Args:
        rule_based_result: Result from rule-based conversion
        erb_path: Path to original ERB template
        ai_service: AI service instance (Anthropic, OpenAI, etc.)

    Returns:
        Enhanced conversion result with AI improvements

    """
    # Read original ERB content
    file_path = Path(erb_path)
    with file_path.open(encoding="utf-8") as f:
        erb_content = f.read()

    jinja2_content = rule_based_result.get("jinja2_template", "")

    # Create validation prompt
    prompt = f"""You are an expert in both Chef ERB templates and \
Ansible Jinja2 templates.

Review the following ERB to Jinja2 conversion and provide feedback:

**Original ERB Template:**
```erb
{erb_content}
```

**Converted Jinja2 Template:**
```jinja2
{jinja2_content}
```

Analyse the conversion and provide:
1. Validation: Is the conversion accurate and complete?
2. Issues: Any Ruby logic that wasn't properly converted?
3. Improvements: Suggested improvements for better Jinja2 syntax
4. Security: Any security concerns in the template

Respond in JSON format:
{{
    "valid": true/false,
    "issues": ["list of issues"],
    "improvements": ["list of improvements"],
    "security_concerns": ["list of security concerns"],
    "improved_template": "improved Jinja2 template if applicable"
}}
"""

    # Call AI service based on type
    response_text = ""

    if hasattr(ai_service, "messages") and hasattr(ai_service.messages, "create"):
        # Anthropic API
        response = ai_service.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text
    elif hasattr(ai_service, "chat") and hasattr(ai_service.chat, "completions"):
        # OpenAI API
        response = ai_service.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        response_text = response.choices[0].message.content
    else:
        # Unsupported AI service
        return rule_based_result

    # Parse AI response
    import json
    import re

    # Extract JSON from response (may be wrapped in markdown code blocks)
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)

    try:
        ai_feedback = json.loads(response_text)

        # Enhance result with AI feedback
        enhanced_result = rule_based_result.copy()
        enhanced_result["ai_validation"] = {
            "valid": ai_feedback.get("valid", True),
            "issues": ai_feedback.get("issues", []),
            "improvements": ai_feedback.get("improvements", []),
            "security_concerns": ai_feedback.get("security_concerns", []),
        }

        # Use improved template if provided and valid
        if ai_feedback.get("improved_template") and ai_feedback.get("valid"):
            enhanced_result["jinja2_template"] = ai_feedback["improved_template"]
            enhanced_result["ai_improved"] = True

        return enhanced_result

    except json.JSONDecodeError:
        # If AI response isn't valid JSON, add raw feedback
        rule_based_result["ai_feedback_raw"] = response_text
        return rule_based_result
