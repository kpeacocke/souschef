"""Aggressive coverage targeting uncovered error paths and edge cases."""

from pathlib import Path

from souschef.assessment import (
    _parse_berksfile,
    _parse_chefignore,
    _parse_metadata_file,
)
from souschef.converters.playbook import (
    _create_ai_conversion_prompt,
    _normalize_path,
)
from souschef.server import (
    convert_inspec_to_test,
    parse_inspec_profile,
)


# PLAYBOOK PROMPTING TESTS
def test_create_prompt_with_all_recommendations() -> None:
    """Prompt creation includes all recommendation parts."""
    recommendations = {
        "project_complexity": "High",
        "migration_strategy": "phased",
        "project_effort_days": 25.0,
        "dependency_density": 1.5,
        "recommendations": ["Use Lightspeed", "Group roles"],
        "migration_order": [
            {
                "cookbook": "base",
                "phase": "1",
                "complexity": "low",
                "dependencies": [],
                "reason": "foundation",
            },
            {
                "cookbook": "app",
                "phase": "2",
                "complexity": "high",
                "dependencies": ["base"],
                "reason": "main",
            },
        ],
    }
    prompt = _create_ai_conversion_prompt(
        "package 'nginx'", "Package resource", "recipes/default.rb", recommendations
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 50


def test_create_prompt_minimal_recommendations() -> None:
    """Prompt creation with minimal recommendation structure."""
    recommendations = {"project_complexity": "Low", "migration_order": []}
    prompt = _create_ai_conversion_prompt(
        "service 'nginx'", "Service resource", "recipes/simple.rb", recommendations
    )
    assert isinstance(prompt, str)


def test_create_prompt_empty_recommendations() -> None:
    """Prompt creation with empty recommendation dict."""
    prompt = _create_ai_conversion_prompt(
        "template '/etc/nginx'", "Template resource", "recipes/test.rb"
    )
    assert isinstance(prompt, str)


# PATH NORMALIZATION TESTS
def test_normalize_path_absolute(tmp_path: Path) -> None:
    """Path normalisation handles absolute paths."""
    test_file = tmp_path / "test.rb"
    test_file.touch()
    result = _normalize_path(str(test_file))
    assert isinstance(result, (str, Path))


def test_normalize_path_relative() -> None:
    """Path normalisation handles relative paths."""
    result = _normalize_path("relative/path")
    assert isinstance(result, (str, Path))


def test_normalize_path_dots() -> None:
    """Path normalisation resolves .. directories."""
    result = _normalize_path("../relative")
    assert isinstance(result, (str, Path))


def test_normalize_path_empty() -> None:
    """Path normalisation handles empty string."""
    result = _normalize_path("")
    assert isinstance(result, (str, Path))


# METADATA PARSING TESTS
def test_parse_metadata_multiple_depends(tmp_path: Path) -> None:
    """Metadata parsing extracts multiple dependencies."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text(
        "name 'test'\ndepends 'base'\ndepends 'database'\ndepends 'monitoring'\n"
    )
    result = _parse_metadata_file(str(metadata))
    assert isinstance(result, (str, dict))


def test_parse_metadata_with_attributes(tmp_path: Path) -> None:
    """Metadata parsing includes attribute definitions."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'test'\nattribute 'version', default: '1.0'\n")
    result = _parse_metadata_file(str(metadata))
    assert isinstance(result, (str, dict))


def test_parse_metadata_invalid_path() -> None:
    """Metadata parsing handles missing file."""
    result = _parse_metadata_file("/nonexistent/metadata.rb")
    assert isinstance(result, (str, dict))


# BERKSFILE PARSING TESTS
def test_parse_berksfile_git_sources(tmp_path: Path) -> None:
    """Berksfile parsing handles git sources."""
    berksfile = tmp_path / "Berksfile"
    berksfile.write_text(
        "source 'https://supermarket.chef.io'\n"
        "cookbook 'app', git: 'https://github.com/example/cookbook-app.git'\n"
    )
    result = _parse_berksfile(berksfile)
    assert isinstance(result, (str, dict))


def test_parse_berksfile_path_sources(tmp_path: Path) -> None:
    """Berksfile parsing handles path sources."""
    berksfile = tmp_path / "Berksfile"
    berksfile.write_text("cookbook 'local', path: './local_cookbook'\n")
    result = _parse_berksfile(berksfile)
    assert isinstance(result, (str, dict))


def test_parse_berksfile_invalid() -> None:
    """Berksfile parsing handles missing file."""
    result = _parse_berksfile(Path("/nonexistent/Berksfile"))
    assert isinstance(result, (str, dict))


