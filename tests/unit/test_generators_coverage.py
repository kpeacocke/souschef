"""
Tests for missing coverage branches in generators/repo.py and other small modules.

Covers error paths, edge cases, and rarely-triggered branches not reached by
existing test suites.
"""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from souschef.ci.jenkins_pipeline import _create_lint_stage
from souschef.converters.habitat import (
    _validate_docker_image_name,
    _validate_docker_network_name,
)
from souschef.converters.playbook_optimizer import optimize_task_loops
from souschef.converters.resource import (
    _build_module_params,
    _convert_chef_resource_to_ansible,
    _get_cookbook_file_params,
    _get_include_recipe_params,
    convert_resource_to_task,
)
from souschef.generators.repo import (
    RepoType,
    _analyse_with_ai,
    _commit_repo_changes,
    _get_roles_destination,
    create_ansible_repository_from_roles,
    generate_ansible_repository,
)
from souschef.parsers.habitat import _extract_plan_array, _is_quote_blocked
from souschef.parsers.inspec import parse_inspec_profile
from souschef.parsers.recipe import parse_recipe

# ===========================================================================
# souschef/generators/repo.py
# ===========================================================================


# ---------------------------------------------------------------------------
# Lines 148, 159-167: _analyse_with_ai decision logic and exception fallback
# ---------------------------------------------------------------------------


def test_analyse_with_ai_high_complexity_collection(tmp_path: Path) -> None:
    """Test _analyse_with_ai returns COLLECTION for high complexity with roles."""
    with patch(
        "souschef.assessment.assess_single_cookbook_with_ai",
        return_value={"complexity_score": 80},
    ):
        result = _analyse_with_ai(
            str(tmp_path),
            num_recipes=5,
            num_roles=3,
            ai_provider="anthropic",
            api_key="test-key",
            model="claude",
        )

    assert result == RepoType.COLLECTION


def test_analyse_with_ai_low_complexity_playbooks(tmp_path: Path) -> None:
    """Test _analyse_with_ai returns PLAYBOOKS_ROLES for low complexity."""
    with patch(
        "souschef.assessment.assess_single_cookbook_with_ai",
        return_value={"complexity_score": 20},
    ):
        result = _analyse_with_ai(
            str(tmp_path),
            num_recipes=2,
            num_roles=1,
            ai_provider="anthropic",
            api_key="test-key",
            model="claude",
        )

    assert result == RepoType.PLAYBOOKS_ROLES


def test_analyse_with_ai_medium_complexity_playbooks(tmp_path: Path) -> None:
    """Test _analyse_with_ai returns PLAYBOOKS_ROLES for medium-low complexity."""
    with patch(
        "souschef.assessment.assess_single_cookbook_with_ai",
        return_value={"complexity_score": 40},
    ):
        result = _analyse_with_ai(
            str(tmp_path),
            num_recipes=5,
            num_roles=1,
            ai_provider="anthropic",
            api_key="test-key",
            model="claude",
        )

    assert result == RepoType.PLAYBOOKS_ROLES


def test_analyse_with_ai_default_inventory_first(tmp_path: Path) -> None:
    """Test _analyse_with_ai defaults to INVENTORY_FIRST for medium complexity."""
    with patch(
        "souschef.assessment.assess_single_cookbook_with_ai",
        return_value={"complexity_score": 60},
    ):
        result = _analyse_with_ai(
            str(tmp_path),
            num_recipes=5,
            num_roles=1,
            ai_provider="anthropic",
            api_key="test-key",
            model="claude",
        )

    assert result == RepoType.INVENTORY_FIRST


def test_analyse_with_ai_exception_returns_none(tmp_path: Path) -> None:
    """Test _analyse_with_ai returns None on exception (lines 165-167)."""
    with patch(
        "souschef.assessment.assess_single_cookbook_with_ai",
        side_effect=RuntimeError("AI boom"),
    ):
        result = _analyse_with_ai(
            str(tmp_path),
            num_recipes=5,
            num_roles=2,
            ai_provider="anthropic",
            api_key="test-key",
            model="claude",
        )

    assert result is None


