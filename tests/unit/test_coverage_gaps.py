"""
Tests targeting specific uncovered lines across multiple SousChef modules.

These tests cover exception handlers, edge cases, and rarely-exercised code
paths to bring the overall coverage to 100%.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# souschef/__init__.py – OSError from pyproject.toml
# ---------------------------------------------------------------------------


class TestInitGetVersion:
    """Tests for _get_version in souschef/__init__.py."""

    def test_get_version_os_error_returns_unknown(self) -> None:
        """Test that OSError when reading pyproject.toml returns 'unknown'."""
        from pathlib import Path

        import souschef as sc

        # Patch Path.open to raise OSError when called
        original_open = Path.open

        def mock_open(self_path, *args, **kwargs):
            if "pyproject.toml" in str(self_path):
                raise OSError("disk error")
            return original_open(self_path, *args, **kwargs)

        with patch.object(Path, "open", mock_open):
            result = sc._get_version()
        assert result == "unknown"


# ---------------------------------------------------------------------------
# souschef/cli_registry.py – uncovered lines 60-61, 74-76, 89-91, 104, 114
# ---------------------------------------------------------------------------


class TestCLIFeatureRegistry:
    """Tests for CLIFeatureRegistry."""

    def _make_registry(self):
        """Create a fresh registry instance for each test."""
        from souschef.cli_registry import CLIFeatureRegistry

        return CLIFeatureRegistry()

    def test_load_all_raises_runtime_error_on_loader_failure(self) -> None:
        """load_all raises RuntimeError when a loader raises an exception."""
        registry = self._make_registry()

        def bad_loader(cli: Any) -> None:
            raise RuntimeError("loader exploded")

        registry.register("bad", bad_loader, enabled=True)

        with pytest.raises(RuntimeError, match="Failed to load CLI group 'bad'"):
            registry.load_all(object())

    def test_enable_raises_key_error_for_unknown_group(self) -> None:
        """enable() raises KeyError for a group that has not been registered."""
        registry = self._make_registry()
        with pytest.raises(KeyError, match="Unknown CLI group"):
            registry.enable("nonexistent")

    def test_disable_raises_key_error_for_unknown_group(self) -> None:
        """disable() raises KeyError for a group that has not been registered."""
        registry = self._make_registry()
        with pytest.raises(KeyError, match="Unknown CLI group"):
            registry.disable("nonexistent")

    def test_is_enabled_returns_false_for_unknown_group(self) -> None:
        """is_enabled() returns False for an unregistered group."""
        registry = self._make_registry()
        assert registry.is_enabled("unknown") is False

    def test_list_groups_returns_copy(self) -> None:
        """list_groups() returns a copy of the internal groups dict."""
        registry = self._make_registry()
        registry.register("alpha", lambda cli: None, enabled=True, description="desc")
        groups = registry.list_groups()
        assert "alpha" in groups
        # Mutating the returned dict must not affect the registry
        del groups["alpha"]
        assert "alpha" in registry.list_groups()

    def test_enable_and_disable_group(self) -> None:
        """Enable and disable change the enabled state of a group."""
        registry = self._make_registry()
        registry.register("grp", lambda cli: None, enabled=False)
        assert registry.is_enabled("grp") is False
        registry.enable("grp")
        assert registry.is_enabled("grp") is True
        registry.disable("grp")
        assert registry.is_enabled("grp") is False


# ---------------------------------------------------------------------------
# souschef/storage/config.py – uncovered lines 43, 78, 148
# ---------------------------------------------------------------------------


class TestStorageConfig:
    """Tests for storage configuration helpers."""

    def test_normalise_backend_empty_string_returns_default(self) -> None:
        """_normalise_backend returns the default when value is empty."""
        from souschef.storage.config import _normalise_backend

        result = _normalise_backend("", aliases={}, default="sqlite")
        assert result == "sqlite"

    def test_load_database_settings_unknown_backend_falls_back_to_sqlite(
        self,
    ) -> None:
        """Unknown DB backend resets to 'sqlite'."""
        from souschef.storage.config import load_database_settings

        settings = load_database_settings(env={"SOUSCHEF_DB_BACKEND": "oracle"})
        assert settings.backend == "sqlite"

    def test_load_blob_settings_unknown_backend_falls_back_to_local(self) -> None:
        """Unknown blob storage backend resets to 'local'."""
        from souschef.storage.config import load_blob_settings

        settings = load_blob_settings(env={"SOUSCHEF_STORAGE_BACKEND": "gcs"})
        assert settings.backend == "local"


# ---------------------------------------------------------------------------
# souschef/ir/versioning.py – uncovered lines 93, 117, 159, 169, 192-196
# ---------------------------------------------------------------------------


class TestIRVersioning:
    """Tests for IR versioning module."""

    def test_irversion_eq_returns_not_implemented_for_non_irversion(self) -> None:
        """IRVersion.__eq__ returns NotImplemented for non-IRVersion objects."""
        from souschef.ir.versioning import IRVersion

        v = IRVersion(1, 0, 0)
        result = v.__eq__("1.0.0")
        assert result is NotImplemented

    def test_schema_migration_migrate_applies_transformation(self) -> None:
        """SchemaMigration.migrate() applies the transformation function."""
        from souschef.ir.versioning import IRVersion, SchemaMigration

        v1 = IRVersion(1, 0, 0)
        v2 = IRVersion(2, 0, 0)
        migration = SchemaMigration(
            from_version=v1,
            to_version=v2,
            transformation=lambda d: {**d, "migrated": True},
        )
        result = migration.migrate({"key": "value"})
        assert result == {"key": "value", "migrated": True}

    def test_get_migrations_path_same_version_returns_empty(self) -> None:
        """get_migrations_path returns [] when from == to."""
        from souschef.ir.versioning import IRVersion, IRVersionManager

        manager = IRVersionManager()
        v1 = IRVersion(1, 0, 0)
        assert manager.get_migrations_path(v1, v1) == []

    def test_get_migrations_path_raises_value_error_when_no_path(self) -> None:
        """get_migrations_path raises ValueError when no migration exists."""
        from souschef.ir.versioning import IRVersion, IRVersionManager

        manager = IRVersionManager()
        v1 = IRVersion(1, 0, 0)
        v2 = IRVersion(2, 0, 0)
        with pytest.raises(ValueError, match="No migration path"):
            manager.get_migrations_path(v1, v2)

    def test_migrate_data_applies_registered_migration(self) -> None:
        """migrate_data applies a registered schema migration."""
        from souschef.ir.versioning import IRVersion, IRVersionManager, SchemaMigration

        manager = IRVersionManager()
        v1 = IRVersion(1, 0, 0)
        v2 = IRVersion(2, 0, 0)
        migration = SchemaMigration(
            from_version=v1,
            to_version=v2,
            transformation=lambda d: {**d, "version": "2.0"},
        )
        manager.register_migration(migration)
        result = manager.migrate_data({"x": 1}, v1, v2)
        assert result == {"x": 1, "version": "2.0"}


# ---------------------------------------------------------------------------
# souschef/ir/plugin.py – uncovered lines 201, 233
# ---------------------------------------------------------------------------


class TestIRPlugin:
    """Tests for IR plugin registry."""

    def _make_concrete_generator(self, target_type_val):
        """Create a minimal concrete TargetGenerator subclass."""
        from souschef.ir.plugin import TargetGenerator
        from souschef.ir.schema import IRGraph

        class ConcreteGenerator(TargetGenerator):
            @property
            def target_type(self):
                return target_type_val

            @property
            def supported_versions(self):
                return ["1.0"]

            def generate(self, graph: IRGraph, output_path: str, **options) -> None:
                # Empty implementation for testing - concrete class needed to instantiate abstract IRGenerator
                pass

            def validate_ir(self, graph: IRGraph) -> dict:
                return {}

        return ConcreteGenerator

    def test_register_generator_duplicate_raises_value_error(self) -> None:
        """Registering the same TargetType twice raises ValueError."""
        from souschef.ir.plugin import PluginRegistry
        from souschef.ir.schema import TargetType

        registry = PluginRegistry()
        gen_class = self._make_concrete_generator(TargetType.ANSIBLE)
        registry.register_generator(TargetType.ANSIBLE, gen_class)
        with pytest.raises(ValueError, match="already registered"):
            registry.register_generator(TargetType.ANSIBLE, gen_class)

    def test_get_generator_unregistered_returns_none(self) -> None:
        """get_generator returns None for an unregistered TargetType."""
        from souschef.ir.plugin import PluginRegistry
        from souschef.ir.schema import TargetType

        registry = PluginRegistry()
        result = registry.get_generator(TargetType.ANSIBLE)
        assert result is None


# ---------------------------------------------------------------------------
# souschef/core/error_handling.py – uncovered lines 52, 367-370, 421-423
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for core error handling utilities."""

    def test_format_message_includes_line_number(self) -> None:
        """format_message includes line number when context has line_number set."""
        from souschef.core.error_handling import (
            EnhancedErrorMessage,
            ErrorContext,
        )

        context = ErrorContext(
            error_type="syntax",
            location="recipe.rb",
            line_number=42,
        )
        msg = EnhancedErrorMessage(
            title="Parse Error",
            description="Something went wrong",
            context=context,
            suggestions=["Fix it"],
        )
        formatted = msg.format_message()
        assert "Line 42" in formatted

    def test_validate_collection_name_non_string_returns_false(self) -> None:
        """validate_collection_name returns (False, msg) for non-string input."""
        from souschef.core.error_handling import validate_collection_name

        valid, msg = validate_collection_name(123)  # type: ignore[arg-type]
        assert valid is False
        assert msg is not None

    def test_validate_hostname_valid_ipv4_returns_true(self) -> None:
        """validate_hostname returns (True, None) for a valid IPv4 address."""
        from souschef.core.error_handling import validate_hostname

        valid, msg = validate_hostname("192.0.2.1")
        assert valid is True
        assert msg is None


