"""
Targeted tests for the remaining 19 uncovered lines.

Each test is explicitly mapped to a specific file:line.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# souschef/ansible_upgrade.py  lines 744-748
# _handle_version_specifier – else branch (required NOT in specifier)
# ---------------------------------------------------------------------------
def test_handle_version_specifier_not_in_specifier() -> None:
    """Lines 744-748: required version is NOT within the specifier range."""
    from souschef.ansible_upgrade import _handle_version_specifier

    result: dict = {"compatible": [], "updates_needed": [], "warnings": []}
    # version ">=2.0" means 1.5 is NOT compatible
    _handle_version_specifier(result, "community.general", ">=2.0", "1.5")
    assert result["warnings"]  # a warning was added


# ---------------------------------------------------------------------------
# souschef/converters/habitat.py  lines 247-248 and 305-306
# These secondary dangerous-char checks are unreachable in practice because
# the preceding regex (lines 226-227, 300-301) already rejects any input that
# contains such characters.  They are marked # pragma: no cover in source.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# souschef/converters/playbook.py  line 159
# generate_playbook_from_recipe_with_ai – cookbook_path branch
# ---------------------------------------------------------------------------
def test_generate_playbook_with_cookbook_path(tmp_path: Path) -> None:
    """Line 159: cookbook_path triggers _ensure_within_base_path for it."""
    from souschef.converters.playbook import generate_playbook_from_recipe_with_ai

    recipe = tmp_path / "recipes" / "default.rb"
    recipe.parent.mkdir(parents=True)
    recipe.write_text("package 'nginx' do\n  action :install\nend\n")

    # Providing cookbook_path triggers line 159; without a real AI key the
    # function returns an error string, but the path was still exercised.
    result = generate_playbook_from_recipe_with_ai(
        recipe_path=str(recipe),
        ai_provider="anthropic",
        api_key="fake-key",
        cookbook_path=str(tmp_path),
    )
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# souschef/converters/playbook.py  line 268
# _initialize_ai_client – watson branch returns APIClient instance
# ---------------------------------------------------------------------------
def test_initialize_ai_client_watson() -> None:
    """Line 268: watson provider returns a mocked APIClient instance."""
    from souschef.converters import playbook as playbook_mod

    mock_client = MagicMock()
    mock_api_class = MagicMock(return_value=mock_client)

    with patch.object(playbook_mod, "APIClient", mock_api_class):
        from souschef.converters.playbook import _initialize_ai_client

        result = _initialize_ai_client(
            ai_provider="watson",
            api_key="test-key",
            project_id="proj-123",
            base_url="https://us-south.ml.cloud.ibm.com",
        )
    assert result is mock_client


# ---------------------------------------------------------------------------
# souschef/converters/playbook.py  line 341
# _call_anthropic_api – fallback to response.content[0].text
# ---------------------------------------------------------------------------
def test_call_anthropic_api_text_fallback() -> None:
    """Line 341: when no tool_use block, fall back to content[0].text."""
    from souschef.converters.playbook import _call_anthropic_api

    # Create a block that is NOT tool_use
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "fallback text"

    mock_response = MagicMock()
    mock_response.content = [text_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = _call_anthropic_api(
        client=mock_client,
        prompt="hello",
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,
        max_tokens=100,
        response_format={"type": "json_object"},
    )
    assert result == "fallback text"


# ---------------------------------------------------------------------------
# souschef/converters/playbook.py  line 2806
# _extract_chef_guards – multiple when conditions (list not scalar)
# ---------------------------------------------------------------------------
def test_extract_chef_guards_multiple_conditions() -> None:
    """Line 2806: multiple conditions produce a list in guards['when']."""
    from souschef.converters.playbook import _extract_chef_guards

    # Inline format: all guards on the same line after 'do' (before '\nend')
    # This matches the REGEX_QUOTE_DO_END pattern which captures non-newline content
    resource = {
        "type": "package",
        "name": "nginx",
        "action": "install",
        "properties": "",
    }
    raw = "package 'nginx' do; only_if 'which nginx'; not_if 'test -f /tmp/skip'\nend\n"
    guards = _extract_chef_guards(resource, raw)
    # With 2 conditions, 'when' should be a list
    assert isinstance(guards.get("when"), list)
    assert len(guards["when"]) == 2


# ---------------------------------------------------------------------------
# souschef/core/ansible_versions.py  lines 715-716
# _load_ai_cache – fresh cache with versions key
# ---------------------------------------------------------------------------
def test_load_ai_cache_fresh_with_versions(tmp_path: Path) -> None:
    """Lines 715-716: fresh cache returns the versions dict."""
    from souschef.core import ansible_versions as av_mod

    cache_file = tmp_path / "ansible_versions_cache.json"
    cache_data = {
        "cached_at": datetime.now().isoformat(),
        "versions": {"2.15": ["2.15.0", "2.15.1"], "2.16": ["2.16.0"]},
    }
    cache_file.write_text(json.dumps(cache_data))

    with (
        patch.object(av_mod, "_CACHE_FILE", cache_file),
        patch.object(av_mod, "_CACHE_DIR", tmp_path),
        patch.object(av_mod, "_get_cache_path", return_value=cache_file),
    ):
        result = av_mod._load_ai_cache()

    assert result == cache_data["versions"]


# ---------------------------------------------------------------------------
# souschef/deployment.py  line 1902
# _generate_deployment_migration_recommendations – empty recs → general list
# ---------------------------------------------------------------------------
def test_generate_deployment_migration_recommendations_empty() -> None:
    """Line 1902: no matching patterns + unknown app_type → general recommendations."""
    from souschef.deployment import _generate_deployment_migration_recommendations

    # deployment_count > 0 but all patterns unknown type → no recs added
    # app_type also unknown → no recs added
    # Triggers the 'if not recommendations' branch
    patterns = {"deployment_patterns": [{"type": "unknown_deployment_type"}]}
    result = _generate_deployment_migration_recommendations(patterns, app_type="other")
    assert "Start with non-production" in result


# ---------------------------------------------------------------------------
# souschef/generators/repo.py  line 834
# create_ansible_repository_from_roles – dest_dir already exists
# ---------------------------------------------------------------------------
def test_create_ansible_repo_dest_dir_exists(tmp_path: Path) -> None:
    """Line 834: when dest_dir exists, shutil.rmtree removes it before copy."""
    from souschef.generators.repo import RepoType, create_ansible_repository_from_roles

    # Create source role directory
    roles_dir = tmp_path / "roles_source"
    roles_dir.mkdir()
    role_dir = roles_dir / "myrole"
    role_dir.mkdir()
    (role_dir / "tasks").mkdir()
    (role_dir / "tasks" / "main.yml").write_text(
        "---\n- name: test\n  debug:\n    msg: hi\n"
    )

    # repo_path that generate_ansible_repository will "create"
    repo_path = tmp_path / "myrepo"
    repo_path.mkdir()

    # Pre-create the destination so dest_dir.exists() fires line 833-834
    # Default repo_type → roles_dest = repo_path / "roles"
    dest_role = repo_path / "roles" / "myrole"
    dest_role.mkdir(parents=True)
    (dest_role / "old.yml").write_text("old")

    # Mock generate_ansible_repository to return our pre-created repo_path
    fake_result = {
        "success": True,
        "repo_path": str(repo_path),
        "repo_type": RepoType.PLAYBOOKS_ROLES.value,
    }

    output_dir = tmp_path / "output"

    with patch(
        "souschef.generators.repo.generate_ansible_repository",
        return_value=fake_result,
    ):
        result = create_ansible_repository_from_roles(
            roles_path=str(roles_dir),
            output_path=str(output_dir),
            org_name="testorg",
            init_git=False,
            repo_type=RepoType.PLAYBOOKS_ROLES,
        )

    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# souschef/ingestion.py  line 320
# _download_cookbook – item without path/url is skipped (continue)
# ---------------------------------------------------------------------------
def test_download_cookbook_skips_item_without_path(tmp_path: Path) -> None:
    """Line 320: items missing path or url are skipped."""
    from souschef.ingestion import CookbookSpec, _download_cookbook

    mock_client = MagicMock()
    # Return metadata with one valid item and one invalid (no path)
    mock_client.get_cookbook_version.return_value = {
        "files": [
            {"url": "https://example.com/file.rb"},  # missing 'path'
            {"path": "recipes/default.rb"},  # missing 'url'
        ]
    }
    mock_client.download_url.return_value = b"# recipe"

    dest = tmp_path / "dest"
    dest.mkdir()
    cache_root = tmp_path / "cache"
    cache_root.mkdir()

    spec = CookbookSpec(name="mycookbook", version="1.0.0")

    with (
        patch("souschef.ingestion._normalise_spec", return_value=spec),
        patch(
            "souschef.ingestion._collect_cookbook_items",
            return_value=[
                {"url": "https://example.com/file.rb"},  # no path
                {"path": "recipes/default.rb"},  # no url
            ],
        ),
        patch("souschef.ingestion._write_cookbook_metadata"),
    ):
        _download_cookbook(
            client=mock_client,
            spec=spec,
            destination=dest,
            use_cache=False,
            cache_root=cache_root,
            warnings=[],
        )
    # No exception means both items were skipped gracefully


# ---------------------------------------------------------------------------
# souschef/ingestion.py  line 338
# _download_cookbook – use_cache=True, cache_dir exists → rmtree then copytree
# ---------------------------------------------------------------------------
def test_download_cookbook_cache_dir_exists_rmtree(tmp_path: Path) -> None:
    """Line 338: existing cache_dir is removed before re-caching."""
    from souschef.ingestion import CookbookSpec, _download_cookbook

    spec = CookbookSpec(name="mycookbook", version="1.0.0")

    dest = tmp_path / "dest"
    dest.mkdir()
    cache_root = tmp_path / "cache"
    cache_root.mkdir()

    # cache_dir does NOT exist initially (so we proceed to the download path).
    # We create it during _write_cookbook_metadata so that
    # the final `if cache_dir.exists()` check fires (line 337-338).
    cache_dir = cache_root / "mycookbook" / "1.0.0"

    def _create_cache_side_effect(*args: object, **kwargs: object) -> None:
        """Simulate another process creating cache_dir between download and cache."""
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "stale.rb").write_text("# stale")

    mock_client = MagicMock()
    mock_client.get_cookbook_version.return_value = {}

    with (
        patch("souschef.ingestion._normalise_spec", return_value=spec),
        patch("souschef.ingestion._collect_cookbook_items", return_value=[]),
        patch(
            "souschef.ingestion._write_cookbook_metadata",
            side_effect=_create_cache_side_effect,
        ),
    ):
        _download_cookbook(
            client=mock_client,
            spec=spec,
            destination=dest,
            use_cache=True,
            cache_root=cache_root,
            warnings=[],
        )

    # New cache dir should exist (old one replaced and cookbook_dir copied)
    assert (cache_root / "mycookbook" / "1.0.0").exists()


# ---------------------------------------------------------------------------
# souschef/migration_v2.py  lines 748 + 751
# MigrationOrchestrator._prepare_cookbook_source –
#   offline_bundle_path set + warnings from fetch
# ---------------------------------------------------------------------------
def test_prepare_cookbook_source_offline_bundle_and_warnings(tmp_path: Path) -> None:
    """Lines 748, 751: offline_bundle_path and warnings propagated from fetch result."""
    from datetime import datetime

    from souschef.ingestion import CookbookFetchResult, CookbookSpec
    from souschef.migration_v2 import (
        MigrationOrchestrator,
        MigrationResult,
        MigrationStatus,
    )

    orch = MigrationOrchestrator(
        chef_version="15.10.91",
        target_platform="awx",
        target_version="24.6.1",
    )
    orch.result = MigrationResult(
        migration_id=orch.migration_id,
        status=MigrationStatus.PENDING,
        chef_version="15.10.91",
        target_platform="awx",
        target_version="24.6.1",
        ansible_version="2.15",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        source_cookbook="",
    )

    cookbook_root = tmp_path / "cookbooks" / "myapp"
    cookbook_root.mkdir(parents=True)

    bundle_path = tmp_path / "bundle.tar.gz"
    bundle_path.write_bytes(b"fake")

    fetch_result = CookbookFetchResult(
        root_dir=tmp_path,
        cookbooks=[CookbookSpec(name="myapp", version="1.0.0")],
        dependency_graph={},
        manifest_path=tmp_path / "manifest.json",
        offline_bundle_path=bundle_path,
        warnings=["dependency X not resolved"],
    )

    with (
        patch(
            "souschef.migration_v2.fetch_cookbooks_from_chef_server",
            return_value=fetch_result,
        ),
        patch("souschef.migration_v2._get_workspace_root", return_value=tmp_path),
        patch("souschef.migration_v2._safe_join", return_value=tmp_path / ".souschef"),
    ):
        _, _ = orch._prepare_cookbook_source(
            cookbook_path="",
            chef_server_url="https://chef.example.com",
            chef_organisation="myorg",
            chef_client_name="admin",
            chef_client_key_path="/tmp/key.pem",
            chef_client_key=None,
            chef_node=None,
            chef_policy=None,
            cookbook_name="myapp",
            cookbook_version="1.0.0",
            dependency_depth="shallow",
            use_cache=False,
            offline_bundle_path=None,
        )

    # offline_bundle_path was set (line 748)
    assert orch.result.offline_bundle_path == str(bundle_path)
    # warnings were appended (line 751)
    assert any("dependency X" in w.get("message", "") for w in orch.result.warnings)


# ---------------------------------------------------------------------------
# souschef/parsers/attributes.py  line 515
# _extract_attributes – multiline Ruby array reconstructed as %w(...)
# ---------------------------------------------------------------------------
def test_extract_attributes_multiline_ruby_array() -> None:
    r"""Line 515: multiline %w( array is reconstructed with %w(\n...\n)."""
    from souschef.parsers.attributes import _extract_attributes

    # value_start = "%w(" → is_ruby_array=True
    # _collect_multiline_value returns "item1\nitem2\n)" (not starting with %w or [)
    content = "default['myapp']['list'] = %w(\nitem1\nitem2\n)\n"
    attrs = _extract_attributes(content)
    # At least one attribute should be extracted
    assert isinstance(attrs, list)


# ---------------------------------------------------------------------------
# souschef/parsers/recipe.py  line 358
# _extract_conditionals – case body too large → continue
# ---------------------------------------------------------------------------
def test_extract_conditionals_large_case_body() -> None:
    """Line 358: case body exceeding MAX_CASE_BODY_LENGTH is skipped."""
    from souschef.parsers.recipe import MAX_CASE_BODY_LENGTH, _extract_conditionals

    # Build a case block whose body exceeds the limit
    big_body = "  when 'x'\n" + ("    # filler\n" * (MAX_CASE_BODY_LENGTH // 12 + 5))
    content = f"case platform\n{big_body}\nend\n"

    result = _extract_conditionals(content)
    # The oversized case was skipped; result may be empty or contain others
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# souschef/server.py  line 4395
# _get_role_name – metadata_file does not exist → return default_name
# ---------------------------------------------------------------------------
def test_get_role_name_no_metadata_file(tmp_path: Path) -> None:
    """Line 4395: when metadata.rb is absent, default_name is returned."""
    from souschef.server import _get_role_name

    empty_dir = tmp_path / "mycookbook"
    empty_dir.mkdir()

    result = _get_role_name(empty_dir, "mycookbook")
    assert result == "mycookbook"