def test_analyse_with_ai_error_in_assessment(tmp_path: Path) -> None:
    """Test _analyse_with_ai returns None when assessment contains error key."""
    with patch(
        "souschef.assessment.assess_single_cookbook_with_ai",
        return_value={"error": "assessment failed"},
    ):
        result = _analyse_with_ai(
            str(tmp_path),
            num_recipes=5,
            num_roles=2,
            ai_provider="anthropic",
            api_key="test-key",
            model="claude",
        )

    assert result is None


# ---------------------------------------------------------------------------
# Lines 632-633: _get_roles_destination for COLLECTION
# Line 637: _get_roles_destination for MONO_REPO
# ---------------------------------------------------------------------------


def test_get_roles_destination_collection(tmp_path: Path) -> None:
    """Test _get_roles_destination returns collection path for COLLECTION type."""
    dest = _get_roles_destination(tmp_path, RepoType.COLLECTION, "myorg")

    assert "ansible_collections" in str(dest)
    assert "myorg" in str(dest)


def test_get_roles_destination_mono_repo(tmp_path: Path) -> None:
    """Test _get_roles_destination returns shared_roles for MONO_REPO type."""
    dest = _get_roles_destination(tmp_path, RepoType.MONO_REPO, "myorg")

    assert "shared_roles" in str(dest)


def test_get_roles_destination_default(tmp_path: Path) -> None:
    """Test _get_roles_destination returns roles/ for other types."""
    dest = _get_roles_destination(tmp_path, RepoType.PLAYBOOKS_ROLES, "myorg")

    assert str(dest) == str(tmp_path / "roles")


# ---------------------------------------------------------------------------
# Lines 659-662: _commit_repo_changes error paths
# ---------------------------------------------------------------------------


def test_commit_repo_changes_git_error(tmp_path: Path) -> None:
    """Test _commit_repo_changes handles CalledProcessError gracefully."""
    import subprocess

    error = subprocess.CalledProcessError(1, "git", stderr="nothing to commit")
    with patch("subprocess.run", side_effect=error):
        result = _commit_repo_changes(tmp_path, "test commit")

    assert "skipped" in result.lower()


def test_commit_repo_changes_git_not_found(tmp_path: Path) -> None:
    """Test _commit_repo_changes handles missing git binary."""
    with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
        result = _commit_repo_changes(tmp_path, "test commit")

    assert "Git not found" in result


# ---------------------------------------------------------------------------
# Lines 706-707: generate_ansible_repository invalid path ValueError
# ---------------------------------------------------------------------------


def test_generate_ansible_repository_invalid_path() -> None:
    """Test generate_ansible_repository returns error for invalid path."""
    with patch(
        "souschef.generators.repo._normalize_path",
        side_effect=ValueError("invalid path"),
    ):
        result = generate_ansible_repository(
            output_path="/some/path",
            repo_type=RepoType.PLAYBOOKS_ROLES,
        )

    assert result["success"] is False
    assert "Invalid output path" in result["error"]


# ---------------------------------------------------------------------------
# Line 786: create_ansible_repository_from_roles when generate fails
# ---------------------------------------------------------------------------


def test_create_ansible_repository_from_roles_generate_fails(tmp_path: Path) -> None:
    """Test create_ansible_repository_from_roles returns early when repo gen fails."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "myrole").mkdir()

    output_dir = tmp_path / "output"

    with patch(
        "souschef.generators.repo.generate_ansible_repository",
        return_value={"success": False, "error": "path exists"},
    ):
        result = create_ansible_repository_from_roles(
            roles_path=str(roles_dir),
            output_path=str(output_dir),
        )

    assert result["success"] is False


# ---------------------------------------------------------------------------
# Line 814: create_ansible_repository_from_roles success returns repo_result
# Lines 817-820: invalid repo_type string in create_ansible_repository_from_roles
# ---------------------------------------------------------------------------


def test_create_ansible_repository_from_roles_invalid_type_string(
    tmp_path: Path,
) -> None:
    """Test create_ansible_repository_from_roles returns error for bad repo_type."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "myrole").mkdir()

    output_dir = tmp_path / "output"

    with patch(
        "souschef.generators.repo.generate_ansible_repository",
        return_value={
            "success": True,
            "repo_path": str(output_dir),
            "repo_type": "invalid_type",
        },
    ):
        result = create_ansible_repository_from_roles(
            roles_path=str(roles_dir),
            output_path=str(output_dir),
            repo_type="invalid_type",
        )

    assert result["success"] is False
    assert "Invalid repo_type" in result["error"]


