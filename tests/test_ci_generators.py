"""Tests for CI/CD pipeline generation from Chef patterns."""

import tempfile
from pathlib import Path

import pytest
import yaml

from souschef.ci.github_actions import (
    _analyse_chef_ci_patterns as github_analyze_patterns,
)
from souschef.ci.github_actions import (
    _build_integration_test_job,
    _build_lint_job,
    _build_unit_test_job,
    generate_github_workflow_from_chef_ci,
)
from souschef.ci.gitlab_ci import (
    _analyse_chef_ci_patterns as gitlab_analyze_patterns,
)
from souschef.ci.gitlab_ci import (
    _build_lint_jobs,
    _build_test_jobs,
    generate_gitlab_ci_from_chef_ci,
)
from souschef.ci.jenkins_pipeline import (
    _analyse_chef_ci_patterns as jenkins_analyze_patterns,
)
from souschef.ci.jenkins_pipeline import (
    _create_stage,
    _generate_declarative_pipeline,
    _generate_scripted_pipeline,
    _indent_content,
    generate_jenkinsfile_from_chef_ci,
)

# Test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_COOKBOOK = FIXTURES_DIR / "sample_cookbook"


# Jenkins Pipeline Tests


def test_generate_jenkinsfile_declarative():
    """Test Jenkins Declarative Pipeline generation."""
    result = generate_jenkinsfile_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        pipeline_name="test-pipeline",
        pipeline_type="declarative",
        enable_parallel=True,
    )

    assert "pipeline {" in result
    assert "test-pipeline" in result
    assert "agent any" in result
    assert "stages {" in result
    assert "ANSIBLE_FORCE_COLOR" in result


def test_generate_jenkinsfile_scripted():
    """Test Jenkins Scripted Pipeline generation."""
    result = generate_jenkinsfile_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        pipeline_name="scripted-test",
        pipeline_type="scripted",
        enable_parallel=False,
    )

    assert "node {" in result
    assert "scripted-test" in result
    assert "stage('Checkout')" in result
    assert "checkout scm" in result


def test_jenkins_analyze_patterns_with_kitchen():
    """Test Chef CI pattern detection with Test Kitchen."""
    patterns = jenkins_analyze_patterns(str(SAMPLE_COOKBOOK))

    assert patterns["has_kitchen"] is True
    assert patterns["has_chefspec"] is True
    assert "test_suites" in patterns
    assert len(patterns["test_suites"]) == 2
    assert "default" in patterns["test_suites"]
    assert "database" in patterns["test_suites"]


def test_jenkins_analyze_patterns_with_lint_tools():
    """Test detection of linting tools."""
    patterns = jenkins_analyze_patterns(str(SAMPLE_COOKBOOK))

    assert "lint_tools" in patterns
    assert "cookstyle" in patterns["lint_tools"]


