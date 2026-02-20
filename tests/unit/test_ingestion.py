"""Tests for Chef Server ingestion helpers."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from souschef.ingestion import (
    CookbookSpec,
    fetch_cookbooks_from_chef_server,
    import_offline_bundle,
)


class FakeChefClient:
    """Fake Chef Server client for ingestion tests."""

    def __init__(self, fail_downloads: bool = False) -> None:
        self._versions = {
            "nginx": ["1.0.0", "1.1.0", "2.0.0"],
            "apt": ["2.0.0", "2.1.0"],
            "mysql": ["3.0.0"],
        }
        self._fail_downloads = fail_downloads

    def list_cookbook_versions(self, cookbook_name: str) -> list[str]:
        return self._versions.get(cookbook_name, [])

    def get_cookbook_version(self, cookbook_name: str, version: str) -> dict[str, Any]:
        if cookbook_name == "nginx":
            return {
                "metadata": {"dependencies": {"apt": ">= 2.0.0", "mysql": "~> 3.0"}},
                "recipes": [
                    {
                        "path": "recipes/default.rb",
                        "url": "https://chef.example.com/cookbooks/nginx/recipes/default.rb",
                    }
                ],
                "files": [
                    {
                        "path": "files/config.conf",
                        "url": "https://chef.example.com/cookbooks/nginx/files/config.conf",
                    }
                ],
                "templates": [
                    {
                        "path": "templates/site.erb",
                        "url": "https://chef.example.com/cookbooks/nginx/templates/site.erb",
                    }
                ],
            }
        if cookbook_name == "apt":
            return {
                "dependencies": {"mysql": "== 3.0.0"},
                "recipes": [
                    {
                        "path": "recipes/default.rb",
                        "url": "https://chef.example.com/cookbooks/apt/recipes/default.rb",
                    }
                ],
            }
        return {
            "metadata": {"dependencies": {}},
            "recipes": [
                {
                    "path": "recipes/default.rb",
                    "url": f"https://chef.example.com/cookbooks/{cookbook_name}/recipes/default.rb",
                }
            ],
        }

    def download_url(self, url: str) -> bytes:
        if self._fail_downloads and "nginx" in url:
            raise RuntimeError("Download failed")
        return b"file-content"


def test_fetch_cookbooks_from_chef_server_downloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure cookbook downloads include dependencies and manifest."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    output_dir = tmp_path / "downloads"

    with patch(
        "souschef.ingestion.build_chef_server_client", return_value=FakeChefClient()
    ):
        result = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version=""),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=str(output_dir),
            dependency_depth="full",
            use_cache=False,
        )

    nginx_recipe = output_dir / "cookbooks" / "nginx" / "recipes" / "default.rb"
    apt_recipe = output_dir / "cookbooks" / "apt" / "recipes" / "default.rb"

    assert nginx_recipe.exists()
    assert apt_recipe.exists()
    assert result.manifest_path.exists()


def test_import_offline_bundle_extracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure offline bundle import extracts archives safely."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    source_dir = tmp_path / "bundle_source"
    source_dir.mkdir()
    (source_dir / "manifest.json").write_text("{}")

    archive = tmp_path / "bundle.tar.gz"
    from souschef.filesystem.operations import create_tar_gz_archive

    create_tar_gz_archive(str(source_dir), str(archive))

    target_dir = tmp_path / "bundle_target"
    extracted = import_offline_bundle(str(archive), str(target_dir))

    assert (extracted / "manifest.json").exists()


def test_fetch_cookbooks_direct_dependency_depth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test dependency depth=direct only fetches direct dependencies."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    output_dir = tmp_path / "downloads"

    with patch(
        "souschef.ingestion.build_chef_server_client", return_value=FakeChefClient()
    ):
        result = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="2.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=str(output_dir),
            dependency_depth="direct",
            use_cache=False,
        )

    assert len(result.cookbooks) == 1
    assert result.cookbooks[0].name == "nginx"


def test_fetch_cookbooks_with_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test caching of downloaded cookbooks."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    output_dir = tmp_path / "downloads"
    cache_dir = tmp_path / "cache"

    with patch(
        "souschef.ingestion.build_chef_server_client", return_value=FakeChefClient()
    ):
        # First fetch - populate cache
        result1 = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="1.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key=None,
            client_key_path="/tmp/key.pem",  # NOSONAR
            output_dir=str(output_dir),
            dependency_depth="direct",
            use_cache=True,
            cache_dir=str(cache_dir),
        )

        # Second fetch - should use cache
        output_dir2 = tmp_path / "downloads2"
        result2 = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="1.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key=None,
            client_key_path="/tmp/key.pem",  # NOSONAR
            output_dir=str(output_dir2),
            dependency_depth="direct",
            use_cache=True,
            cache_dir=str(cache_dir),
        )

    assert result1.cookbooks[0].name == "nginx"
    assert result2.cookbooks[0].name == "nginx"
    assert (cache_dir / "nginx" / "1.0.0").exists()


def test_fetch_cookbooks_with_offline_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test offline bundle creation during fetch."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    output_dir = tmp_path / "downloads"
    bundle_path = tmp_path / "bundle.tar.gz"

    with patch(
        "souschef.ingestion.build_chef_server_client", return_value=FakeChefClient()
    ):
        result = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="1.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=str(output_dir),
            dependency_depth="direct",
            use_cache=False,
            offline_bundle_path=str(bundle_path),
        )

    assert result.offline_bundle_path is not None
    assert Path(result.offline_bundle_path).exists()


def test_fetch_cookbooks_invalid_dependency_depth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error handling for invalid dependency depth."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    with (
        patch(
            "souschef.ingestion.build_chef_server_client", return_value=FakeChefClient()
        ),
        pytest.raises(ValueError, match="Dependency depth must be"),
    ):
        fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="1.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=str(tmp_path / "downloads"),
            dependency_depth="invalid",
            use_cache=False,
        )


def test_fetch_cookbooks_with_version_constraints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test handling of various version constraints."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    output_dir = tmp_path / "downloads"

    with patch(
        "souschef.ingestion.build_chef_server_client", return_value=FakeChefClient()
    ):
        result = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="2.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=str(output_dir),
            dependency_depth="full",
            use_cache=False,
        )

    # Should resolve dependencies with various constraint formats
    cookbook_names = {cb.name for cb in result.cookbooks}
    assert "nginx" in cookbook_names
    assert "apt" in cookbook_names
    assert "mysql" in cookbook_names


def test_fetch_cookbooks_missing_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test warning generation for missing dependencies."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    output_dir = tmp_path / "downloads"

    fake_client = FakeChefClient()
    # Add a cookbook with a missing dependency
    fake_client._versions["missing_deps"] = ["1.0.0"]

    def get_cookbook_with_missing_dep(
        cookbook_name: str, version: str
    ) -> dict[str, Any]:
        if cookbook_name == "missing_deps":
            return {
                "metadata": {"dependencies": {"nonexistent": ">= 0.0.0"}},
                "recipes": [],
            }
        return fake_client.get_cookbook_version(cookbook_name, version)

    fake_client.get_cookbook_version = get_cookbook_with_missing_dep

    with patch("souschef.ingestion.build_chef_server_client", return_value=fake_client):
        result = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="missing_deps", version="1.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=str(output_dir),
            dependency_depth="full",
            use_cache=False,
        )

    assert any("nonexistent" in warning for warning in result.warnings)


def test_fetch_cookbooks_download_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test warning generation for download failures."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    output_dir = tmp_path / "downloads"

    with patch(
        "souschef.ingestion.build_chef_server_client",
        return_value=FakeChefClient(fail_downloads=True),
    ):
        result = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="1.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=str(output_dir),
            dependency_depth="direct",
            use_cache=False,
        )

    assert any("Failed to download" in warning for warning in result.warnings)


def test_fetch_cookbooks_additional_cookbooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fetching with additional cookbooks from run_list."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    output_dir = tmp_path / "downloads"

    with patch(
        "souschef.ingestion.build_chef_server_client", return_value=FakeChefClient()
    ):
        result = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="1.0.0"),
            additional_cookbooks=[
                CookbookSpec(name="apt", version="2.0.0"),
                CookbookSpec(name="mysql", version="3.0.0"),
            ],
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=str(output_dir),
            dependency_depth="direct",
            use_cache=False,
        )

    cookbook_names = {cb.name for cb in result.cookbooks}
    assert "nginx" in cookbook_names
    assert "apt" in cookbook_names
    assert "mysql" in cookbook_names


def test_fetch_cookbooks_no_output_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fetch creates temp directory when no output_dir specified."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    with patch(
        "souschef.ingestion.build_chef_server_client", return_value=FakeChefClient()
    ):
        result = fetch_cookbooks_from_chef_server(
            cookbook=CookbookSpec(name="nginx", version="1.0.0"),
            additional_cookbooks=None,
            server_url="https://chef.example.com",
            organisation="default",
            client_name="chef-client",
            client_key_path="/tmp/key.pem",  # NOSONAR
            client_key=None,
            output_dir=None,
            dependency_depth="direct",
            use_cache=False,
        )

    assert result.root_dir.exists()
    assert "souschef-cookbooks-" in str(result.root_dir)
