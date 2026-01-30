"""Tests for git functionality in repository generation."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.generators.repo import RepoType, generate_ansible_repository


class TestGitConfigFiles:
    """Test .gitattributes and .editorconfig generation."""

    def test_gitattributes_created(self, tmp_path):
        """Test that .gitattributes is created with appropriate content."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True

        gitattributes_file = output_dir / ".gitattributes"
        assert gitattributes_file.exists()

        content = gitattributes_file.read_text()
        # Check for key rules
        assert "* text=auto eol=lf" in content
        assert "*.yml text" in content
        assert "*.py text" in content
        assert "*.sh text eol=lf" in content

    def test_editorconfig_created(self, tmp_path):
        """Test that .editorconfig is created with appropriate settings."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.COLLECTION,
            init_git=False,
        )

        assert result["success"] is True

        editorconfig_file = output_dir / ".editorconfig"
        assert editorconfig_file.exists()

        content = editorconfig_file.read_text()
        # Check for key settings
        assert "root = true" in content
        assert "[*.{yml,yaml}]" in content
        assert "indent_size = 2" in content  # YAML 2-space indent
        assert "[*.py]" in content
        assert "indent_size = 4" in content  # Python 4-space indent
        assert "charset = utf-8" in content
        assert "end_of_line = lf" in content

    def test_config_files_in_all_repo_types(self, tmp_path):
        """Test that config files are created for all repository types."""
        for repo_type in RepoType:
            output_dir = tmp_path / f"test_repo_{repo_type.value}"

            result = generate_ansible_repository(
                output_path=str(output_dir),
                repo_type=repo_type,
                init_git=False,
            )

            assert result["success"] is True
            assert (output_dir / ".gitattributes").exists()
            assert (output_dir / ".editorconfig").exists()

    def test_config_files_included_in_file_list(self, tmp_path):
        """Test that config files appear in files_created list."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True
        assert ".gitattributes" in result["files_created"]
        assert ".editorconfig" in result["files_created"]


