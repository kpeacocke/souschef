"""Tests for Ansible repository generation."""

import io
import json
from pathlib import Path
from unittest.mock import patch

import hypothesis
from hypothesis import given, settings
from hypothesis import strategies as st

from souschef.generators.repo import (
    RepoType,
    analyse_conversion_output,
    generate_ansible_repository,
)

# ============================================================================
# Unit Tests
# ============================================================================


class TestAnalyseConversionOutput:
    """Test repo type analysis logic."""

    def test_suggests_collection_for_many_roles(self, tmp_path):
        """Test that collection layout is suggested for 3+ roles."""
        result = analyse_conversion_output(
            cookbook_path=str(tmp_path / "test"),
            num_recipes=5,
            num_roles=3,
            has_multiple_apps=False,
            needs_multi_env=True,
        )
        assert result == RepoType.COLLECTION

    def test_suggests_mono_repo_for_multiple_apps(self, tmp_path):
        """Test that mono-repo is suggested for multiple applications."""
        result = analyse_conversion_output(
            cookbook_path=str(tmp_path / "test"),
            num_recipes=4,
            num_roles=2,
            has_multiple_apps=True,
            needs_multi_env=True,
        )
        assert result == RepoType.MONO_REPO

    def test_suggests_simple_for_small_projects(self, tmp_path):
        """Test that simple structure is suggested for small projects."""
        result = analyse_conversion_output(
            cookbook_path=str(tmp_path / "test"),
            num_recipes=2,
            num_roles=1,
            has_multiple_apps=False,
            needs_multi_env=False,
        )
        assert result == RepoType.PLAYBOOKS_ROLES

    def test_suggests_inventory_first_by_default(self, tmp_path):
        """Test that inventory-first is suggested by default for infra."""
        result = analyse_conversion_output(
            cookbook_path=str(tmp_path / "test"),
            num_recipes=4,
            num_roles=2,
            has_multiple_apps=False,
            needs_multi_env=True,
        )
        assert result == RepoType.INVENTORY_FIRST

    def test_ai_analysis_high_complexity_multiple_roles(self, tmp_path):
        """Test that high complexity + multiple roles returns collection."""
        mock_assessment = {
            "complexity_score": 75,
            "estimated_effort_days": 10,
            "ai_insights": "Complex multi-component system",
        }

        with patch(
            "souschef.assessment.assess_single_cookbook_with_ai",
            return_value=mock_assessment,
        ):
            result = analyse_conversion_output(
                cookbook_path=str(tmp_path / "test"),
                num_recipes=5,
                num_roles=2,
                has_multiple_apps=False,
                needs_multi_env=True,
                ai_provider="anthropic",
                api_key="test-key",
            )

        assert result == RepoType.COLLECTION

    def test_ai_analysis_low_complexity_simple_project(self, tmp_path):
        """Test that low complexity with simple structure returns playbooks_roles."""
        mock_assessment = {
            "complexity_score": 25,
            "estimated_effort_days": 2,
            "ai_insights": "Simple cookie cutter pattern",
        }

        with patch(
            "souschef.assessment.assess_single_cookbook_with_ai",
            return_value=mock_assessment,
        ):
            result = analyse_conversion_output(
                cookbook_path=str(tmp_path / "test"),
                num_recipes=2,
                num_roles=1,
                has_multiple_apps=False,
                needs_multi_env=False,
                ai_provider="anthropic",
                api_key="test-key",
            )

        assert result == RepoType.PLAYBOOKS_ROLES

    def test_ai_analysis_high_complexity_defaults_to_inventory_first(self, tmp_path):
        """Test that high complexity defaults to inventory-first."""
        mock_assessment = {
            "complexity_score": 80,
            "estimated_effort_days": 15,
            "ai_insights": "Enterprise infrastructure automation",
        }

        with patch(
            "souschef.assessment.assess_single_cookbook_with_ai",
            return_value=mock_assessment,
        ):
            result = analyse_conversion_output(
                cookbook_path=str(tmp_path / "test"),
                num_recipes=10,
                num_roles=1,
                has_multiple_apps=False,
                needs_multi_env=True,
                ai_provider="anthropic",
                api_key="test-key",
            )

        assert result == RepoType.INVENTORY_FIRST

    def test_ai_analysis_error_falls_back_to_heuristics(self, tmp_path):
        """Test that AI errors fall back to heuristic analysis."""
        mock_assessment = {"error": "AI service unavailable"}

        with patch(
            "souschef.assessment.assess_single_cookbook_with_ai",
            return_value=mock_assessment,
        ):
            result = analyse_conversion_output(
                cookbook_path=str(tmp_path / "test"),
                num_recipes=5,
                num_roles=3,
                has_multiple_apps=False,
                needs_multi_env=True,
                ai_provider="anthropic",
                api_key="test-key",
            )

        # Heuristics should suggest collection for 3+ roles
        assert result == RepoType.COLLECTION

    def test_no_ai_credentials_uses_heuristics(self, tmp_path):
        """Test that missing AI credentials falls back to heuristics."""
        result = analyse_conversion_output(
            cookbook_path=str(tmp_path / "test"),
            num_recipes=5,
            num_roles=3,
            has_multiple_apps=False,
            needs_multi_env=True,
            ai_provider="",  # Empty provider
            api_key="",  # Empty key
        )

        # Heuristics should suggest collection for 3+ roles
        assert result == RepoType.COLLECTION


