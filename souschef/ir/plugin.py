"""
Plugin architecture for extensible source parsers and target generators.

Defines base classes and plugin registry for implementing support for new
source tools (Chef, Puppet, Salt, Bash, PowerShell) and target systems
(Ansible, Terraform, CloudFormation).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .schema import IRGraph, SourceType, TargetType


class SourceParser(ABC):
    """
    Base class for source tool parsers.

    Subclasses implement parsing logic for specific configuration management tools
    like Chef, Puppet, Salt, etc., converting their native formats to IR.
    """

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Return the source tool type this parser handles."""
        pass

    @property
    @abstractmethod
    def supported_versions(self) -> list[str]:
        """Return list of supported versions for the source tool."""
        pass

    @abstractmethod
    def parse(self, source_path: str, **options: Any) -> IRGraph:  # noqa: ARG002
        """
        Parse source configuration into IR.

        Args:
            source_path: Path to source file or directory.
            **options: Parser-specific options.

        Returns:
            IRGraph representing the parsed configuration.

        Raises:
            FileNotFoundError: If source path does not exist.
            ValueError: If source format is invalid.

        """
        pass

    @abstractmethod
    def validate(self, source_path: str) -> dict[str, Any]:  # noqa: ARG002
        """
        Validate source configuration without parsing.

        Args:
            source_path: Path to source file or directory.

        Returns:
            Dictionary with validation results:
            - "valid": bool indicating if source is valid
            - "errors": list of error messages if invalid
            - "warnings": list of warning messages

        """
        pass

    def get_metadata(self) -> dict[str, str]:
        """
        Get metadata about this parser.

        Returns:
            Dictionary with parser metadata.

        """
        return {
            "source_type": self.source_type.value,
            "supported_versions": ", ".join(self.supported_versions),
        }


class TargetGenerator(ABC):
    """
    Base class for target system generators.

    Subclasses implement generation logic for specific target platforms
    like Ansible, Terraform, CloudFormation, etc., converting IR to
    native target formats.
    """

    @property
    @abstractmethod
    def target_type(self) -> TargetType:
        """Return the target system type this generator handles."""
        pass

    @property
    @abstractmethod
    def supported_versions(self) -> list[str]:
        """Return list of supported versions for the target system."""
        pass

    @abstractmethod
    def generate(self, graph: IRGraph, output_path: str, **options: Any) -> None:  # noqa: ARG002
        """
        Generate target configuration from IR.

        Args:
            graph: IRGraph to generate from.
            output_path: Path where generated configuration will be written.
            **options: Generator-specific options.

        Raises:
            ValueError: If IR is not suitable for target.
            IOError: If output cannot be written.

        """
        pass

    @abstractmethod
    def validate_ir(self, graph: IRGraph) -> dict[str, Any]:
        """
        Validate IR for compatibility with this target.

        Args:
            graph: IRGraph to validate.

        Returns:
            Dictionary with validation results:
            - "compatible": bool indicating if IR can be generated
            - "issues": list of compatibility issues
            - "warnings": list of warning messages

        """
        pass

    def get_metadata(self) -> dict[str, str]:
        """
        Get metadata about this generator.

        Returns:
            Dictionary with generator metadata.

        """
        return {
            "target_type": self.target_type.value,
            "supported_versions": ", ".join(self.supported_versions),
        }


class PluginRegistry:
    """
    Registry for source parsers and target generators.

    Manages plugin registration, discovery, and instantiation.
    """

    def __init__(self) -> None:
        """Initialise plugin registry."""
        self._parsers: dict[SourceType, type[SourceParser]] = {}
        self._generators: dict[TargetType, type[TargetGenerator]] = {}

    def register_parser(
        self, source_type: SourceType, parser_class: type[SourceParser]
    ) -> None:
        """
        Register a source parser.

        Args:
            source_type: Source type the parser handles.
            parser_class: Parser class (not instantiated).

        Raises:
            ValueError: If parser for this source type already registered.

        """
        if source_type in self._parsers:
            raise ValueError(f"Parser for {source_type} already registered")
        self._parsers[source_type] = parser_class

    def register_generator(
        self, target_type: TargetType, generator_class: type[TargetGenerator]
    ) -> None:
        """
        Register a target generator.

        Args:
            target_type: Target type the generator handles.
            generator_class: Generator class (not instantiated).

        Raises:
            ValueError: If generator for this target type already registered.

        """
        if target_type in self._generators:
            raise ValueError(f"Generator for {target_type} already registered")
        self._generators[target_type] = generator_class

    def get_parser(self, source_type: SourceType) -> SourceParser | None:
        """
        Get parser for a source type.

        Args:
            source_type: Source type to get parser for.

        Returns:
            Instantiated parser or None if not registered.

        """
        parser_class = self._parsers.get(source_type)
        if parser_class is None:
            return None
        return parser_class()

    def get_generator(self, target_type: TargetType) -> TargetGenerator | None:
        """
        Get generator for a target type.

        Args:
            target_type: Target type to get generator for.

        Returns:
            Instantiated generator or None if not registered.

        """
        generator_class = self._generators.get(target_type)
        if generator_class is None:
            return None
        return generator_class()

    def get_available_parsers(self) -> list[SourceType]:
        """
        Get list of registered source types.

        Returns:
            List of available source types.

        """
        return list(self._parsers.keys())

    def get_available_generators(self) -> list[TargetType]:
        """
        Get list of registered target types.

        Returns:
            List of available target types.

        """
        return list(self._generators.keys())

    def get_registry_info(self) -> dict[str, Any]:
        """
        Get information about registered plugins.

        Returns:
            Dictionary with parser and generator information.

        """
        parsers = []
        for source_type, parser_class in self._parsers.items():
            parser = parser_class()
            parsers.append(
                {
                    "type": source_type.value,
                    "metadata": parser.get_metadata(),
                }
            )

        generators = []
        for target_type, generator_class in self._generators.items():
            generator = generator_class()
            generators.append(
                {
                    "type": target_type.value,
                    "metadata": generator.get_metadata(),
                }
            )

        return {
            "parsers": parsers,
            "generators": generators,
        }


# Global plugin registry instance
_plugin_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """
    Get or create the global plugin registry.

    Returns:
        Global PluginRegistry instance.

    """
    global _plugin_registry
    if _plugin_registry is None:
        _plugin_registry = PluginRegistry()
    return _plugin_registry