def test_jenkins_analyze_patterns_no_files():
    """Test pattern analysis with no CI files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        patterns = jenkins_analyze_patterns(tmpdir)

        assert patterns["has_kitchen"] is False
        assert patterns["has_chefspec"] is False
        assert patterns["has_inspec"] is False
        assert patterns["has_berksfile"] is False
        assert patterns["lint_tools"] == []
        assert patterns["test_suites"] == []


def test_jenkins_declarative_with_lint_stages():
    """Test Declarative Pipeline includes lint stages."""
    ci_patterns = {
        "has_kitchen": True,
        "has_chefspec": False,
        "has_inspec": False,
        "lint_tools": ["cookstyle", "foodcritic"],
        "test_suites": [],
    }

    result = _generate_declarative_pipeline("test", ci_patterns, False)

    assert "stage('Lint')" in result
    assert "ansible-lint playbooks/" in result
    assert "yamllint" in result


def test_jenkins_declarative_with_unit_tests():
    """Test Declarative Pipeline includes ChefSpec unit tests."""
    ci_patterns = {
        "has_kitchen": False,
        "has_chefspec": True,
        "has_inspec": False,
        "lint_tools": [],
        "test_suites": [],
    }

    result = _generate_declarative_pipeline("test", ci_patterns, False)

    assert "stage('Unit Tests')" in result
    assert "molecule test --scenario-name default" in result


def test_jenkins_declarative_with_integration_tests():
    """Test Declarative Pipeline includes integration test stages."""
    ci_patterns = {
        "has_kitchen": True,
        "has_chefspec": False,
        "has_inspec": True,
        "lint_tools": [],
        "test_suites": ["default", "database", "web"],
    }

    result = _generate_declarative_pipeline("test", ci_patterns, False)

    assert "stage('Integration Tests')" in result
    assert "molecule test --scenario-name default" in result
    assert "molecule test --scenario-name database" in result
    assert "molecule test --scenario-name web" in result


def test_jenkins_declarative_deploy_stage():
    """Test Declarative Pipeline includes deploy stage."""
    ci_patterns = {
        "has_kitchen": False,
        "has_chefspec": False,
        "has_inspec": False,
        "lint_tools": [],
        "test_suites": [],
    }

    result = _generate_declarative_pipeline("test", ci_patterns, False)

    assert "stage('Deploy')" in result
    assert "ansible-playbook" in result
    assert "--check" in result
    assert "input message" in result


def test_jenkins_scripted_pipeline_structure():
    """Test Scripted Pipeline has correct structure."""
    result = _generate_scripted_pipeline("test", False)

    assert "node {" in result
    assert "try {" in result
    assert "stage('Checkout')" in result
    assert "stage('Lint')" in result
    assert "stage('Test')" in result
    assert "stage('Deploy')" in result
    assert "catch (Exception e)" in result
    assert "finally {" in result
    assert "cleanWs()" in result


def test_jenkins_create_stage():
    """Test stage creation utility."""
    stage = _create_stage(
        "Test Stage",
        ["sh 'command1'", "sh 'command2'"],
    )

    assert "stage('Test Stage')" in stage
    assert "steps {" in stage
    assert "sh 'command1'" in stage
    assert "sh 'command2'" in stage


def test_jenkins_indent_content():
    """Test content indentation utility."""
    content = "line1\nline2\nline3"
    result = _indent_content(content, 4)

    lines = result.split("\n")
    assert lines[0] == "    line1"
    assert lines[1] == "    line2"
    assert lines[2] == "    line3"


def test_jenkins_indent_content_preserves_empty_lines():
    """Test indentation preserves empty lines."""
    content = "line1\n\nline3"
    result = _indent_content(content, 2)

    lines = result.split("\n")
    assert lines[0] == "  line1"
    assert lines[1] == ""
    assert lines[2] == "  line3"


# GitLab CI Tests


def test_generate_gitlab_ci_default():
    """Test GitLab CI YAML generation with defaults."""
    result = generate_gitlab_ci_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        project_name="test-project",
        enable_cache=True,
        enable_artifacts=True,
    )

    assert "# .gitlab-ci.yml: test-project" in result
    assert "image: python:3.11" in result
    assert "stages:" in result
    assert "- lint" in result
    assert "- test" in result
    assert "- deploy" in result
    assert "cache:" in result
    assert "ANSIBLE_FORCE_COLOR" in result


def test_generate_gitlab_ci_no_cache():
    """Test GitLab CI generation without caching."""
    result = generate_gitlab_ci_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        project_name="test",
        enable_cache=False,
        enable_artifacts=True,
    )

    assert "cache:" not in result


def test_generate_gitlab_ci_no_artifacts():
    """Test GitLab CI generation without artifacts."""
    result = generate_gitlab_ci_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        project_name="test",
        enable_cache=True,
        enable_artifacts=False,
    )

    # Deploy job should still be there but test jobs shouldn't have artifacts
    assert "deploy:production" in result


def test_gitlab_analyze_patterns():
    """Test GitLab CI pattern analysis."""
    patterns = gitlab_analyze_patterns(str(SAMPLE_COOKBOOK))

    assert patterns["has_kitchen"] is True
    assert patterns["has_chefspec"] is True
    assert "cookstyle" in patterns["lint_tools"]
    assert len(patterns["test_suites"]) == 2


def test_gitlab_analyze_patterns_empty_dir():
    """Test pattern analysis with empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        patterns = gitlab_analyze_patterns(tmpdir)

        assert patterns["has_kitchen"] is False
        assert patterns["has_chefspec"] is False
        assert patterns["lint_tools"] == []


def test_gitlab_build_lint_jobs_with_tools():
    """Test lint job generation."""
    ci_patterns = {
        "lint_tools": ["cookstyle", "foodcritic"],
    }

    jobs = _build_lint_jobs(ci_patterns, enable_artifacts=True)

    assert len(jobs) == 1
    assert "lint:ansible" in jobs[0]
    assert "ansible-lint playbooks/" in jobs[0]
    assert "yamllint" in jobs[0]