class TestGenerateAnsibleRepository:
    """Test repository generation."""

    def test_rejects_existing_path(self, tmp_path):
        """Test that generation fails for existing paths."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        result = generate_ansible_repository(
            output_path=str(existing_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_accepts_string_repo_type(self, tmp_path):
        """Test that string repo types are converted to enum."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type="playbooks_roles",
            init_git=False,
        )

        assert result["success"] is True
        assert result["repo_type"] == "playbooks_roles"

    def test_rejects_invalid_repo_type(self, tmp_path):
        """Test that invalid repo types are rejected."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type="invalid_type",
            init_git=False,
        )

        assert result["success"] is False
        assert "Invalid repo_type" in result["error"]

    def test_creates_common_files(self, tmp_path):
        """Test that common files are created for all repo types."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True

        # Check common files
        assert (output_dir / "ansible.cfg").exists()
        assert (output_dir / "requirements.yml").exists()
        assert (output_dir / ".gitignore").exists()
        assert (output_dir / "README.md").exists()

    def test_inventory_first_structure(self, tmp_path):
        """Test inventory-first repo structure creation."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.INVENTORY_FIRST,
            init_git=False,
        )

        assert result["success"] is True

        # Check inventory-first specific structure
        assert (output_dir / "inventories" / "prod" / "hosts.yml").exists()
        assert (output_dir / "inventories" / "nonprod" / "hosts.yml").exists()
        assert (output_dir / "inventories" / "prod" / "group_vars").is_dir()
        assert (output_dir / "playbooks").is_dir()
        assert (output_dir / "roles").is_dir()
        assert (output_dir / "filter_plugins").is_dir()

    def test_playbooks_roles_structure(self, tmp_path):
        """Test simple playbooks + roles structure creation."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True

        # Check simple structure
        assert (output_dir / "inventory" / "hosts.yml").exists()
        assert (output_dir / "inventory" / "group_vars").is_dir()
        assert (output_dir / "playbooks").is_dir()
        assert (output_dir / "roles").is_dir()

    def test_collection_structure(self, tmp_path):
        """Test Ansible Collection structure creation."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.COLLECTION,
            org_name="testorg",
            init_git=False,
        )

        assert result["success"] is True

        # Check collection structure
        collection_base = output_dir / "ansible_collections" / "testorg" / "platform"
        assert (collection_base / "galaxy.yml").exists()
        assert (collection_base / "plugins").is_dir()
        assert (collection_base / "roles").is_dir()
        assert (collection_base / "playbooks").is_dir()
        assert (collection_base / "docs").is_dir()

    def test_mono_repo_structure(self, tmp_path):
        """Test mono-repo structure creation."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.MONO_REPO,
            init_git=False,
        )

        assert result["success"] is True

        # Check mono-repo structure
        assert (output_dir / "projects" / "app1" / "playbooks").is_dir()
        assert (output_dir / "projects" / "app1" / "roles").is_dir()
        assert (output_dir / "shared_roles").is_dir()
        assert (output_dir / "collections").is_dir()

    def test_git_initialisation_success(self, tmp_path):
        """Test successful git initialisation."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=True,
        )

        assert result["success"] is True
        assert "git_status" in result

        # Check git was initialised
        if "initialised" in result["git_status"]:
            assert (output_dir / ".git").is_dir()

    def test_git_initialisation_skipped(self, tmp_path):
        """Test git initialisation can be skipped."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True
        assert result["git_status"] == ""
        assert not (output_dir / ".git").exists()

    @patch("subprocess.run")
    def test_git_not_available(self, mock_run, tmp_path):
        """Test graceful handling when git is not available."""
        mock_run.side_effect = FileNotFoundError("git not found")

        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=True,
        )

        assert result["success"] is True
        assert "Git not found" in result["git_status"]

    def test_files_created_list(self, tmp_path):
        """Test that files_created list is accurate."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True
        assert len(result["files_created"]) > 0
        assert "ansible.cfg" in result["files_created"]
        assert "README.md" in result["files_created"]

    def test_custom_org_name(self, tmp_path):
        """Test custom organisation name is used."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.COLLECTION,
            org_name="custom_org",
            init_git=False,
        )

        assert result["success"] is True

        # Check org name in collection path
        collection_base = output_dir / "ansible_collections" / "custom_org"
        assert collection_base.exists()

        # Check org name in README
        readme_content = (output_dir / "README.md").read_text()
        assert "custom_org" in readme_content


