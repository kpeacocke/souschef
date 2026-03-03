"""Comprehensive tests for souschef package initialization."""

import builtins
import importlib
import sys
import types
from pathlib import Path

import pytest

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

    def test_tomli_fallback_when_tomllib_missing(self, monkeypatch):
        """Test tomli fallback is used when tomllib is unavailable."""
        real_import = builtins.__import__
        fake_tomli = types.ModuleType("tomli")

        def fake_load(_f):
            return {"tool": {"poetry": {"version": "0.0.0"}}}

        fake_tomli.load = fake_load
        monkeypatch.setitem(sys.modules, "tomli", fake_tomli)

        def guarded_import(name, *args, **kwargs):
            if name == "tomllib":
                raise ModuleNotFoundError("tomllib missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", guarded_import)

        try:
            reloaded = importlib.reload(souschef)
            assert reloaded.__version__ == "0.0.0"
        finally:
            monkeypatch.setattr(builtins, "__import__", real_import)
            sys.modules.pop("tomli", None)
            importlib.reload(souschef)

    def test_get_version_handles_oserror(self, monkeypatch):
        """Test version lookup returns unknown on OSError."""
        original_open = Path.open

        def raise_oserror(*_args, **_kwargs):
            raise OSError("boom")

        monkeypatch.setattr(Path, "open", raise_oserror)

        try:
            reloaded = importlib.reload(souschef)
            assert reloaded.__version__ == "unknown"
        finally:
            monkeypatch.setattr(Path, "open", original_open)
            importlib.reload(souschef)

    def test_server_import_error_uses_placeholder(self, monkeypatch):
        """Test server import error creates placeholder function."""
        real_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "souschef.server":
                raise ImportError("server missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", guarded_import)

        try:
            reloaded = importlib.reload(souschef)
            with pytest.raises(NotImplementedError, match="MCP server not available"):
                reloaded.analyse_chef_search_patterns()
        finally:
            monkeypatch.setattr(builtins, "__import__", real_import)
            importlib.reload(souschef)