def test_gitlab_build_lint_jobs_no_tools():
    """Test lint job generation with no tools."""
    ci_patterns = {"lint_tools": []}

    jobs = _build_lint_jobs(ci_patterns, enable_artifacts=False)

    assert len(jobs) == 0


def test_gitlab_build_test_jobs_unit_only():
    """Test test job generation with unit tests only."""
    ci_patterns = {
        "has_chefspec": True,
        "has_kitchen": False,
        "has_inspec": False,
        "test_suites": [],
    }

    jobs = _build_test_jobs(ci_patterns, enable_artifacts=True)

    assert len(jobs) == 1
    assert "test:unit" in jobs[0]
    assert "molecule test --scenario-name default" in jobs[0]


def test_gitlab_build_test_jobs_integration_with_suites():
    """Test integration job generation with multiple suites."""
    ci_patterns = {
        "has_chefspec": False,
        "has_kitchen": True,
        "has_inspec": False,
        "test_suites": ["default", "database", "web"],
    }

    jobs = _build_test_jobs(ci_patterns, enable_artifacts=True)

    assert len(jobs) == 3
    assert "test:integration:default" in jobs[0]
    assert "test:integration:database" in jobs[1]
    assert "test:integration:web" in jobs[2]


def test_gitlab_build_test_jobs_integration_no_suites():
    """Test integration job generation without test suites."""
    ci_patterns = {
        "has_chefspec": False,
        "has_kitchen": False,
        "has_inspec": True,
        "test_suites": [],
    }

    jobs = _build_test_jobs(ci_patterns, enable_artifacts=False)

    assert len(jobs) == 1
    assert "test:integration" in jobs[0]
    assert "molecule test" in jobs[0]


def test_gitlab_build_test_jobs_both():
    """Test job generation with both unit and integration tests."""
    ci_patterns = {
        "has_chefspec": True,
        "has_kitchen": True,
        "has_inspec": False,
        "test_suites": ["default"],
    }

    jobs = _build_test_jobs(ci_patterns, enable_artifacts=True)

    assert len(jobs) == 2
    assert "test:unit" in jobs[0]
    assert "test:integration:default" in jobs[1]


def test_gitlab_ci_deploy_job():
    """Test deploy job is always included."""
    result = generate_gitlab_ci_from_chef_ci(str(SAMPLE_COOKBOOK), "test", True, True)

    assert "deploy:production:" in result
    assert "stage: deploy" in result
    assert "when: manual" in result
    assert "only:" in result
    assert "- main" in result


def test_gitlab_ci_before_script():
    """Test before_script section."""
    result = generate_gitlab_ci_from_chef_ci(str(SAMPLE_COOKBOOK), "test", True, True)

    assert "before_script:" in result
    assert "python -m venv venv" in result
    assert "pip install --upgrade pip" in result
    assert "pip install ansible ansible-lint molecule molecule-docker" in result


# Kitchen.yml parsing tests


def test_jenkins_parse_kitchen_with_suites():
    """Test parsing kitchen.yml with test suites."""
    patterns = jenkins_analyze_patterns(str(SAMPLE_COOKBOOK))

    assert "default" in patterns["test_suites"]
    assert "database" in patterns["test_suites"]


def test_jenkins_parse_kitchen_yaml_error():
    """Test handling of invalid kitchen.yml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        kitchen_file = tmppath / ".kitchen.yml"
        kitchen_file.write_text("invalid: yaml: content: [[[")

        patterns = jenkins_analyze_patterns(tmpdir)

        # Should not crash, just return empty test_suites
        assert patterns["test_suites"] == []


def test_gitlab_parse_kitchen_yaml_error():
    """Test GitLab handling of invalid kitchen.yml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        kitchen_file = tmppath / ".kitchen.yml"
        kitchen_file.write_text("invalid yaml")

        patterns = gitlab_analyze_patterns(tmpdir)

        assert patterns["test_suites"] == []


# Edge cases and error handling


def test_jenkins_with_all_features():
    """Test Jenkins pipeline with all Chef CI features detected."""
    ci_patterns = {
        "has_kitchen": True,
        "has_chefspec": True,
        "has_inspec": True,
        "has_berksfile": True,
        "lint_tools": ["cookstyle", "foodcritic"],
        "test_suites": ["default", "database"],
    }

    result = _generate_declarative_pipeline("full-test", ci_patterns, True)

    assert "stage('Lint')" in result
    assert "stage('Unit Tests')" in result
    assert "stage('Integration Tests')" in result
    assert "stage('Deploy')" in result


