"""
Additional tests for souschef/ui/pages/bash_migration.py to reach 100% coverage.

Covers the render helpers for users, groups, file_perms, git_ops, archives,
sed_ops, cron_jobs, firewall_rules, hostname_ops, env_vars, sensitive_data,
cm_escapes, quality_score, aap_hints, _display_role_results, and the role
button paths in the paste/upload tabs.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest


class SessionState(dict):
    """Session state helper that supports attribute and dict access."""

    def __getattr__(self, name: str) -> Any:
        """Return item by attribute access."""
        if name in self:
            return self[name]
        raise AttributeError(f"No attribute {name}")

    def __setattr__(self, name: str, value: Any) -> None:
        """Store item via attribute access."""
        self[name] = value


def _ctx() -> MagicMock:
    """Create a context manager mock factory."""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=False)
    return mock


@pytest.fixture(autouse=True)
def mock_streamlit() -> Any:
    """Mock streamlit module so tests run without Streamlit installed."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        yield


# ---------------------------------------------------------------------------
# Paste tab – role button path (line 89)
# ---------------------------------------------------------------------------


class TestPasteTabRoleButton:
    """Tests for the role generation button in the paste tab."""

    def test_paste_tab_role_with_content(self) -> None:
        """Clicking Generate Ansible Role with content calls _display_role_results."""
        from souschef.ui.pages.bash_migration import _render_paste_tab

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration._display_role_results"
            ) as mock_role,
        ):
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.text_area.return_value = "#!/bin/bash\napt-get install nginx\n"
            mock_st.button.side_effect = [False, False, True]
            _render_paste_tab()
            mock_role.assert_called_once()

    def test_paste_tab_role_without_content_shows_warning(self) -> None:
        """Clicking Generate Ansible Role without content shows warning."""
        from souschef.ui.pages.bash_migration import _render_paste_tab

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.text_area.return_value = ""
            mock_st.button.side_effect = [False, False, True]
            _render_paste_tab()
            mock_st.warning.assert_called_once()


# ---------------------------------------------------------------------------
# Upload tab – role button path (line 123)
# ---------------------------------------------------------------------------


class TestUploadTabRoleButton:
    """Tests for the role generation button in the upload tab."""

    def test_upload_tab_role_uploaded_file(self) -> None:
        """Clicking Generate Role from Uploaded Script calls _display_role_results."""
        from souschef.ui.pages.bash_migration import _render_upload_tab

        fake_file = MagicMock()
        fake_file.read.return_value = b"#!/bin/bash\napt-get install nginx\n"
        fake_file.name = "deploy.sh"

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration._display_role_results"
            ) as mock_role,
        ):
            mock_st.file_uploader.return_value = fake_file
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.button.side_effect = [False, False, True]
            _render_upload_tab()
            mock_role.assert_called_once()


# ---------------------------------------------------------------------------
# _render_users
# ---------------------------------------------------------------------------