# ============================================================================
# Integration Tests
# ============================================================================


class TestRepositoryIntegration:
    """Integration tests with real file operations."""

    def test_generated_ansible_cfg_is_valid(self, tmp_path):
        """Test that generated ansible.cfg is valid."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.INVENTORY_FIRST,
            init_git=False,
        )

        assert result["success"] is True

        ansible_cfg = output_dir / "ansible.cfg"
        content = ansible_cfg.read_text()

        # Check for required sections
        assert "[defaults]" in content
        assert "[privilege_escalation]" in content
        assert "[ssh_connection]" in content
        assert "inventory =" in content
        assert "roles_path =" in content

    def test_generated_requirements_yml_is_valid_yaml(self, tmp_path):
        """Test that requirements.yml is valid YAML."""
        import yaml

        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True

        requirements_file = output_dir / "requirements.yml"
        content = yaml.safe_load(requirements_file.read_text())

        # Check structure
        assert "collections" in content
        assert "roles" in content
        assert isinstance(content["collections"], list)

    def test_generated_playbook_is_valid_yaml(self, tmp_path):
        """Test that generated playbooks are valid YAML."""
        import yaml

        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.INVENTORY_FIRST,
            init_git=False,
        )

        assert result["success"] is True

        playbook_file = output_dir / "playbooks" / "site.yml"
        content = yaml.safe_load(playbook_file.read_text())

        # Check playbook structure
        assert isinstance(content, list)
        assert "name" in content[0]
        assert "hosts" in content[0]

    def test_generated_inventory_is_valid_yaml(self, tmp_path):
        """Test that generated inventory is valid YAML."""
        import yaml

        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.INVENTORY_FIRST,
            init_git=False,
        )

        assert result["success"] is True

        inventory_file = output_dir / "inventories" / "prod" / "hosts.yml"
        content = yaml.safe_load(inventory_file.read_text())

        # Check inventory structure
        assert "all" in content
        assert isinstance(content["all"], dict)

    def test_gitignore_covers_common_patterns(self, tmp_path):
        """Test that .gitignore covers common Ansible patterns."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True

        gitignore = output_dir / ".gitignore"
        content = gitignore.read_text()

        # Check for important patterns
        assert "*.retry" in content
        assert "__pycache__" in content
        assert "vault-password.txt" in content
        assert ".DS_Store" in content


# ============================================================================
# Property-Based Tests
# ============================================================================


