"""Unit tests for validation helpers in souschef.orchestrators.chef."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


@patch("souschef.orchestrators.chef.assessment")
def test_orchestrate_validate_conversion_delegates(
    mock_assessment: MagicMock,
) -> None:
    """Validation orchestration delegates to the assessment layer."""
    mock_assessment.validate_conversion.return_value = '{"summary": {}}'

    from souschef.orchestrators.chef import orchestrate_validate_conversion

    result = orchestrate_validate_conversion(
        "recipe",
        "- hosts: all\n",
        output_format="json",
    )

    assert result == '{"summary": {}}'
    mock_assessment.validate_conversion.assert_called_once_with(
        "recipe",
        "- hosts: all\n",
        output_format="json",
    )