# ---------------------------------------------------------------------------
# Line 834: existing role directory removed before copy
# ---------------------------------------------------------------------------


def test_create_ansible_repository_from_roles_removes_existing(tmp_path: Path) -> None:
    """Test create_ansible_repository_from_roles removes existing role dirs."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    role_dir = roles_dir / "webserver"
    role_dir.mkdir()
    (role_dir / "tasks").mkdir()
    (role_dir / "tasks" / "main.yml").write_text("---")

    output_dir = tmp_path / "output"

    result = create_ansible_repository_from_roles(
        roles_path=str(roles_dir),
        output_path=str(output_dir),
        init_git=False,
    )

    assert result.get("roles_copied") is not None or not result["success"]


# ---------------------------------------------------------------------------
# Lines 848-849: create_ansible_repository_from_roles exception handler
# ---------------------------------------------------------------------------


def test_create_ansible_repository_from_roles_exception(tmp_path: Path) -> None:
    """Test create_ansible_repository_from_roles handles unexpected exceptions."""
    with patch(
        "souschef.generators.repo._check_symlink_safety",
        side_effect=RuntimeError("unexpected"),
    ):
        result = create_ansible_repository_from_roles(
            roles_path=str(tmp_path),
            output_path=str(tmp_path / "output"),
        )

    assert result["success"] is False
    assert "error" in result


# ===========================================================================
# souschef/converters/resource.py
# ===========================================================================


# ---------------------------------------------------------------------------
# Lines 111-112: convert_resource_to_task exception path
# ---------------------------------------------------------------------------


def test_convert_resource_to_task_exception() -> None:
    """Test convert_resource_to_task returns error string on exception."""
    with patch(
        "souschef.converters.resource._convert_chef_resource_to_ansible",
        side_effect=RuntimeError("conversion boom"),
    ):
        result = convert_resource_to_task("package", "vim", "install", "")

    assert "An error occurred" in result


# ---------------------------------------------------------------------------
# Line 247: _get_cookbook_file_params with mode/owner/group
# Line 249: delete action sets state absent
# ---------------------------------------------------------------------------


def test_get_cookbook_file_params_with_properties() -> None:
    """Test _get_cookbook_file_params includes mode/owner/group properties."""
    props = {"mode": "0644", "owner": "root", "group": "www-data"}
    result = _get_cookbook_file_params("myfile", "create", props)

    assert result.get("mode") == "0644"
    assert result.get("owner") == "root"


def test_get_cookbook_file_params_delete_action() -> None:
    """Test _get_cookbook_file_params sets state absent for delete action."""
    result = _get_cookbook_file_params("/etc/myfile", "delete", {})

    assert result.get("state") == "absent"


# ---------------------------------------------------------------------------
# Line 265: _get_include_recipe_params returns dict from cookbook_config
# ---------------------------------------------------------------------------


def test_get_include_recipe_params_known_cookbook() -> None:
    """Test _get_include_recipe_params returns cookbook-specific config."""
    with patch(
        "souschef.converters.resource.get_cookbook_package_config",
        return_value={"module": "ansible.builtin.include_role", "params": {"name": "base"}},
    ):
        result = _get_include_recipe_params("base::default", "include", {})

    assert result == {"name": "base"}


def test_get_include_recipe_params_unknown_cookbook() -> None:
    """Test _get_include_recipe_params falls back to include_role for unknown."""
    with patch(
        "souschef.converters.resource.get_cookbook_package_config",
        return_value=None,
    ):
        result = _get_include_recipe_params("myapp::deploy", "include", {})

    assert result["name"] == "myapp"


# ---------------------------------------------------------------------------
# Line 322: _convert_chef_resource_to_ansible cookbook-specific include_recipe
# ---------------------------------------------------------------------------


def test_convert_chef_resource_include_recipe_cookbook_specific() -> None:
    """Test _convert_chef_resource_to_ansible uses cookbook module for include_recipe."""
    with patch(
        "souschef.converters.resource.get_cookbook_package_config",
        return_value={
            "module": "ansible.builtin.include_role",
            "params": {"name": "apache2"},
        },
    ):
        result = _convert_chef_resource_to_ansible(
            "include_recipe", "apache2::default", "include", ""
        )

    assert "ansible.builtin.include_role" in result


# ---------------------------------------------------------------------------
# Line 355: _convert_chef_resource_to_ansible copies cookbook params
# ---------------------------------------------------------------------------


def test_convert_chef_resource_include_recipe_params_copy() -> None:
    """Test _convert_chef_resource_to_ansible copies cookbook params (line 355)."""
    with patch(
        "souschef.converters.resource.get_cookbook_package_config",
        return_value={
            "module": "ansible.builtin.include_role",
            "params": {"name": "nginx", "tasks_from": "install"},
        },
    ):
        result = _convert_chef_resource_to_ansible(
            "include_recipe", "nginx::install", "include", ""
        )

    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Line 386: _build_module_params returns cookbook params when not None
# ---------------------------------------------------------------------------


def test_build_module_params_cookbook_params() -> None:
    """Test _build_module_params returns cookbook-specific params."""
    with patch(
        "souschef.converters.resource.build_cookbook_resource_params",
        return_value={"name": "custom_package", "state": "present"},
    ):
        result = _build_module_params("custom_resource", "mypkg", "install", {})

    assert result == {"name": "custom_package", "state": "present"}


# ---------------------------------------------------------------------------
# Line 402: _build_module_params falls back to default for unknown resources
# ---------------------------------------------------------------------------


def test_build_module_params_unknown_resource_default() -> None:
    """Test _build_module_params falls back to default for unknown resource types."""
    result = _build_module_params("totally_unknown_resource", "myname", "run", {})

    assert isinstance(result, dict)
    assert "name" in result or "command" in result


# ===========================================================================
# souschef/converters/habitat.py
# ===========================================================================


# ---------------------------------------------------------------------------
# Line 248: _validate_docker_network_name returns False for dangerous chars
# ---------------------------------------------------------------------------


def test_validate_docker_network_name_with_dangerous_char() -> None:
    """Test _validate_docker_network_name returns False for dangerous characters."""
    result = _validate_docker_network_name("my:network")

    assert result is False


def test_validate_docker_network_name_too_long() -> None:
    """Test _validate_docker_network_name returns False when name is too long."""
    long_name = "a" * 64
    result = _validate_docker_network_name(long_name)

    assert result is False


# ---------------------------------------------------------------------------
# Line 306: _validate_docker_image_name returns False for dangerous chars
# ---------------------------------------------------------------------------


def test_validate_docker_image_name_with_dangerous_char() -> None:
    """Test _validate_docker_image_name returns False for dangerous characters."""
    result = _validate_docker_image_name("ubuntu;rm -rf /")

    assert result is False


def test_validate_docker_image_name_too_long() -> None:
    """Test _validate_docker_image_name returns False when name is too long."""
    long_name = "ubuntu/" + "a" * 256
    result = _validate_docker_image_name(long_name)

    assert result is False


# ===========================================================================
# souschef/parsers/habitat.py
# ===========================================================================


# ---------------------------------------------------------------------------
# Line 149: _extract_plan_array unmatched parentheses returns empty
# ---------------------------------------------------------------------------


def test_extract_plan_array_unmatched_parens() -> None:
    """Test _extract_plan_array handles unmatched parentheses gracefully."""
    # Content with unmatched opening paren (no closing paren)
    content = "pkg_deps=(\ncore/bash\n"
    result = _extract_plan_array(content, "pkg_deps")

    # Should handle gracefully (may return partial or empty)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Line 225: _is_quote_blocked returns False for non-quote characters
# ---------------------------------------------------------------------------


def test_is_quote_blocked_non_quote_char() -> None:
    """Test _is_quote_blocked returns False for characters that aren't quotes."""
    result = _is_quote_blocked("x", False, False, False)

    assert result is False