@given(
    num_recipes=st.integers(min_value=0, max_value=20),
    num_roles=st.integers(min_value=0, max_value=10),
    has_multiple_apps=st.booleans(),
    needs_multi_env=st.booleans(),
)
@settings(
    max_examples=50,
    suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
)
def test_analyse_always_returns_valid_repo_type(
    num_recipes, num_roles, has_multiple_apps, needs_multi_env, tmp_path
):
    """Test that analysis always returns a valid RepoType."""
    result = analyse_conversion_output(
        cookbook_path=str(tmp_path / "test"),
        num_recipes=num_recipes,
        num_roles=num_roles,
        has_multiple_apps=has_multiple_apps,
        needs_multi_env=needs_multi_env,
    )

    assert isinstance(result, RepoType)
    assert result in [
        RepoType.INVENTORY_FIRST,
        RepoType.PLAYBOOKS_ROLES,
        RepoType.COLLECTION,
        RepoType.MONO_REPO,
    ]


@given(
    org_name=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    )
)
@settings(
    max_examples=50,
    suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
)
def test_generate_handles_various_org_names(org_name, tmp_path):
    """Test that generation handles various organisation names."""
    output_dir = tmp_path / "test_repo" / org_name[:20]  # Limit length

    result = generate_ansible_repository(
        output_path=str(output_dir),
        repo_type=RepoType.PLAYBOOKS_ROLES,
        org_name=org_name,
        init_git=False,
    )

    # Should either succeed or fail gracefully
    assert "success" in result
    if result["success"]:
        assert (output_dir / "README.md").exists()


@given(repo_type=st.sampled_from(list(RepoType)))
@settings(
    max_examples=50,
    suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
)
def test_all_repo_types_generate_successfully(repo_type, tmp_path):
    """Test that all repo types can be generated."""
    output_dir = tmp_path / f"test_repo_{repo_type.value}"

    result = generate_ansible_repository(
        output_path=str(output_dir),
        repo_type=repo_type,
        init_git=False,
    )

    assert result["success"] is True
    assert result["repo_type"] == repo_type.value
    assert len(result["files_created"]) > 0


# ============================================================================
# MCP Tool Integration Tests (requires server.py)
# ============================================================================


class TestMCPToolIntegration:
    """Test the MCP tool wrapper."""

    def test_mcp_tool_with_auto_detection(self, tmp_path):
        """Test MCP tool with auto repo type detection."""
        from souschef.server import generate_ansible_repository as mcp_generate

        # Create a fake cookbook
        cookbook_dir = tmp_path / "test_cookbook"
        cookbook_dir.mkdir()
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("# test recipe")
        (recipes_dir / "web.rb").write_text("# web recipe")

        output_dir = tmp_path / "output_repo"

        result_json = mcp_generate(
            output_path=str(output_dir),
            repo_type="auto",
            cookbook_path=str(cookbook_dir),
            org_name="testorg",
            init_git="no",
        )

        result = json.loads(result_json)
        assert result["success"] is True
        assert result["repo_type"] in [t.value for t in RepoType]

    def test_mcp_tool_with_explicit_type(self, tmp_path):
        """Test MCP tool with explicit repo type."""
        from souschef.server import generate_ansible_repository as mcp_generate

        output_dir = tmp_path / "output_repo"

        result_json = mcp_generate(
            output_path=str(output_dir),
            repo_type="playbooks_roles",
            org_name="testorg",
            init_git="no",
        )

        result = json.loads(result_json)
        assert result["success"] is True
        assert result["repo_type"] == "playbooks_roles"

    def test_mcp_tool_requires_cookbook_for_auto(self, tmp_path):
        """Test that MCP tool requires cookbook_path with auto detection."""
        from souschef.server import generate_ansible_repository as mcp_generate

        output_dir = tmp_path / "output_repo"

        result_json = mcp_generate(
            output_path=str(output_dir),
            repo_type="auto",
            cookbook_path="",  # Empty path
            init_git="no",
        )

        result = json.loads(result_json)
        assert result["success"] is False
        assert "cookbook_path required" in result["error"]


# ============================================================================
# Exception Path Tests (Lines 402, 492-493)
# ============================================================================