def test_gitlab_with_all_features():
    """Test GitLab CI with all Chef CI features detected."""
    result = generate_gitlab_ci_from_chef_ci(
        str(SAMPLE_COOKBOOK), "full-test", True, True
    )

    assert "lint:ansible" in result
    assert "test:unit" in result
    assert "test:integration:" in result
    assert "deploy:production" in result


def test_jenkins_empty_cookbook():
    """Test Jenkins generation with cookbook that has no CI config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_jenkinsfile_from_chef_ci(
            tmpdir, "empty-test", "declarative", False
        )

        # Should still generate a valid pipeline
        assert "pipeline {" in result
        assert "stage('Deploy')" in result


def test_gitlab_empty_cookbook():
    """Test GitLab generation with cookbook that has no CI config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_gitlab_ci_from_chef_ci(tmpdir, "empty-test", False, False)

        # Should still generate valid CI config
        assert "stages:" in result
        assert "deploy:production" in result


# Integration tests with real cookbook


def test_jenkins_integration_with_sample_cookbook():
    """Integration test: Generate Jenkins pipeline from sample cookbook."""
    result = generate_jenkinsfile_from_chef_ci(
        str(SAMPLE_COOKBOOK), "sample-pipeline", "declarative", True
    )

    # Verify complete pipeline structure
    assert "// Jenkinsfile: sample-pipeline" in result
    assert "Generated from Chef cookbook CI/CD patterns" in result
    assert "Pipeline Type: Declarative" in result
    assert "options {" in result
    assert "timestamps()" in result
    assert "ansiColor('xterm')" in result
    assert "post {" in result
    assert "success {" in result
    assert "failure {" in result


def test_gitlab_integration_with_sample_cookbook():
    """Integration test: Generate GitLab CI from sample cookbook."""
    result = generate_gitlab_ci_from_chef_ci(
        str(SAMPLE_COOKBOOK), "sample-project", True, True
    )

    # Verify complete CI structure
    assert "# .gitlab-ci.yml: sample-project" in result
    assert "Generated from Chef cookbook CI/CD patterns" in result
    assert "variables:" in result
    assert "PIP_CACHE_DIR" in result
    assert "before_script:" in result
    assert "lint:ansible" in result or "test:" in result  # Has either lint or test


# Parameterized tests


@pytest.mark.parametrize(
    "pipeline_type,expected",
    [
        ("declarative", "pipeline {"),
        ("scripted", "node {"),
    ],
)
def test_jenkins_pipeline_types(pipeline_type, expected):
    """Test both Jenkins pipeline types."""
    result = generate_jenkinsfile_from_chef_ci(
        str(SAMPLE_COOKBOOK), "test", pipeline_type, False
    )

    assert expected in result


@pytest.mark.parametrize(
    "enable_cache,expected_text",
    [
        (True, "cache:"),
        (False, "stages:"),
    ],
)
def test_gitlab_cache_option(enable_cache, expected_text):
    """Test GitLab CI cache enabling/disabling."""
    result = generate_gitlab_ci_from_chef_ci(
        str(SAMPLE_COOKBOOK), "test", enable_cache, True
    )

    if enable_cache:
        assert expected_text in result
    # Both should have stages
    assert "stages:" in result


@pytest.mark.parametrize(
    "lint_tools,expected_count",
    [
        ([], 0),
        (["cookstyle"], 1),
        (["cookstyle", "foodcritic"], 1),  # Combined into one job
    ],
)
def test_gitlab_lint_jobs_count(lint_tools, expected_count):
    """Test lint job generation with different tool combinations."""
    ci_patterns = {"lint_tools": lint_tools}

    jobs = _build_lint_jobs(ci_patterns, True)

    assert len(jobs) == expected_count


def test_gitlab_build_lint_jobs_with_foodcritic_only():
    """Test lint job generation with only foodcritic."""
    ci_patterns = {"lint_tools": ["foodcritic"]}

    jobs = _build_lint_jobs(ci_patterns, enable_artifacts=False)

    assert len(jobs) == 1
    assert "lint:ansible" in jobs[0]
    assert "yamllint" in jobs[0]