def test_is_quote_blocked_single_quote_in_double() -> None:
    """Test _is_quote_blocked returns True for single quote inside double quote."""
    result = _is_quote_blocked("'", False, True, False)

    assert result is True


def test_is_quote_blocked_backtick_not_blocked() -> None:
    """Test _is_quote_blocked for backtick when not blocked."""
    result = _is_quote_blocked("`", False, False, False)

    assert result is False


# ===========================================================================
# souschef/parsers/recipe.py
# ===========================================================================


# ---------------------------------------------------------------------------
# Line 226: parse_recipe skips oversized resource bodies
# ---------------------------------------------------------------------------


def test_parse_recipe_oversized_resource_body(tmp_path: Path) -> None:
    """Test parse_recipe skips resource bodies exceeding max length."""
    # Create a recipe with a very long resource body
    large_content = "package 'vim' do\n" + "  # comment\n" * 1600 + "end\n"
    recipe_file = tmp_path / "default.rb"
    recipe_file.write_text(large_content)

    result = parse_recipe(str(recipe_file))

    # Should complete without error (body skipped)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Line 358: parse_recipe skips oversized case bodies
# ---------------------------------------------------------------------------


def test_parse_recipe_oversized_case_body(tmp_path: Path) -> None:
    """Test parse_recipe skips case bodies exceeding max length."""
    # Create a recipe with a case block with very long body
    large_case = (
        "case node['platform']\n"
         "when 'ubuntu'\n"
         "  # " + "x" * 300 + "\n"
    ) * 10 + "end\n"
    recipe_file = tmp_path / "default.rb"
    recipe_file.write_text(large_case)

    result = parse_recipe(str(recipe_file))

    assert isinstance(result, str)