# ---------------------------------------------------------------------------
# souschef/ci/jenkins_pipeline.py – uncovered line 54
# ---------------------------------------------------------------------------


class TestJenkinsPipeline:
    """Tests for Jenkins pipeline generator."""

    def test_create_lint_stage_returns_none_when_no_lint_tools(self) -> None:
        """_create_lint_stage returns None when no recognised lint tools exist."""
        from souschef.ci.jenkins_pipeline import _create_lint_stage

        # Empty ci_patterns → no lint steps → should return None
        result = _create_lint_stage({})
        assert result is None


# ---------------------------------------------------------------------------
# souschef/converters/advanced_resource.py – uncovered line 102
# ---------------------------------------------------------------------------


class TestAdvancedResource:
    """Tests for advanced resource converter."""

    def test_convert_guard_to_ansible_unknown_type_returns_empty(self) -> None:
        """convert_guard_to_ansible_when returns '' for an unknown guard_type."""
        from souschef.converters.advanced_resource import convert_guard_to_ansible_when

        result = convert_guard_to_ansible_when("unknown_type", "some command")
        assert result == ""


# ---------------------------------------------------------------------------
# souschef/converters/playbook_optimizer.py – uncovered lines 93, 155, 202
# ---------------------------------------------------------------------------


class TestPlaybookOptimizer:
    """Tests for playbook optimiser module."""

    def test_extract_module_name_returns_none_for_unknown_task(self) -> None:
        """_extract_module_name returns None when no known module key is present."""
        from souschef.converters.playbook_optimizer import _extract_module_name

        result = _extract_module_name({"name": "some task"})
        assert result is None

    def test_create_loop_consolidated_task_empty_list_returns_empty_dict(
        self,
    ) -> None:
        """_create_loop_consolidated_task returns {} for an empty tasks list."""
        from souschef.converters.playbook_optimizer import (
            _create_loop_consolidated_task,
        )

        result = _create_loop_consolidated_task([], None)
        assert result == {}

    def test_non_consolidatable_tasks_break_loop(self) -> None:
        """Optimiser skips consolidation when tasks use different modules."""
        from souschef.converters.playbook_optimizer import optimize_task_loops

        # Mix of different module types → should not consolidate
        tasks = [
            {"name": "install pkg", "ansible.builtin.package": {"name": "curl"}},
            {"name": "copy file", "ansible.builtin.copy": {"src": "/a", "dest": "/b"}},
        ]
        result = optimize_task_loops(tasks)
        # Should not throw; individual tasks stay separate
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# souschef/converters/handler_generation.py – uncovered line 56
# ---------------------------------------------------------------------------