class TestExceptionPaths:
    """Test exception paths in repository generation."""

    def test_git_init_subprocess_failure(self, tmp_path):
        """Test git initialisation handles subprocess failure gracefully."""
        import subprocess

        from souschef.generators.repo import _init_git_repo

        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "git", stderr="fatal: not a git repository"
            )

            result = _init_git_repo(repo_dir)

            assert "Git initialisation failed" in result
            assert "fatal: not a git repository" in result

    def test_git_not_found_error(self, tmp_path):
        """Test git initialisation handles missing git binary."""
        from souschef.generators.repo import _init_git_repo

        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")

            result = _init_git_repo(repo_dir)

            assert "Git not found" in result
            assert "skipped repository initialisation" in result

    def test_generate_repository_general_exception(self, tmp_path):
        """Test generate_ansible_repository handles unexpected exceptions."""
        output_dir = tmp_path / "output_repo"

        # Trigger exception by patching _create_ansible_cfg to fail
        with patch("souschef.generators.repo._create_ansible_cfg") as mock_create:
            mock_create.side_effect = RuntimeError("Unexpected filesystem error")

            result = generate_ansible_repository(
                output_path=str(output_dir),
                repo_type=RepoType.PLAYBOOKS_ROLES,
                org_name="testorg",
                init_git=False,
            )

            assert result["success"] is False
            assert "Failed to generate repository" in result["error"]
            assert "Unexpected filesystem error" in result["error"]

    def test_generate_repository_permission_error(self, tmp_path):
        """Test repository generation handles permission errors."""
        output_dir = tmp_path / "output_repo"

        with (
            patch("souschef.generators.repo._normalize_path", return_value=output_dir),
            patch(
                "souschef.core.path_utils._ensure_within_base_path",
                return_value=output_dir,
            ),
            patch("souschef.generators.repo._check_symlink_safety"),
            patch.object(Path, "exists", return_value=False),
            patch.object(
                Path,
                "mkdir",
                side_effect=PermissionError(
                    "Permission denied: cannot create directory"
                ),
            ),
        ):
            result = generate_ansible_repository(
                output_path=str(output_dir),
                repo_type=RepoType.PLAYBOOKS_ROLES,
                org_name="testorg",
                init_git=False,
            )

            assert result["success"] is False
            assert "error" in result

    def test_git_init_with_invalid_path(self, tmp_path):
        """Test git initialisation with invalid path."""
        from souschef.generators.repo import _init_git_repo

        invalid_path = tmp_path / "nonexistent" / "nested" / "path"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = _init_git_repo(invalid_path)

            assert "Git not found" in result or "skipped" in result


# ============================================================================
# UI Integration Tests
# ============================================================================