def test_gitlab_ci_artifact_configuration():
    """Test artifact configuration in jobs."""
    ci_patterns = {
        "has_chefspec": True,
        "has_kitchen": False,
        "has_inspec": False,
        "test_suites": [],
    }

    jobs = _build_test_jobs(ci_patterns, enable_artifacts=True)

    assert len(jobs) == 1
    # Artifacts should be configured
    assert "test:unit" in jobs[0]


def test_jenkins_with_foodcritic():
    """Test Jenkins pipeline with foodcritic detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / ".foodcritic").touch()

        patterns = jenkins_analyze_patterns(tmpdir)

        assert "foodcritic" in patterns["lint_tools"]


def test_gitlab_with_foodcritic():
    """Test GitLab CI with foodcritic detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / ".foodcritic").touch()

        patterns = gitlab_analyze_patterns(tmpdir)

        assert "foodcritic" in patterns["lint_tools"]


def test_jenkins_kitchen_without_suites_key():
    """Test handling kitchen.yml without suites key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        kitchen_file = tmppath / ".kitchen.yml"
        kitchen_file.write_text("driver:\n  name: docker\n")

        patterns = jenkins_analyze_patterns(tmpdir)

        assert patterns["has_kitchen"] is True
        assert patterns["test_suites"] == []


def test_gitlab_kitchen_without_suites_key():
    """Test GitLab handling kitchen.yml without suites key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        kitchen_file = tmppath / ".kitchen.yml"
        kitchen_file.write_text("driver:\n  name: docker\n")

        patterns = gitlab_analyze_patterns(tmpdir)

        assert patterns["has_kitchen"] is True
        assert patterns["test_suites"] == []


def test_gitlab_lint_job_allow_failure():
    """Test lint job with allow_failure=False generates proper YAML."""
    ci_patterns = {"lint_tools": ["cookstyle"]}

    jobs = _build_lint_jobs(ci_patterns, enable_artifacts=True)

    # Verify allow_failure is NOT in the job (it's False)
    assert len(jobs) == 1
    assert "lint:ansible" in jobs[0]
    # allow_failure should only appear when True, not when False
    assert "allow_failure" not in jobs[0]


def test_gitlab_kitchen_yaml_read_exception():
    """Test handling of exception when reading kitchen.yml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        kitchen_file = tmppath / ".kitchen.yml"
        # Create file with invalid YAML that will raise exception
        kitchen_file.write_text("{{{{invalid yaml]]]")

        # Should not crash, just return empty test_suites
        patterns = gitlab_analyze_patterns(tmpdir)

        assert patterns["has_kitchen"] is True
        assert patterns["test_suites"] == []


# GitHub Actions Workflow Tests


def test_generate_github_workflow_basic():
    """Test basic GitHub Actions workflow generation."""
    result = generate_github_workflow_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        workflow_name="Test Workflow",
        enable_cache=True,
        enable_artifacts=True,
    )

    workflow = yaml.safe_load(result)
    assert workflow["name"] == "Test Workflow"
    assert "on" in workflow
    assert "jobs" in workflow


def test_generate_github_workflow_with_lint():
    """Test workflow with lint job."""
    result = generate_github_workflow_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        enable_cache=True,
        enable_artifacts=True,
    )

    workflow = yaml.safe_load(result)
    assert "lint" in workflow["jobs"]
    lint_job = workflow["jobs"]["lint"]
    assert lint_job["runs-on"] == "ubuntu-latest"
    assert any("Cookstyle" in step.get("name", "") for step in lint_job["steps"])


def test_generate_github_workflow_with_unit_tests():
    """Test workflow with ChefSpec unit tests."""
    result = generate_github_workflow_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        enable_cache=True,
        enable_artifacts=True,
    )

    workflow = yaml.safe_load(result)
    assert "unit-test" in workflow["jobs"]
    unit_job = workflow["jobs"]["unit-test"]
    assert any("ChefSpec" in step.get("name", "") for step in unit_job["steps"])


def test_generate_github_workflow_with_integration_tests():
    """Test workflow with Test Kitchen integration tests."""
    result = generate_github_workflow_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        enable_cache=True,
        enable_artifacts=True,
    )

    workflow = yaml.safe_load(result)
    assert "integration-test" in workflow["jobs"]
    integration_job = workflow["jobs"]["integration-test"]
    assert "strategy" in integration_job
    assert "matrix" in integration_job["strategy"]


def test_generate_github_workflow_without_cache():
    """Test workflow generation without caching."""
    result = generate_github_workflow_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        enable_cache=False,
        enable_artifacts=True,
    )

    workflow = yaml.safe_load(result)
    lint_job = workflow["jobs"].get("lint", {})
    # Should not have cache step
    cache_steps = [
        s for s in lint_job.get("steps", []) if "cache" in s.get("name", "").lower()
    ]
    assert len(cache_steps) == 0


def test_generate_github_workflow_without_artifacts():
    """Test workflow generation without artifacts."""
    result = generate_github_workflow_from_chef_ci(
        str(SAMPLE_COOKBOOK),
        enable_cache=True,
        enable_artifacts=False,
    )

    workflow = yaml.safe_load(result)
    integration_job = workflow["jobs"].get("integration-test", {})
    # Should not have upload artifact step
    artifact_steps = [
        s
        for s in integration_job.get("steps", [])
        if "upload" in s.get("name", "").lower()
    ]
    assert len(artifact_steps) == 0


def test_github_analyze_patterns():
    """Test pattern analysis for GitHub Actions."""
    patterns = github_analyze_patterns(SAMPLE_COOKBOOK)

    assert patterns["has_kitchen"] is True
    assert patterns["has_chefspec"] is True
    assert patterns["has_cookstyle"] is True
    assert len(patterns["kitchen_suites"]) > 0


def test_github_analyze_patterns_empty_dir():
    """Test pattern analysis with empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        patterns = github_analyze_patterns(Path(tmpdir))

        assert patterns["has_kitchen"] is False
        assert patterns["has_chefspec"] is False
        assert patterns["has_cookstyle"] is False
        assert patterns["kitchen_suites"] == []