class TestHandlerGeneration:
    """Tests for handler generation utilities."""

    def test_extract_handler_callbacks_exception_method(self) -> None:
        """_extract_methods_and_callbacks returns 'converge_failed' for exception method."""
        from souschef.converters.handler_generation import (
            _extract_methods_and_callbacks,
        )

        handler_content = """
  def exception(message)
    Chef::Log.error(message)
  end
"""
        _methods, callbacks = _extract_methods_and_callbacks(handler_content)
        assert "converge_failed" in callbacks


# ---------------------------------------------------------------------------
# souschef/converters/custom_module_generator.py – uncovered line 41
# ---------------------------------------------------------------------------


class TestCustomModuleGenerator:
    """Tests for custom module generator."""

    def test_analyse_resource_complexity_increments_on_provides(self) -> None:
        """analyse_resource_complexity increments score for 'provides :name'."""
        from souschef.converters.custom_module_generator import (
            analyse_resource_complexity,
        )

        resource_body = """
property :name, String
provides :my_custom_resource

action :create do
  file '/tmp/foo' do
    content new_resource.name
  end
end
"""  # NOSONAR - Test fixture containing Chef Ruby code with /tmp path
        result = analyse_resource_complexity(resource_body)
        # The 'provides' directive adds 2 to complexity_score
        assert result["complexity_score"] >= 2