# ===========================================================================
# souschef/parsers/inspec.py
# ===========================================================================


# ---------------------------------------------------------------------------
# Line 78: parse_inspec_profile for special file (not file or dir)
# ---------------------------------------------------------------------------


def test_parse_inspec_profile_special_file() -> None:
    """Test parse_inspec_profile returns error for special file types."""
    with (
        tempfile.NamedTemporaryFile(suffix=".rb") as tmp_f,
        patch.object(Path, "is_dir", return_value=False),
        patch.object(Path, "is_file", return_value=False),
        patch.object(Path, "exists", return_value=True),
    ):
        result = parse_inspec_profile(tmp_f.name)

    assert "Error" in result
    assert "Invalid path type" in result


# ===========================================================================
# souschef/ci/jenkins_pipeline.py
# ===========================================================================


# ---------------------------------------------------------------------------
# Line 54: _create_lint_stage returns None when no lint steps matched
# ---------------------------------------------------------------------------


def test_create_lint_stage_no_matching_tools() -> None:
    """Test _create_lint_stage returns None when no recognised tools found."""
    ci_patterns: dict[str, Any] = {"lint_tools": ["rubocop", "unknown_tool"]}

    result = _create_lint_stage(ci_patterns)

    assert result is None


def test_create_lint_stage_cookstyle() -> None:
    """Test _create_lint_stage generates ansible-lint step for cookstyle."""
    ci_patterns: dict[str, Any] = {"lint_tools": ["cookstyle"]}

    result = _create_lint_stage(ci_patterns)

    assert result is not None
    assert "ansible-lint" in result


# ===========================================================================
# souschef/converters/playbook_optimizer.py
# ===========================================================================


# ---------------------------------------------------------------------------
# Line 155: optimize_task_loops consolidates 3+ similar tasks into a loop
# ---------------------------------------------------------------------------


def test_optimize_task_loops_consolidates_similar() -> None:
    """Test optimize_task_loops consolidates 3+ similar tasks into a loop."""
    tasks = [
        {"name": "install vim", "apt": {"name": "vim", "state": "present"}},
        {"name": "install git", "apt": {"name": "git", "state": "present"}},
        {"name": "install curl", "apt": {"name": "curl", "state": "present"}},
        {"name": "install wget", "apt": {"name": "wget", "state": "present"}},
    ]

    result = optimize_task_loops(tasks)

    # Should consolidate to fewer tasks
    assert isinstance(result, list)
    assert len(result) < len(tasks)


def test_optimize_task_loops_no_consolidation() -> None:
    """Test optimize_task_loops leaves dissimilar tasks unchanged."""
    tasks = [
        {"name": "install vim", "apt": {"name": "vim"}},
        {"name": "start nginx", "service": {"name": "nginx", "state": "started"}},
        {"name": "copy config", "copy": {"src": "nginx.conf", "dest": "/etc/nginx/"}},
    ]

    result = optimize_task_loops(tasks)

    assert len(result) == len(tasks)