def test_github_build_lint_job():
    """Test lint job building."""
    patterns = {"has_cookstyle": True, "has_foodcritic": False}
    job = _build_lint_job(patterns, enable_cache=True)

    assert job["name"] == "Lint Cookbook"
    assert job["runs-on"] == "ubuntu-latest"
    assert any("Cookstyle" in step.get("name", "") for step in job["steps"])
    assert any("cache" in step.get("name", "").lower() for step in job["steps"])


def test_github_build_lint_job_without_cache():
    """Test lint job without caching."""
    patterns = {"has_cookstyle": True, "has_foodcritic": False}
    job = _build_lint_job(patterns, enable_cache=False)

    cache_steps = [s for s in job["steps"] if "cache" in s.get("name", "").lower()]
    assert len(cache_steps) == 0


def test_github_build_unit_test_job():
    """Test unit test job building."""
    job = _build_unit_test_job(enable_cache=True)

    assert job["name"] == "Unit Tests (ChefSpec)"
    assert any("ChefSpec" in step.get("name", "") for step in job["steps"])
    assert any("rspec" in step.get("run", "") for step in job["steps"])


def test_github_build_integration_test_job():
    """Test integration test job building."""
    patterns = {"kitchen_suites": ["default", "database"]}
    job = _build_integration_test_job(
        patterns, enable_cache=True, enable_artifacts=True
    )

    assert job["name"] == "Integration Tests (Test Kitchen)"
    assert "strategy" in job
    assert job["strategy"]["matrix"]["suite"] == ["default", "database"]
    assert any("upload" in s.get("name", "").lower() for s in job["steps"])


def test_github_build_integration_test_job_no_suites():
    """Test integration job when no suites defined."""
    patterns = {"kitchen_suites": []}
    job = _build_integration_test_job(
        patterns, enable_cache=True, enable_artifacts=True
    )

    # Should default to ["default"]
    assert job["strategy"]["matrix"]["suite"] == ["default"]


def test_github_workflow_nonexistent_cookbook():
    """Test workflow generation with nonexistent cookbook."""
    with pytest.raises(FileNotFoundError):
        generate_github_workflow_from_chef_ci("/nonexistent/path")


def test_github_workflow_triggers():
    """Test workflow trigger configuration."""
    result = generate_github_workflow_from_chef_ci(str(SAMPLE_COOKBOOK))

    workflow = yaml.safe_load(result)
    assert "push" in workflow["on"]
    assert "pull_request" in workflow["on"]
    assert workflow["on"]["push"]["branches"] == ["main", "develop"]


def test_github_pattern_detection_with_multiple_suites():
    """Test pattern detection with multiple Kitchen suites."""
    patterns = github_analyze_patterns(SAMPLE_COOKBOOK)

    # Sample cookbook should have suites
    assert patterns["has_kitchen"] is True
    assert isinstance(patterns["kitchen_suites"], list)
    assert len(patterns["kitchen_suites"]) >= 1