# ---------------------------------------------------------------------------
# souschef/filesystem/operations.py – uncovered lines 40, 101, 139
# ---------------------------------------------------------------------------


class TestFilesystemOperations:
    """Tests for filesystem operations."""

    def test_list_directory_returns_error_on_value_error(self, tmp_path: Path) -> None:
        """list_directory returns an error string when ValueError is raised."""
        from souschef.filesystem.operations import list_directory

        with patch(
            "souschef.filesystem.operations._get_workspace_root",
            side_effect=ValueError("bad path"),
        ):
            result = list_directory(str(tmp_path))

        assert isinstance(result, str)
        assert "Error" in result

    def test_create_tar_gz_archive_raises_for_nonexistent_source(
        self, tmp_path: Path
    ) -> None:
        """create_tar_gz_archive raises ValueError for a non-existent source dir."""
        from souschef.filesystem.operations import create_tar_gz_archive

        nonexistent = str(tmp_path / "missing_dir")
        output = str(tmp_path / "output.tar.gz")

        with (
            patch(
                "souschef.filesystem.operations._get_workspace_root",
                return_value=tmp_path,
            ),
            pytest.raises(ValueError, match="Source directory does not exist"),
        ):
            create_tar_gz_archive(nonexistent, output)

    def test_extract_tar_gz_archive_raises_for_nonexistent_archive(
        self, tmp_path: Path
    ) -> None:
        """extract_tar_gz_archive raises ValueError for a non-existent archive."""
        from souschef.filesystem.operations import extract_tar_gz_archive

        fake_archive = str(tmp_path / "missing.tar.gz")
        output_dir = str(tmp_path / "out")

        with (
            patch(
                "souschef.filesystem.operations._get_workspace_root",
                return_value=tmp_path,
            ),
            pytest.raises(ValueError, match="Archive does not exist"),
        ):
            extract_tar_gz_archive(fake_archive, output_dir)


# ---------------------------------------------------------------------------
# souschef/core/path_utils.py – uncovered lines 28, 30, 144
# ---------------------------------------------------------------------------


class TestPathUtils:
    """Tests for core path utility functions."""

    def test_get_workspace_root_raises_for_nonexistent_path(self) -> None:
        """_get_workspace_root raises ValueError when env var path does not exist."""
        from souschef.core.path_utils import _get_workspace_root

        with (
            patch.dict(
                os.environ, {"SOUSCHEF_WORKSPACE_ROOT": "/nonexistent_xyz_path"}
            ),
            pytest.raises(ValueError, match="Workspace root does not exist"),
        ):
            _get_workspace_root()

    def test_get_workspace_root_raises_for_file_path(self, tmp_path: Path) -> None:
        """_get_workspace_root raises ValueError when env var points to a file."""
        from souschef.core.path_utils import _get_workspace_root

        tmp_file = tmp_path / "not_a_dir.txt"
        tmp_file.write_text("hello")

        with (
            patch.dict(os.environ, {"SOUSCHEF_WORKSPACE_ROOT": str(tmp_file)}),
            pytest.raises(ValueError, match="Workspace root is not a directory"),
        ):
            _get_workspace_root()

    def test_safe_parts_raises_for_combined_absolute_result(self) -> None:
        """_validate_relative_parts raises ValueError when a part contains '..'."""
        from souschef.core.path_utils import _validate_relative_parts

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _validate_relative_parts(("../evil",))


# ---------------------------------------------------------------------------
# souschef/core/url_validation.py – uncovered lines 41, 106-124, 165, 267
# ---------------------------------------------------------------------------