class TestUIIntegration:
    """Test UI helper functions from cookbook_analysis.py."""

    def test_create_ansible_repository_success(self, tmp_path):
        """Test _create_ansible_repository creates valid repository."""
        from souschef.ui.pages.cookbook_analysis import _create_ansible_repository

        output_path = tmp_path / "roles_output"
        output_path.mkdir()

        # Create a dummy role structure
        role_dir = output_path / "web_server"
        role_dir.mkdir()
        (role_dir / "tasks").mkdir()
        (role_dir / "tasks" / "main.yml").write_text("---\n- name: test task\n")

        result = _create_ansible_repository(
            output_path=str(output_path), cookbook_path="", num_roles=1
        )

        assert result["success"] is True
        assert "temp_path" in result
        assert Path(result["temp_path"]).exists()

        # Cleanup temp directory
        import shutil

        shutil.rmtree(result["temp_path"])

    def test_create_ansible_repository_with_cookbook_path(self, tmp_path):
        """Test repository creation with cookbook analysis."""
        from souschef.ui.pages.cookbook_analysis import _create_ansible_repository

        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()
        recipes_dir = cookbook_path / "recipes"
        recipes_dir.mkdir()

        # Create dummy recipe files
        (recipes_dir / "default.rb").write_text("package 'nginx'")
        (recipes_dir / "web.rb").write_text("service 'nginx'")

        output_path = tmp_path / "output"
        output_path.mkdir()

        result = _create_ansible_repository(
            output_path=str(output_path),
            cookbook_path=str(cookbook_path),
            num_roles=2,
        )

        assert result["success"] is True
        assert "temp_path" in result

        # Cleanup
        import shutil

        shutil.rmtree(result["temp_path"])

    def test_create_ansible_repository_error_handling(self, tmp_path):
        """Test repository creation handles errors gracefully."""
        from souschef.ui.pages.cookbook_analysis import _create_ansible_repository

        # Use invalid path to trigger error
        with patch(
            "souschef.ui.pages.cookbook_analysis.generate_ansible_repository"
        ) as mock_gen:
            mock_gen.side_effect = RuntimeError("Test error")

            result = _create_ansible_repository(
                output_path="/invalid/path", cookbook_path="", num_roles=1
            )

            assert result["success"] is False
            assert "error" in result

    def test_create_repository_zip_success(self, tmp_path):
        """Test _create_repository_zip creates valid ZIP archive."""
        import zipfile

        from souschef.ui.pages.cookbook_analysis import _create_repository_zip

        # Create test repository structure
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "ansible.cfg").write_text("[defaults]\n")
        roles_dir = repo_path / "roles"
        roles_dir.mkdir()
        (roles_dir / "test_role").mkdir()
        (roles_dir / "test_role" / "tasks").mkdir()
        (roles_dir / "test_role" / "tasks" / "main.yml").write_text("---\n")

        # Create ZIP
        zip_data = _create_repository_zip(str(repo_path))

        # Validate ZIP
        assert isinstance(zip_data, bytes)
        assert len(zip_data) > 0

        # Verify ZIP contents
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            names = zf.namelist()
            assert any("ansible.cfg" in name for name in names)
            assert any("roles" in name for name in names)

    def test_create_repository_zip_with_nested_structure(self, tmp_path):
        """Test ZIP creation with deeply nested directory structure."""
        import zipfile

        from souschef.ui.pages.cookbook_analysis import _create_repository_zip

        repo_path = tmp_path / "test_repo"
        nested_dir = repo_path / "a" / "b" / "c" / "d"
        nested_dir.mkdir(parents=True)
        (nested_dir / "file.txt").write_text("test content")

        zip_data = _create_repository_zip(str(repo_path))

        assert len(zip_data) > 0

        # Verify nested structure preserved
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            assert any("a/b/c/d/file.txt" in name for name in zf.namelist())

    def test_create_repository_zip_excludes_hidden_files(self, tmp_path):
        """Test that ZIP creation includes .git but excludes other hidden files."""
        import zipfile

        from souschef.ui.pages.cookbook_analysis import _create_repository_zip

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "visible.txt").write_text("visible")
        (repo_path / ".hidden").write_text("hidden")
        (repo_path / ".git").mkdir()
        (repo_path / ".git" / "config").write_text("git config")
        (repo_path / ".gitignore").write_text("*.pyc")

        zip_data = _create_repository_zip(str(repo_path))

        # Verify behavior:
        # - .git directory SHOULD be included (git history preserved)
        # - .gitignore SHOULD be included (important dotfile)
        # - .hidden SHOULD be excluded (random hidden file)
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            names = zf.namelist()
            assert any(".git" in name for name in names), ".git should be included"
            assert any(".gitignore" in name for name in names), (
                ".gitignore should be included"
            )
            assert not any(".hidden" in name for name in names), (
                ".hidden should be excluded"
            )

    def test_create_repository_with_multiple_roles(self, tmp_path):
        """Test repository creation with multiple roles."""
        from souschef.ui.pages.cookbook_analysis import _create_ansible_repository

        output_path = tmp_path / "roles_output"
        output_path.mkdir()

        # Create multiple role directories
        for i in range(3):
            role_dir = output_path / f"role_{i}"
            role_dir.mkdir()
            (role_dir / "tasks").mkdir()
            (role_dir / "tasks" / "main.yml").write_text(f"---\n# Role {i}\n")

        result = _create_ansible_repository(
            output_path=str(output_path), cookbook_path="", num_roles=3
        )

        assert result["success"] is True

        # Verify roles were copied
        temp_path = Path(result["temp_path"])
        roles_dirs = [
            temp_path / "roles",
            temp_path / "ansible_collections" / "souschef" / "platform" / "roles",
        ]

        roles_found = False
        for roles_dir in roles_dirs:
            if roles_dir.exists():
                roles_found = True
                break

        assert roles_found

        # Cleanup
        import shutil

        shutil.rmtree(result["temp_path"])


# ============================================================================
# MCP Tool Edge Cases
# ============================================================================