class TestGitCommitsForCopiedContent:
    """Test git commits for copied roles and playbooks."""

    def test_git_initialized_with_initial_commit(self, tmp_path):
        """Test that git is initialized with initial commit."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=True,
        )

        assert result["success"] is True

        if "initialised" in result.get("git_status", "").lower():
            # Check git directory exists
            assert (output_dir / ".git").exists()

            # Check initial commit exists
            try:
                log_result = subprocess.run(
                    ["git", "log", "--oneline"],
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert "Initial commit" in log_result.stdout
            except subprocess.CalledProcessError:
                pytest.skip("Git not available or repo not initialized")

    def test_git_config_files_are_committed(self, tmp_path):
        """Test that .gitattributes and .editorconfig are in initial commit."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=True,
        )

        assert result["success"] is True

        if "initialised" in result.get("git_status", "").lower():
            try:
                # Check files are tracked by git
                ls_files = subprocess.run(
                    ["git", "ls-files"],
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                tracked_files = ls_files.stdout
                assert ".gitattributes" in tracked_files
                assert ".editorconfig" in tracked_files
                assert ".gitignore" in tracked_files
            except subprocess.CalledProcessError:
                pytest.skip("Git not available")

    def test_working_directory_is_clean_after_generation(self, tmp_path):
        """Test that working directory is clean after repository generation."""
        output_dir = tmp_path / "test_repo"

        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type=RepoType.INVENTORY_FIRST,
            init_git=True,
        )

        assert result["success"] is True

        if "initialised" in result.get("git_status", "").lower():
            try:
                # Check git status
                status_result = subprocess.run(
                    ["git", "status", "--short"],
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                # Should be empty (clean working directory)
                assert status_result.stdout.strip() == ""
            except subprocess.CalledProcessError:
                pytest.skip("Git not available")


class TestZIPArchiveInclusion:
    """Test that config files are included in ZIP archives."""

    def test_config_files_included_in_zip(self, tmp_path):
        """Test that .gitattributes and .editorconfig are in ZIP."""
        import zipfile

        from souschef.ui.pages.cookbook_analysis import _create_repository_zip

        # Create test repository
        repo_path = tmp_path / "test_repo"
        result = generate_ansible_repository(
            output_path=str(repo_path),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True

        # Create ZIP
        zip_data = _create_repository_zip(str(repo_path))
        assert len(zip_data) > 0

        # Check ZIP contents
        import io

        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            file_list = zf.namelist()
            assert any(".gitattributes" in f for f in file_list)
            assert any(".editorconfig" in f for f in file_list)
            assert any(".gitignore" in f for f in file_list)

    def test_config_files_extract_correctly(self, tmp_path):
        """Test that config files extract with correct content."""
        import io
        import zipfile

        from souschef.ui.pages.cookbook_analysis import _create_repository_zip

        # Create test repository
        repo_path = tmp_path / "test_repo"
        result = generate_ansible_repository(
            output_path=str(repo_path),
            repo_type=RepoType.PLAYBOOKS_ROLES,
            init_git=False,
        )

        assert result["success"] is True

        # Create ZIP
        zip_data = _create_repository_zip(str(repo_path))

        # Extract to new location
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            zf.extractall(extract_dir)

        # Verify files exist and have content
        extracted_repo = extract_dir / "test_repo"
        gitattrs = extracted_repo / ".gitattributes"
        editorconf = extracted_repo / ".editorconfig"

        assert gitattrs.exists()
        assert editorconf.exists()
        assert gitattrs.stat().st_size > 0
        assert editorconf.stat().st_size > 0

        # Verify content is valid
        gitattrs_content = gitattrs.read_text()
        assert "* text=auto eol=lf" in gitattrs_content

        editorconf_content = editorconf.read_text()
        assert "root = true" in editorconf_content


class TestGitHelperFunction:
    """Test _get_git_path helper function."""

    def test_get_git_path_finds_git(self):
        """Test that _get_git_path can find git."""
        from souschef.ui.pages.cookbook_analysis import _get_git_path

        try:
            git_path = _get_git_path()
            assert git_path is not None
            assert isinstance(git_path, str)
            assert len(git_path) > 0
        except FileNotFoundError:
            pytest.skip("Git not available in test environment")

    def test_get_git_path_raises_on_missing_git(self):
        """Test that _get_git_path raises FileNotFoundError when git missing."""
        from souschef.ui.pages.cookbook_analysis import _get_git_path

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = FileNotFoundError("git not found")

            with pytest.raises(FileNotFoundError) as exc_info:
                _get_git_path()

            assert "git executable not found" in str(exc_info.value)
            assert "Git is installed" in str(exc_info.value)

    def test_get_git_path_checks_common_locations(self):
        """Test that _get_git_path checks common git locations."""
        from souschef.ui.pages.cookbook_analysis import _get_git_path

        with patch("pathlib.Path.exists") as mock_exists:
            # First call: /usr/bin/git exists
            mock_exists.return_value = True

            git_path = _get_git_path()

            # Should return one of the common paths
            assert git_path in [
                "/usr/bin/git",
                "/usr/local/bin/git",
                "/opt/homebrew/bin/git",
            ]

    def test_get_git_path_uses_which_fallback(self):
        """Test that _get_git_path falls back to 'which git'."""
        from souschef.ui.pages.cookbook_analysis import _get_git_path

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            # Simulate 'which git' returning a path
            mock_run.return_value.stdout = "/custom/path/to/git\n"
            mock_run.return_value.returncode = 0

            with patch("pathlib.Path.exists", side_effect=[False, False, False, True]):
                git_path = _get_git_path()
                assert git_path == "/custom/path/to/git"


class TestUIIntegrationWithGit:
    """Test UI integration functions with git functionality."""

    def test_create_ansible_repository_commits_roles(self, tmp_path):
        """Test that _create_ansible_repository commits copied roles."""
        from souschef.ui.pages.cookbook_analysis import _create_ansible_repository

        # Create mock output with roles
        output_path = tmp_path / "roles_output"
        output_path.mkdir()
        role_dir = output_path / "web_server"
        role_dir.mkdir()
        (role_dir / "tasks").mkdir()
        (role_dir / "tasks" / "main.yml").write_text("---\n- name: test\n")

        result = _create_ansible_repository(
            output_path=str(output_path), cookbook_path="", num_roles=1
        )

        assert result["success"] is True

        # Check git log if git was initialized
        temp_path = Path(result["temp_path"])
        if (temp_path / ".git").exists():
            try:
                log_result = subprocess.run(
                    ["git", "log", "--oneline"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commits = log_result.stdout.strip().split("\n")
                # Should have at least 2 commits: initial + roles
                assert len(commits) >= 2, f"Expected multiple commits, got: {commits}"
                assert any("role" in commit.lower() for commit in commits)
            except subprocess.CalledProcessError:
                pytest.skip("Git not available")
        else:
            pytest.skip("Git not initialized in repository")

        # Cleanup
        import shutil

        shutil.rmtree(temp_path, ignore_errors=True)

    def test_create_ansible_repository_no_untracked_files(self, tmp_path):
        """Test that repository has no untracked files after creation."""
        from souschef.ui.pages.cookbook_analysis import _create_ansible_repository

        output_path = tmp_path / "roles_output"
        output_path.mkdir()
        role_dir = output_path / "test_role"
        role_dir.mkdir()
        (role_dir / "tasks").mkdir()
        (role_dir / "tasks" / "main.yml").write_text("---\n- name: setup\n")

        result = _create_ansible_repository(
            output_path=str(output_path), cookbook_path="", num_roles=1
        )

        assert result["success"] is True

        temp_path = Path(result["temp_path"])
        if (temp_path / ".git").exists():
            try:
                status_result = subprocess.run(
                    ["git", "status", "--short"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                # Check for untracked files
                assert status_result.stdout.strip() == "", (
                    f"Found untracked files: {status_result.stdout}"
                )
            except subprocess.CalledProcessError:
                pytest.skip("Git not available")
        else:
            pytest.skip("Git not initialized")

        # Cleanup
        import shutil

        shutil.rmtree(temp_path, ignore_errors=True)


class TestDockerGitAvailability:
    """Test git availability in containerized environments."""

    def test_git_path_validation_in_subprocess(self):
        """Test that git can be found and executed."""
        from souschef.ui.pages.cookbook_analysis import _get_git_path

        try:
            git_path = _get_git_path()

            # Try to actually run git with the found path
            result = subprocess.run(
                [git_path, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )

            assert result.returncode == 0
            assert "git version" in result.stdout.lower()
        except FileNotFoundError:
            pytest.skip("Git not available")

    def test_create_repository_provides_helpful_error_when_git_missing(self, tmp_path):
        """Test that helpful error is provided when git is missing."""
        from souschef.ui.pages.cookbook_analysis import _create_ansible_repository

        output_path = tmp_path / "output"
        output_path.mkdir()

        with patch("souschef.ui.pages.cookbook_analysis._get_git_path") as mock_git:
            mock_git.side_effect = FileNotFoundError(
                "git executable not found. Please ensure Git is installed"
            )

            result = _create_ansible_repository(
                output_path=str(output_path), cookbook_path="", num_roles=1
            )

            assert result["success"] is False
            assert "git" in result["error"].lower()
