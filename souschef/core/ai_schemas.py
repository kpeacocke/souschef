"""
Pydantic schemas for AI structured outputs.

This module defines schemas for structured AI responses, enabling
reliable parsing of AI-generated content with type safety.
"""

from typing import Any

from pydantic import BaseModel, Field


class AnsibleTask(BaseModel):
    """Schema for a single Ansible task."""

    name: str = Field(..., description="Human-readable task name")
    module: str = Field(
        ..., description="Ansible module name (e.g., 'package', 'service')"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Module parameters as key-value pairs"
    )
    when: str | None = Field(
        None, description="Conditional expression for task execution"
    )
    notify: list[str] | None = Field(
        None, description="List of handlers to notify on change"
    )
    tags: list[str] | None = Field(
        None, description="List of tags for task categorization"
    )
    become: bool | None = Field(None, description="Whether to use privilege escalation")
    register: str | None = Field(None, description="Variable name to store task result")


class AnsibleHandler(BaseModel):
    """Schema for an Ansible handler."""

    name: str = Field(..., description="Handler name")
    module: str = Field(..., description="Ansible module name")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Module parameters"
    )


class AnsiblePlaybook(BaseModel):
    """Schema for a complete Ansible playbook."""

    name: str = Field(..., description="Playbook name")
    hosts: str = Field(default="all", description="Target hosts pattern")
    become: bool | None = Field(None, description="Whether to use privilege escalation")
    vars: dict[str, Any] | None = Field(None, description="Playbook variables")
    tasks: list[AnsibleTask] = Field(default_factory=list, description="List of tasks")
    handlers: list[AnsibleHandler] | None = Field(None, description="List of handlers")


class ConversionResult(BaseModel):
    """Schema for AI conversion results."""

    playbook: AnsiblePlaybook = Field(..., description="Generated Ansible playbook")
    notes: list[str] | None = Field(
        None,
        description="Conversion notes, warnings, or manual steps required",
    )
    confidence: float | None = Field(
        None,
        description="Confidence score (0.0-1.0) for the conversion accuracy",
        ge=0.0,
        le=1.0,
    )


class TemplateConversion(BaseModel):
    """Schema for template conversion results."""

    jinja2_template: str = Field(..., description="Converted Jinja2 template content")
    variable_mappings: dict[str, str] | None = Field(
        None,
        description="Mapping of Chef variables to Ansible variables",
    )
    notes: list[str] | None = Field(None, description="Conversion notes or warnings")
