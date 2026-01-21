"""Chef ERB template to Jinja2 converter."""

from pathlib import Path

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

    # Future enhancement: Use AI service to validate/improve complex conversions
    if ai_service is not None:
        # AI validation/improvement logic deferred to future enhancement
        # when AI integration becomes more critical to the template conversion process
        pass

    return result