class TestMCPEdgeCases:
    """Test MCP tool with edge cases and error scenarios."""

    def test_mcp_with_malformed_cookbook_path(self, tmp_path):
        """Test MCP tool handles malformed cookbook paths."""
        from souschef.server import generate_ansible_repository as mcp_generate

        output_dir = tmp_path / "output"

        # Test with path containing null bytes
        result_json = mcp_generate(
            output_path=str(output_dir),
            repo_type="auto",
            cookbook_path=str(tmp_path / "test_malicious"),
            init_git="no",
        )

        result = json.loads(result_json)
        assert result["success"] is False

    def test_mcp_with_nonexistent_cookbook_path(self, tmp_path):
        """Test MCP tool with non-existent cookbook path."""
        from souschef.server import generate_ansible_repository as mcp_generate

        output_dir = tmp_path / "output"
        nonexistent = tmp_path / "does_not_exist" / "cookbook"

        result_json = mcp_generate(
            output_path=str(output_dir),
            repo_type="auto",
            cookbook_path=str(nonexistent),
            init_git="no",
        )

        result = json.loads(result_json)
        # Should still attempt to generate repo even if cookbook doesn't exist
        assert "success" in result

    def test_mcp_with_existing_output_directory(self, tmp_path):
        """Test MCP tool when output directory already exists."""
        from souschef.server import generate_ansible_repository as mcp_generate

        output_dir = tmp_path / "existing_output"
        output_dir.mkdir()

        # Create existing content
        (output_dir / "existing_file.txt").write_text("existing content")

        result_json = mcp_generate(
            output_path=str(output_dir),
            repo_type="playbooks_roles",
            init_git="no",
        )

        result = json.loads(result_json)
        # Should handle gracefully - either succeeds or returns valid error
        assert "success" in result
        assert isinstance(result["success"], bool)

    def test_mcp_with_invalid_repo_type(self, tmp_path):
        """Test MCP tool with invalid repo type."""
        from souschef.server import generate_ansible_repository as mcp_generate

        output_dir = tmp_path / "output"

        result_json = mcp_generate(
            output_path=str(output_dir),
            repo_type="invalid_type_xyz",
            init_git="no",
        )

        result = json.loads(result_json)
        assert result["success"] is False
        assert "Invalid repo_type" in result["error"]

    def test_mcp_with_special_characters_in_org_name(self, tmp_path):
        """Test MCP tool handles special characters in org name."""
        from souschef.server import generate_ansible_repository as mcp_generate

        output_dir = tmp_path / "output"

        result_json = mcp_generate(
            output_path=str(output_dir),
            repo_type="collection",
            org_name="my@org!#$%",
            init_git="no",
        )

        result = json.loads(result_json)
        # Should sanitise org name or handle gracefully
        assert "success" in result

    def test_mcp_with_very_long_paths(self, tmp_path):
        """Test MCP tool with extremely long file paths."""
        from souschef.server import generate_ansible_repository as mcp_generate

        # Create deeply nested path
        long_path = tmp_path
        for i in range(20):
            long_path = long_path / f"very_long_directory_name_{i}"

        result_json = mcp_generate(
            output_path=str(long_path),
            repo_type="playbooks_roles",
            init_git="no",
        )

        result = json.loads(result_json)
        # Should handle path length limits gracefully
        assert "success" in result

    def test_mcp_git_init_boolean_variations(self, tmp_path):
        """Test MCP tool handles various boolean formats for init_git."""
        from souschef.server import generate_ansible_repository as mcp_generate

        output_dir = tmp_path / "output"

        test_cases = [
            ("true", True),
            ("false", False),
            ("yes", True),
            ("no", False),
            ("1", True),
            ("0", False),
        ]

        for git_value, expected_init in test_cases:
            result_json = mcp_generate(
                output_path=str(output_dir / f"test_{git_value}"),
                repo_type="playbooks_roles",
                init_git=git_value,
            )

            result = json.loads(result_json)
            assert result["success"], f"Failed with init_git={git_value}"

            # Validate git initialization based on expected boolean value
            if expected_init:
                assert result["git_status"], f"Expected git init with {git_value}"
            else:
                assert result["git_status"] == "", (
                    f"Expected no git init with {git_value}"
                )
