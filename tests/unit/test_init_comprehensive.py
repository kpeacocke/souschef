"""Comprehensive tests for souschef package initialization."""

import souschef


class TestPackageInit:
    """Tests for souschef/__init__.py module."""

    def test_version_is_string(self):
        """Test that version is a string."""
        assert isinstance(souschef.__version__, str)
        assert len(souschef.__version__) > 0

    def test_version_format(self):
        """Test that version follows semantic versioning."""
        version_parts = souschef.__version__.split(".")
        # Should have at least major.minor
        assert len(version_parts) >= 2
        # Major version should be numeric
        assert version_parts[0].isdigit()

    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        assert hasattr(souschef, "__all__")
        # __all__ contains MCP tool exports, not __version__
        assert len(souschef.__all__) > 0
        # Verify key tools are exported
        assert "assess_chef_migration_complexity" in souschef.__all__

    def test_module_docstring(self):
        """Test that module has a docstring."""
        assert souschef.__doc__ is not None
        assert len(souschef.__doc__) > 0

    def test_package_path(self):
        """Test that package __file__ is set correctly."""
        assert hasattr(souschef, "__file__")
        assert "souschef" in souschef.__file__
        assert souschef.__file__.endswith("__init__.py")

    def test_name_attribute(self):
        """Test that __name__ is set correctly."""
        assert souschef.__name__ == "souschef"

    def test_has_server_module(self):
        """Test that server module is importable."""
        from souschef import server

        assert server is not None

    def test_has_cli_module(self):
        """Test that CLI module is importable."""
        from souschef import cli

        assert cli is not None

    def test_has_assessment_module(self):
        """Test that assessment module is importable."""
        from souschef import assessment

        assert assessment is not None

    def test_has_core_package(self):
        """Test that core package is importable."""
        from souschef import core

        assert core is not None

    def test_has_parsers_package(self):
        """Test that parsers package is importable."""
        from souschef import parsers

        assert parsers is not None

    def test_has_converters_package(self):
        """Test that converters package is importable."""
        from souschef import converters

        assert converters is not None