class TestUrlValidation:
    """Tests for URL validation utilities."""

    def test_matches_allowlist_wildcard_entry(self) -> None:
        """_matches_allowlist handles wildcard entries like '*.example.com'."""
        from souschef.core.url_validation import _matches_allowlist

        assert _matches_allowlist("api.example.com", ["*.example.com"]) is True
        assert _matches_allowlist("other.net", ["*.example.com"]) is False

    def test_is_private_host_empty_addrinfo(self) -> None:
        """_is_private_hostname returns False when DNS resolves to no addresses."""
        from souschef.core.url_validation import _is_private_hostname

        with patch("socket.getaddrinfo", return_value=[]):
            assert _is_private_hostname("no-result.test-domain.xyz") is False

    def test_is_private_host_private_ip(self) -> None:
        """_is_private_hostname returns True for a private IP address."""
        from souschef.core.url_validation import _is_private_hostname

        fake_addr = [(2, 1, 6, "", ("198.51.100.51", 0))]  # RFC 5737 documentation IP
        with patch("socket.getaddrinfo", return_value=fake_addr):
            assert _is_private_hostname("private.internal-company.xyz") is True

    def test_is_private_host_public_ip(self) -> None:
        """_is_private_hostname returns False for a public IP address."""
        from souschef.core.url_validation import _is_private_hostname

        fake_addr = [
            (2, 1, 6, "", ("1.1.1.1", 0))  # NOSONAR - Test fixture simulating public IP
        ]
        with patch("socket.getaddrinfo", return_value=fake_addr):
            assert _is_private_hostname("public.company-cloud.xyz") is False

    def test_validate_url_raises_when_base_url_empty(self) -> None:
        """Validation raises ValueError when base_url is empty and no default."""
        from souschef.core.url_validation import validate_user_provided_url

        with pytest.raises(ValueError, match="Base URL"):
            validate_user_provided_url("", default_url=None)

    def test_validate_url_raises_when_no_hostname(self) -> None:
        """Validation raises ValueError when URL has no hostname."""
        from souschef.core.url_validation import validate_user_provided_url

        with pytest.raises(ValueError):
            validate_user_provided_url("https://")


# ---------------------------------------------------------------------------
# souschef/core/http_client.py – uncovered lines 104, 159, 166, 172,
#                                257, 272-273, 320-321, 378-379
# ---------------------------------------------------------------------------


class TestHTTPClient:
    """Tests for the HTTP client module."""

    def test_get_error_hint_unknown_status_returns_generic_message(self) -> None:
        """HTTPError._get_suggestion returns the generic message for unknown status codes."""
        from souschef.core.http_client import HTTPError

        hint = HTTPError._get_suggestion(418)
        assert "API documentation" in hint

    def test_http_client_rejects_plain_http_url(self) -> None:
        """HTTPClient raises SousChefError for an insecure http:// base URL."""
        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        with pytest.raises(SousChefError):
            HTTPClient(
                base_url="http://example.com"  # NOSONAR - Testing HTTP rejection
            )

    def test_http_client_rejects_invalid_max_retries(self) -> None:
        """HTTPClient raises SousChefError for max_retries > 10."""
        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        with pytest.raises(SousChefError):
            HTTPClient(base_url="https://example.com", max_retries=11)

    def test_http_client_rejects_invalid_backoff_factor(self) -> None:
        """HTTPClient raises SousChefError for backoff_factor < 0.1."""
        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        with pytest.raises(SousChefError):
            HTTPClient(base_url="https://example.com", backoff_factor=0.05)

    def test_handle_request_error_raises_for_http_error_without_response(
        self,
    ) -> None:
        """_handle_request_error raises SousChefError for HTTPError with no response."""
        from requests.exceptions import HTTPError as RequestsHTTPError

        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        client = HTTPClient(base_url="https://example.com")
        error = RequestsHTTPError("HTTP Error")
        error.response = None  # type: ignore[attr-defined]

        with pytest.raises(SousChefError):
            client._handle_request_error(error, "https://example.com/api", 30, None)

    def test_handle_request_error_raises_for_request_exception(self) -> None:
        """_handle_request_error raises SousChefError for generic RequestException."""
        from requests.exceptions import RequestException

        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        client = HTTPClient(base_url="https://example.com")
        error = RequestException("generic error")

        with pytest.raises(SousChefError):
            client._handle_request_error(error, "https://example.com/api", 30, None)

    def test_post_raises_when_response_is_not_dict(self) -> None:
        """post() raises SousChefError when the JSON response is not a dict."""
        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        client = HTTPClient(base_url="https://example.com")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["not", "a", "dict"]
        mock_response.headers = {}

        with (
            patch.object(client.session, "post", return_value=mock_response),
            pytest.raises(SousChefError, match="Expected JSON object"),
        ):
            client.post("/api", json_data={"key": "val"})

    def test_get_raises_when_response_is_not_dict(self) -> None:
        """get() raises SousChefError when the JSON response is not a dict."""
        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        client = HTTPClient(base_url="https://example.com")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [1, 2, 3]
        mock_response.headers = {}

        with (
            patch.object(client.session, "get", return_value=mock_response),
            pytest.raises(SousChefError, match="Expected JSON object"),
        ):
            client.get("/api")
