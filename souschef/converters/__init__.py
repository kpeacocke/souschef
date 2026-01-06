"""Chef to Ansible converters."""

from souschef.converters.resource import convert_resource_to_task

__all__ = ["convert_resource_to_task"]