class TestRenderUsers:
    """Tests for the user management rendering helper."""

    def test_no_users_renders_nothing(self) -> None:
        """With no users, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_users

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_users({"users": []})
            mock_st.subheader.assert_not_called()

    def test_users_renders_expander(self) -> None:
        """With users, subheader and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_users

        ir = {
            "users": [
                {
                    "line": 5,
                    "action": "add",
                    "raw": "useradd deploy",
                    "confidence": 0.9,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_users(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_groups
# ---------------------------------------------------------------------------


class TestRenderGroups:
    """Tests for the group management rendering helper."""

    def test_no_groups_renders_nothing(self) -> None:
        """With no groups, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_groups

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_groups({"groups": []})
            mock_st.subheader.assert_not_called()

    def test_groups_renders_expander(self) -> None:
        """With groups, subheader and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_groups

        ir = {
            "groups": [
                {
                    "line": 6,
                    "action": "add",
                    "raw": "groupadd devs",
                    "confidence": 0.85,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_groups(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_file_perms
# ---------------------------------------------------------------------------


class TestRenderFilePerms:
    """Tests for the file permissions rendering helper."""

    def test_no_file_perms_renders_nothing(self) -> None:
        """With no file_perms, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_file_perms

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_file_perms({"file_perms": []})
            mock_st.subheader.assert_not_called()

    def test_file_perms_chmod_renders_mode(self) -> None:
        """Chmod entries show mode in expander label."""
        from souschef.ui.pages.bash_migration import _render_file_perms

        ir = {
            "file_perms": [
                {
                    "line": 7,
                    "op": "chmod",
                    "mode": "755",
                    "owner": "",
                    "path": "/usr/bin/app",
                    "recursive": False,
                    "raw": "chmod 755 /usr/bin/app",
                    "confidence": 0.95,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_file_perms(ir)
            mock_st.subheader.assert_called_once()

    def test_file_perms_chown_renders_owner(self) -> None:
        """Chown entries show owner in expander label."""
        from souschef.ui.pages.bash_migration import _render_file_perms

        ir = {
            "file_perms": [
                {
                    "line": 8,
                    "op": "chown",
                    "mode": "",
                    "owner": "root",
                    "path": "/etc/app",
                    "recursive": True,
                    "raw": "chown -R root /etc/app",
                    "confidence": 0.9,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_file_perms(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_git_ops
# ---------------------------------------------------------------------------


class TestRenderGitOps:
    """Tests for the git operations rendering helper."""

    def test_no_git_ops_renders_nothing(self) -> None:
        """With no git_ops, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_git_ops

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_git_ops({"git_ops": []})
            mock_st.subheader.assert_not_called()

    def test_git_ops_with_repo_renders_expander(self) -> None:
        """git_ops with repo uses repo as detail."""
        from souschef.ui.pages.bash_migration import _render_git_ops

        ir = {
            "git_ops": [
                {
                    "line": 9,
                    "action": "clone",
                    "repo": "https://github.com/example/repo",
                    "dest": "/opt/app",
                    "raw": "git clone https://github.com/example/repo /opt/app",
                    "confidence": 0.8,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_git_ops(ir)
            mock_st.subheader.assert_called_once()

    def test_git_ops_without_repo_uses_raw(self) -> None:
        """git_ops without repo uses raw[:40] as detail."""
        from souschef.ui.pages.bash_migration import _render_git_ops

        ir = {
            "git_ops": [
                {
                    "line": 10,
                    "action": "pull",
                    "repo": None,
                    "dest": None,
                    "raw": "git pull --rebase",
                    "confidence": 0.7,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_git_ops(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_archives
# ---------------------------------------------------------------------------


class TestRenderArchives:
    """Tests for the archive operations rendering helper."""

    def test_no_archives_renders_nothing(self) -> None:
        """With no archives, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_archives

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_archives({"archives": []})
            mock_st.subheader.assert_not_called()

    def test_archives_renders_expander(self) -> None:
        """With archives, subheader and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_archives

        ir = {
            "archives": [
                {
                    "line": 11,
                    "tool": "tar",
                    "source": "/tmp/app.tar.gz",
                    "raw": "tar -xzf /tmp/app.tar.gz -C /opt",
                    "confidence": 0.85,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_archives(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_sed_ops
# ---------------------------------------------------------------------------


class TestRenderSedOps:
    """Tests for the sed operations rendering helper."""

    def test_no_sed_ops_renders_nothing(self) -> None:
        """With no sed_ops, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_sed_ops

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_sed_ops({"sed_ops": []})
            mock_st.subheader.assert_not_called()

    def test_sed_ops_renders_expander(self) -> None:
        """With sed_ops, subheader and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_sed_ops

        ir = {
            "sed_ops": [
                {
                    "line": 12,
                    "raw": "sed -i 's/foo/bar/g' /etc/app.conf",
                    "ansible_module": "ansible.builtin.lineinfile",
                    "confidence": 0.75,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_sed_ops(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_cron_jobs
# ---------------------------------------------------------------------------


class TestRenderCronJobs:
    """Tests for the cron jobs rendering helper."""

    def test_no_cron_jobs_renders_nothing(self) -> None:
        """With no cron_jobs, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_cron_jobs

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_cron_jobs({"cron_jobs": []})
            mock_st.subheader.assert_not_called()

    def test_cron_jobs_renders_expander(self) -> None:
        """With cron_jobs, subheader and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_cron_jobs

        ir = {
            "cron_jobs": [
                {
                    "line": 13,
                    "raw": "(crontab -l ; echo '0 * * * * /usr/bin/backup') | crontab -",
                    "confidence": 0.7,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_cron_jobs(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_firewall_rules
# ---------------------------------------------------------------------------


class TestRenderFirewallRules:
    """Tests for the firewall rules rendering helper."""

    def test_no_firewall_rules_renders_nothing(self) -> None:
        """With no firewall_rules, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_firewall_rules

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_firewall_rules({"firewall_rules": []})
            mock_st.subheader.assert_not_called()

    def test_firewall_rules_renders_expander(self) -> None:
        """With firewall_rules, subheader and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_firewall_rules

        ir = {
            "firewall_rules": [
                {
                    "line": 14,
                    "tool": "ufw",
                    "ansible_module": "community.general.ufw",
                    "raw": "ufw allow 80/tcp",
                    "confidence": 0.9,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_firewall_rules(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_hostname_ops
# ---------------------------------------------------------------------------


class TestRenderHostnameOps:
    """Tests for the hostname operations rendering helper."""

    def test_no_hostname_ops_renders_nothing(self) -> None:
        """With no hostname_ops, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_hostname_ops

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_hostname_ops({"hostname_ops": []})
            mock_st.subheader.assert_not_called()

    def test_hostname_ops_renders_expander(self) -> None:
        """With hostname_ops, subheader and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_hostname_ops

        ir = {
            "hostname_ops": [
                {
                    "line": 15,
                    "hostname": "webserver-01",
                    "raw": "hostnamectl set-hostname webserver-01",
                    "confidence": 0.95,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_hostname_ops(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_env_vars
# ---------------------------------------------------------------------------


class TestRenderEnvVars:
    """Tests for the environment variables rendering helper."""

    def test_no_env_vars_renders_nothing(self) -> None:
        """With no env_vars, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_env_vars

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_env_vars({"env_vars": []})
            mock_st.subheader.assert_not_called()

    def test_env_vars_non_sensitive_renders_expander(self) -> None:
        """Non-sensitive env_vars render without warning."""
        from souschef.ui.pages.bash_migration import _render_env_vars

        ir = {
            "env_vars": [
                {
                    "line": 16,
                    "name": "APP_ENV",
                    "value": "production",
                    "is_sensitive": False,
                    "raw": "export APP_ENV=production",
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_env_vars(ir)
            mock_st.subheader.assert_called_once()

    def test_env_vars_sensitive_renders_warning(self) -> None:
        """Sensitive env_vars show warning label and inner warning."""
        from souschef.ui.pages.bash_migration import _render_env_vars

        ir = {
            "env_vars": [
                {
                    "line": 17,
                    "name": "DB_SECRET",
                    "value": "placeholder",
                    "is_sensitive": True,
                    "raw": "export DB_SECRET=placeholder",
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_env_vars(ir)
            mock_st.subheader.assert_called_once()
            mock_st.expander.assert_called_once()


# ---------------------------------------------------------------------------
# _render_sensitive_data
# ---------------------------------------------------------------------------


class TestRenderSensitiveData:
    """Tests for the sensitive data rendering helper."""

    def test_no_sensitive_data_renders_nothing(self) -> None:
        """With no sensitive_data, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_sensitive_data

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_sensitive_data({"sensitive_data": []})
            mock_st.subheader.assert_not_called()

    def test_sensitive_data_renders_error(self) -> None:
        """With sensitive_data, subheader and error are rendered."""
        from souschef.ui.pages.bash_migration import _render_sensitive_data

        ir = {
            "sensitive_data": [
                {
                    "line": 18,
                    "type": "aws_key",
                    "suggestion": "Use Ansible Vault to store this credential.",
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_sensitive_data(ir)
            mock_st.subheader.assert_called_once()
            mock_st.error.assert_called_once()


# ---------------------------------------------------------------------------
# _render_cm_escapes
# ---------------------------------------------------------------------------


class TestRenderCmEscapes:
    """Tests for the CM escapes rendering helper."""

    def test_no_cm_escapes_renders_nothing(self) -> None:
        """With no cm_escapes, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_cm_escapes

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_cm_escapes({"cm_escapes": []})
            mock_st.subheader.assert_not_called()

    def test_cm_escapes_renders_warning_and_expander(self) -> None:
        """With cm_escapes, subheader, warning, and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_cm_escapes

        ir = {
            "cm_escapes": [
                {
                    "line": 19,
                    "tool": "chef",
                    "suggestion": "Replace with native Ansible tasks.",
                    "raw": "chef-client --runlist 'recipe[nginx]'",
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_cm_escapes(ir)
            mock_st.subheader.assert_called_once()
            mock_st.warning.assert_called_once()


# ---------------------------------------------------------------------------
# _render_quality_score
# ---------------------------------------------------------------------------


class TestRenderQualityScore:
    """Tests for the quality score rendering helper."""

    def test_no_quality_score_renders_nothing(self) -> None:
        """With no quality_score, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_quality_score

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_quality_score({})
            mock_st.subheader.assert_not_called()

    def test_grade_na_renders_nothing(self) -> None:
        """quality_score with grade N/A renders nothing."""
        from souschef.ui.pages.bash_migration import _render_quality_score

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_quality_score({"quality_score": {"grade": "N/A"}})
            mock_st.subheader.assert_not_called()

    def test_grade_a_renders_success(self) -> None:
        """quality_score with grade A calls st.success."""
        from souschef.ui.pages.bash_migration import _render_quality_score

        data = {
            "quality_score": {
                "grade": "A",
                "coverage_pct": 95,
                "structured_operations": 10,
                "shell_fallbacks": 0,
                "improvements": [],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _render_quality_score(data)
            mock_st.success.assert_called_once()

    def test_grade_b_renders_info(self) -> None:
        """quality_score with grade B calls st.info."""
        from souschef.ui.pages.bash_migration import _render_quality_score

        data = {
            "quality_score": {
                "grade": "B",
                "coverage_pct": 80,
                "structured_operations": 8,
                "shell_fallbacks": 2,
                "improvements": ["Use idempotent tasks"],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _render_quality_score(data)
            mock_st.info.assert_called()

    def test_grade_c_renders_warning(self) -> None:
        """quality_score with grade C calls st.warning."""
        from souschef.ui.pages.bash_migration import _render_quality_score

        data = {
            "quality_score": {
                "grade": "C",
                "coverage_pct": 65,
                "structured_operations": 6,
                "shell_fallbacks": 4,
                "improvements": [],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _render_quality_score(data)
            mock_st.warning.assert_called()

    def test_grade_d_renders_warning(self) -> None:
        """quality_score with grade D calls st.warning."""
        from souschef.ui.pages.bash_migration import _render_quality_score

        data = {
            "quality_score": {
                "grade": "D",
                "coverage_pct": 50,
                "structured_operations": 4,
                "shell_fallbacks": 6,
                "improvements": [],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _render_quality_score(data)
            mock_st.warning.assert_called()

    def test_grade_f_renders_error(self) -> None:
        """quality_score with grade F calls st.error."""
        from souschef.ui.pages.bash_migration import _render_quality_score

        data = {
            "quality_score": {
                "grade": "F",
                "coverage_pct": 20,
                "structured_operations": 2,
                "shell_fallbacks": 8,
                "improvements": ["Add handlers"],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _render_quality_score(data)
            mock_st.error.assert_called()

    def test_unknown_grade_renders_write(self) -> None:
        """quality_score with unknown grade calls st.write (else branch)."""
        from souschef.ui.pages.bash_migration import _render_quality_score

        data = {
            "quality_score": {
                "grade": "X",
                "coverage_pct": 40,
                "structured_operations": 3,
                "shell_fallbacks": 5,
                "improvements": [],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _render_quality_score(data)
            mock_st.write.assert_called()


# ---------------------------------------------------------------------------
# _render_aap_hints
# ---------------------------------------------------------------------------


class TestRenderAapHints:
    """Tests for the AAP hints rendering helper."""

    def test_no_aap_hints_renders_nothing(self) -> None:
        """With no aap_hints, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_aap_hints

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_aap_hints({})
            mock_st.subheader.assert_not_called()

    def test_aap_hints_with_no_survey_no_notes(self) -> None:
        """AAP hints without survey variables or notes render normally."""
        from souschef.ui.pages.bash_migration import _render_aap_hints

        data = {
            "aap_hints": {
                "suggested_ee": "ee-minimal-rhel9:latest",
                "suggested_credentials": ["Machine Credential"],
                "become_enabled": True,
                "timeout": 3600,
                "survey_variables": [],
                "notes": [],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx())
            _render_aap_hints(data)
            mock_st.subheader.assert_called_once()

    def test_aap_hints_with_survey_variables(self) -> None:
        """AAP hints with survey_variables render survey section."""
        from souschef.ui.pages.bash_migration import _render_aap_hints

        data = {
            "aap_hints": {
                "suggested_ee": "ee-minimal-rhel9:latest",
                "suggested_credentials": [],
                "become_enabled": False,
                "timeout": 1800,
                "survey_variables": [
                    {
                        "name": "target_host",
                        "description": "Target host to deploy to",
                        "required": True,
                    }
                ],
                "notes": [],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx())
            _render_aap_hints(data)
            mock_st.info.assert_called()

    def test_aap_hints_with_notes(self) -> None:
        """AAP hints with notes render notes section."""
        from souschef.ui.pages.bash_migration import _render_aap_hints

        data = {
            "aap_hints": {
                "suggested_ee": "ee-minimal-rhel9:latest",
                "suggested_credentials": [],
                "become_enabled": True,
                "timeout": 3600,
                "survey_variables": [],
                "notes": ["Ensure SSH key is configured."],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx())
            _render_aap_hints(data)
            mock_st.warning.assert_called()

    def test_aap_hints_survey_variable_not_required(self) -> None:
        """Survey variable without required flag omits '(required)' tag."""
        from souschef.ui.pages.bash_migration import _render_aap_hints

        data = {
            "aap_hints": {
                "suggested_ee": "ee-minimal-rhel9:latest",
                "suggested_credentials": [],
                "become_enabled": True,
                "timeout": 3600,
                "survey_variables": [
                    {
                        "name": "extra_flag",
                        "description": "Optional extra flag",
                        "required": False,
                    }
                ],
                "notes": [],
            }
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx())
            _render_aap_hints(data)
            mock_st.info.assert_called()


# ---------------------------------------------------------------------------
# _display_conversion_results – JSON error path (line 482-487)
# ---------------------------------------------------------------------------


class TestDisplayConversionResultsJsonError:
    """Test JSON parse error path in _display_conversion_results."""

    def test_json_decode_error_shows_error(self) -> None:
        """When converter returns non-JSON, st.error is called."""
        from souschef.ui.pages.bash_migration import _display_conversion_results

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.convert_bash_content_to_ansible",
                return_value="not valid json!!!",
            ),
        ):
            _display_conversion_results("#!/bin/bash\necho hi\n")
            mock_st.error.assert_called_once()

    def test_conversion_with_quality_score_and_aap(self) -> None:
        """Conversion result with quality_score and aap_hints renders all sections."""
        import json

        from souschef.ui.pages.bash_migration import _display_conversion_results

        result = {
            "status": "ok",
            "playbook_yaml": "---\n- name: test\n  hosts: all\n",
            "warnings": ["Check idempotency."],
            "quality_score": {
                "grade": "B",
                "coverage_pct": 80,
                "structured_operations": 5,
                "shell_fallbacks": 1,
                "improvements": ["Use notify handlers"],
            },
            "aap_hints": {
                "suggested_ee": "ee-minimal-rhel9:latest",
                "suggested_credentials": ["Machine"],
                "become_enabled": True,
                "timeout": 3600,
                "survey_variables": [],
                "notes": [],
            },
            "idempotency_report": {
                "total_risks": 2,
                "non_idempotent_tasks": 1,
                "suggestions": ["Use state: present instead of raw commands"],
            },
        }
        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.convert_bash_content_to_ansible",
                return_value=json.dumps(result),
            ),
        ):
            mock_st.columns.side_effect = [
                (_ctx(), _ctx(), _ctx()),  # quality score
                (_ctx(), _ctx()),  # aap_hints
                (_ctx(), _ctx()),  # idempotency report
            ]
            _display_conversion_results("#!/bin/bash\napt-get install nginx\n")
            mock_st.subheader.assert_called()

    def test_conversion_with_idempotency_suggestions(self) -> None:
        """Idempotency report with suggestions renders them."""
        import json

        from souschef.ui.pages.bash_migration import _display_conversion_results

        result = {
            "status": "ok",
            "playbook_yaml": "---\n",
            "warnings": [],
            "idempotency_report": {
                "total_risks": 1,
                "non_idempotent_tasks": 1,
                "suggestions": ["Use creates: flag for file conditions"],
            },
        }
        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.convert_bash_content_to_ansible",
                return_value=json.dumps(result),
            ),
        ):
            mock_st.columns.return_value = (_ctx(), _ctx())
            _display_conversion_results("any script")
            mock_st.info.assert_called()


# ---------------------------------------------------------------------------
# _display_role_results
# ---------------------------------------------------------------------------


class TestDisplayRoleResults:
    """Tests for the role generation display function."""

    def test_role_json_decode_error_shows_error(self) -> None:
        """When role generator returns non-JSON, st.error is called."""
        from souschef.ui.pages.bash_migration import _display_role_results

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.generate_ansible_role_from_bash",
                return_value="not valid json!!!",
            ),
        ):
            _display_role_results("#!/bin/bash\necho hi\n")
            mock_st.error.assert_called_once()

    def test_role_error_status_shows_error(self) -> None:
        """When role generator returns error status, st.error is called."""
        import json

        from souschef.ui.pages.bash_migration import _display_role_results

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.generate_ansible_role_from_bash",
                return_value=json.dumps({"status": "error", "error": "Bad input"}),
            ),
        ):
            _display_role_results("bad script")
            mock_st.error.assert_called_once()

    def test_role_success_renders_files(self) -> None:
        """Successful role generation renders file expanders."""
        import json

        from souschef.ui.pages.bash_migration import _display_role_results

        result = {
            "status": "ok",
            "role_name": "bash_converted",
            "files": {
                "tasks/main.yml": "---\n- name: Install nginx\n  apt:\n    name: nginx\n",
                "README.md": "# Role README\n",
            },
        }
        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.generate_ansible_role_from_bash",
                return_value=json.dumps(result),
            ),
        ):
            mock_st.expander.return_value = _ctx()
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _display_role_results("#!/bin/bash\napt-get install nginx\n")
            mock_st.subheader.assert_called()
            mock_st.expander.assert_called()

    def test_role_success_with_quality_score_and_aap(self) -> None:
        """Role with quality_score and aap_hints renders extra sections."""
        import json

        from souschef.ui.pages.bash_migration import _display_role_results

        result = {
            "status": "ok",
            "role_name": "bash_converted",
            "files": {},
            "quality_score": {
                "grade": "A",
                "coverage_pct": 100,
                "structured_operations": 5,
                "shell_fallbacks": 0,
                "improvements": [],
            },
            "aap_hints": {
                "suggested_ee": "ee-minimal-rhel9:latest",
                "suggested_credentials": [],
                "become_enabled": True,
                "timeout": 3600,
                "survey_variables": [],
                "notes": [],
            },
        }
        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.generate_ansible_role_from_bash",
                return_value=json.dumps(result),
            ),
        ):
            mock_st.columns.side_effect = [
                (_ctx(), _ctx(), _ctx()),  # quality score
                (_ctx(), _ctx()),  # aap_hints
            ]
            _display_role_results("#!/bin/bash\napt-get install nginx\n")
            mock_st.subheader.assert_called()