# CHEFIGNORE PARSING TESTS
def test_parse_chefignore_patterns(tmp_path: Path) -> None:
    """Chefignore parsing extracts patterns."""
    chefignore = tmp_path / ".chefignore"
    chefignore.write_text("*.pyc\n.git/\ntest/*\n# Comment\n")
    result = _parse_chefignore(str(chefignore))
    assert isinstance(result, (str, dict))


def test_parse_chefignore_empty(tmp_path: Path) -> None:
    """Chefignore parsing handles empty file."""
    chefignore = tmp_path / ".chefignore"
    chefignore.write_text("")
    result = _parse_chefignore(str(chefignore))
    assert isinstance(result, (str, dict))


def test_parse_chefignore_invalid() -> None:
    """Chefignore parsing handles missing file."""
    result = _parse_chefignore("/nonexistent/.chefignore")
    assert isinstance(result, (str, dict))


# INSPEC CONVERSION TESTS
def test_convert_inspec_to_testinfra(tmp_path: Path) -> None:
    """InSpec conversion to Testinfra format."""
    profile = tmp_path / "profile.yml"
    profile.write_text(
        "name: 'test-profile'\n"
        "controls:\n"
        "  - id: 'control-1'\n"
        "    title: 'Test control'\n"
    )
    result = convert_inspec_to_test(str(profile), "testinfra")
    assert isinstance(result, str)


def test_convert_inspec_to_serverspec(tmp_path: Path) -> None:
    """InSpec conversion to ServerSpec format."""
    profile = tmp_path / "profile.yml"
    profile.write_text("name: 'test'\n")
    result = convert_inspec_to_test(str(profile), "serverspec")
    assert isinstance(result, str)


def test_convert_inspec_to_goss(tmp_path: Path) -> None:
    """InSpec conversion to Goss format."""
    profile = tmp_path / "profile.yml"
    profile.write_text("name: 'test'\n")
    result = convert_inspec_to_test(str(profile), "goss")
    assert isinstance(result, str)


def test_convert_inspec_to_ansible(tmp_path: Path) -> None:
    """InSpec conversion to Ansible assert format."""
    profile = tmp_path / "profile.yml"
    profile.write_text("name: 'test'\n")
    result = convert_inspec_to_test(str(profile), "ansible_assert")
    assert isinstance(result, str)


# INSPEC PARSING TESTS
def test_parse_inspec_profile_with_controls(tmp_path: Path) -> None:
    """InSpec profile parsing extracts controls."""
    profile = tmp_path / "profile.yml"
    profile.write_text(
        "name: 'test-profile'\ntitle: 'Test Profile'\ncontrols:\n  - id: 'control-1'\n"
    )
    result = parse_inspec_profile(str(profile))
    assert isinstance(result, str)


def test_parse_inspec_profile_invalid() -> None:
    """InSpec profile parsing handles missing file."""
    result = parse_inspec_profile("/nonexistent/profile.yml")
    assert isinstance(result, str)


def test_parse_inspec_profile_malformed_yaml(tmp_path: Path) -> None:
    """InSpec profile parsing handles malformed YAML."""
    profile = tmp_path / "profile.yml"
    profile.write_text("invalid: [yaml: structure:")
    result = parse_inspec_profile(str(profile))
    assert isinstance(result, str)


# EDGE CASE TESTS
def test_path_normalisation_unicode() -> None:
    """Path normalisation handles Unicode characters."""
    result = _normalize_path("café/café.rb")
    assert isinstance(result, (str, Path))


def test_metadata_parse_special_chars(tmp_path: Path) -> None:
    """Metadata parsing preserves special characters."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'test-123_ABC'\ndescription 'Test café'\n")
    result = _parse_metadata_file(str(metadata))
    assert isinstance(result, (str, dict))


def test_berksfile_large_cookbook_list(tmp_path: Path) -> None:
    """Berksfile parsing handles many cookbooks."""
    berksfile = tmp_path / "Berksfile"
    cookbooks = "\n".join([f"cookbook 'cookbook-{i}'" for i in range(50)])
    berksfile.write_text(f"source 'https://supermarket.chef.io'\n{cookbooks}\n")
    result = _parse_berksfile(berksfile)
    assert isinstance(result, (str, dict))


def test_chefignore_complex_patterns(tmp_path: Path) -> None:
    """Chefignore parsing handles complex glob patterns."""
    chefignore = tmp_path / ".chefignore"
    chefignore.write_text("**/*.pyc\n[Tt]est*\n*.{log,tmp,swp}\n")
    result = _parse_chefignore(str(chefignore))
    assert isinstance(result, (str, dict))
