"""
Unit tests for the enterprise action-type classifiers added to souschef/parsers/powershell.py.

Covers:
- User management  (user_create, user_modify, user_remove,
                    group_member_add, group_member_remove)
- Firewall rules   (firewall_rule_create, firewall_rule_enable,
                    firewall_rule_disable, firewall_rule_remove)
- Scheduled tasks  (scheduled_task_register, scheduled_task_unregister)
- Environment vars (environment_set  – both Set-Item and ::SetEnvironmentVariable)
- PS modules       (psmodule_install)
- Certificates     (certificate_import)
- WinRM            (winrm_enable)
- IIS              (iis_website_create)
- DNS              (dns_client_set)
- ACL              (acl_set)
"""

from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _actions(script: str) -> list[dict]:
    """Parse *script* and return the actions list."""
    from souschef.parsers.powershell import parse_powershell_content

    return json.loads(parse_powershell_content(script))["actions"]


def _single(script: str) -> dict:
    """Return the first (and expected-only) action for *script*."""
    acts = _actions(script)
    assert len(acts) == 1, f"Expected 1 action, got {len(acts)}: {acts}"
    return acts[0]


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


class TestUserCreate:
    """Tests for the user_create action type (New-LocalUser)."""

    def test_basic_new_local_user(self) -> None:
        """New-LocalUser produces a user_create action with the username."""
        action = _single("New-LocalUser -Name deploy_svc\n")
        assert action["action_type"] == "user_create"
        assert action["params"]["username"] == "deploy_svc"

    def test_new_local_user_quoted_name(self) -> None:
        """New-LocalUser with a quoted username is parsed correctly."""
        action = _single("New-LocalUser 'app-user'\n")
        assert action["action_type"] == "user_create"
        assert action["params"]["username"] == "app-user"

    def test_new_local_user_double_quoted(self) -> None:
        """New-LocalUser with a double-quoted username is parsed correctly."""
        action = _single('New-LocalUser "svc.account"\n')
        assert action["action_type"] == "user_create"
        assert action["params"]["username"] == "svc.account"

    def test_new_local_user_case_insensitive(self) -> None:
        """new-localuser (lower-case) still produces user_create."""
        action = _single("new-localuser -name ADMIN2\n")
        assert action["action_type"] == "user_create"
        assert action["params"]["username"] == "ADMIN2"

    def test_new_local_user_source_line_recorded(self) -> None:
        """source_line is recorded for user_create actions."""
        action = _single("New-LocalUser -Name testuser\n")
        assert action["source_line"] == 1


class TestUserModify:
    """Tests for the user_modify action type (Set-LocalUser)."""

    def test_basic_set_local_user(self) -> None:
        """Set-LocalUser produces a user_modify action."""
        action = _single("Set-LocalUser -Name deploy_svc\n")
        assert action["action_type"] == "user_modify"
        assert action["params"]["username"] == "deploy_svc"

    def test_set_local_user_no_flag(self) -> None:
        """Set-LocalUser without -Name flag still captures the username."""
        action = _single("Set-LocalUser app_user\n")
        assert action["action_type"] == "user_modify"
        assert action["params"]["username"] == "app_user"

    def test_set_local_user_with_extra_params(self) -> None:
        """Set-LocalUser with additional parameters is still classified."""
        action = _single("Set-LocalUser -Name svc -PasswordNeverExpires $true\n")
        assert action["action_type"] == "user_modify"
        assert action["params"]["username"] == "svc"


class TestUserRemove:
    """Tests for the user_remove action type (Remove-LocalUser)."""

    def test_basic_remove_local_user(self) -> None:
        """Remove-LocalUser produces a user_remove action."""
        action = _single("Remove-LocalUser -Name olduser\n")
        assert action["action_type"] == "user_remove"
        assert action["params"]["username"] == "olduser"

    def test_remove_local_user_quoted(self) -> None:
        """Remove-LocalUser with quoted name is parsed correctly."""
        action = _single("Remove-LocalUser 'temp.account'\n")
        assert action["action_type"] == "user_remove"
        assert action["params"]["username"] == "temp.account"

    def test_remove_local_user_uppercase(self) -> None:
        """REMOVE-LOCALUSER (upper-case) is still classified correctly."""
        action = _single("REMOVE-LOCALUSER -NAME TESTUSER\n")
        assert action["action_type"] == "user_remove"


class TestGroupMemberAdd:
    """Tests for the group_member_add action type (Add-LocalGroupMember)."""

    def test_basic_add_local_group_member(self) -> None:
        """Add-LocalGroupMember produces a group_member_add action."""
        action = _single(
            "Add-LocalGroupMember -Group Administrators -Member deploy_svc\n"
        )
        assert action["action_type"] == "group_member_add"
        assert action["params"]["group"] == "Administrators"
        assert action["params"]["member"] == "deploy_svc"

    def test_add_local_group_member_no_flags(self) -> None:
        """Add-LocalGroupMember without explicit -Member flag falls back to win_shell."""
        action = _single("Add-LocalGroupMember Administrators deploy_svc\n")
        assert action["action_type"] == "win_shell"

    def test_add_local_group_member_case_insensitive(self) -> None:
        """add-localgroupmember (lower-case) is still classified."""
        action = _single("add-localgroupmember -group Admins -member svc\n")
        assert action["action_type"] == "group_member_add"

    def test_add_local_group_member_source_line(self) -> None:
        """source_line is recorded for group_member_add actions."""
        action = _single("Add-LocalGroupMember -Group Admins -Member bob\n")
        assert action["source_line"] == 1


class TestGroupMemberRemove:
    """Tests for the group_member_remove action type (Remove-LocalGroupMember)."""

    def test_basic_remove_local_group_member(self) -> None:
        """Remove-LocalGroupMember produces a group_member_remove action."""
        action = _single(
            "Remove-LocalGroupMember -Group Administrators -Member deploy_svc\n"
        )
        assert action["action_type"] == "group_member_remove"
        assert action["params"]["group"] == "Administrators"
        assert action["params"]["member"] == "deploy_svc"

    def test_remove_local_group_member_no_flags(self) -> None:
        """Remove-LocalGroupMember without explicit -Member flag falls back to win_shell."""
        action = _single("Remove-LocalGroupMember Administrators olduser\n")
        assert action["action_type"] == "win_shell"

    def test_remove_local_group_member_case_insensitive(self) -> None:
        """remove-localgroupmember (lower-case) is still classified."""
        action = _single("remove-localgroupmember -group Users -member bob\n")
        assert action["action_type"] == "group_member_remove"


# ---------------------------------------------------------------------------
# Firewall rules
# ---------------------------------------------------------------------------


class TestFirewallRuleCreate:
    """Tests for the firewall_rule_create action type (New-NetFirewallRule)."""

    def test_basic_new_net_firewall_rule(self) -> None:
        """New-NetFirewallRule produces a firewall_rule_create action."""
        action = _single('New-NetFirewallRule -DisplayName "Allow HTTP"\n')
        assert action["action_type"] == "firewall_rule_create"
        assert "Allow HTTP" in action["params"]["rule_name"]

    def test_new_net_firewall_rule_name_flag(self) -> None:
        """New-NetFirewallRule with -Name flag is classified."""
        action = _single("New-NetFirewallRule -Name Allow-RDP\n")
        assert action["action_type"] == "firewall_rule_create"
        assert "Allow-RDP" in action["params"]["rule_name"]

    def test_new_net_firewall_rule_case_insensitive(self) -> None:
        """new-netfirewallrule (lower-case) is still classified."""
        action = _single("new-netfirewallrule -displayname TestRule\n")
        assert action["action_type"] == "firewall_rule_create"

    def test_new_net_firewall_rule_source_line(self) -> None:
        """source_line is recorded for firewall_rule_create actions."""
        action = _single("New-NetFirewallRule -DisplayName MyRule\n")
        assert action["source_line"] == 1


class TestFirewallRuleEnable:
    """Tests for the firewall_rule_enable action type (Enable-NetFirewallRule)."""

    def test_basic_enable_net_firewall_rule(self) -> None:
        """Enable-NetFirewallRule produces a firewall_rule_enable action."""
        action = _single("Enable-NetFirewallRule -DisplayName Allow-HTTP\n")
        assert action["action_type"] == "firewall_rule_enable"
        assert "Allow-HTTP" in action["params"]["rule_name"]

    def test_enable_net_firewall_rule_quoted(self) -> None:
        """Enable-NetFirewallRule with quoted name is parsed correctly."""
        action = _single('Enable-NetFirewallRule -Name "Allow RDP"\n')
        assert action["action_type"] == "firewall_rule_enable"

    def test_enable_net_firewall_rule_case_insensitive(self) -> None:
        """enable-netfirewallrule (lower-case) is still classified."""
        action = _single("enable-netfirewallrule -name testrule\n")
        assert action["action_type"] == "firewall_rule_enable"


class TestFirewallRuleDisable:
    """Tests for the firewall_rule_disable action type (Disable-NetFirewallRule)."""

    def test_basic_disable_net_firewall_rule(self) -> None:
        """Disable-NetFirewallRule produces a firewall_rule_disable action."""
        action = _single("Disable-NetFirewallRule -DisplayName Block-Telnet\n")
        assert action["action_type"] == "firewall_rule_disable"
        assert "Block-Telnet" in action["params"]["rule_name"]

    def test_disable_net_firewall_rule_quoted(self) -> None:
        """Disable-NetFirewallRule with quoted name is parsed correctly."""
        action = _single('Disable-NetFirewallRule -Name "Block All Outbound"\n')
        assert action["action_type"] == "firewall_rule_disable"

    def test_disable_net_firewall_rule_case_insensitive(self) -> None:
        """disable-netfirewallrule (lower-case) is still classified."""
        action = _single("disable-netfirewallrule -name testrule\n")
        assert action["action_type"] == "firewall_rule_disable"


class TestFirewallRuleRemove:
    """Tests for the firewall_rule_remove action type (Remove-NetFirewallRule)."""

    def test_basic_remove_net_firewall_rule(self) -> None:
        """Remove-NetFirewallRule produces a firewall_rule_remove action."""
        action = _single("Remove-NetFirewallRule -DisplayName OldRule\n")
        assert action["action_type"] == "firewall_rule_remove"
        assert "OldRule" in action["params"]["rule_name"]

    def test_remove_net_firewall_rule_name_flag(self) -> None:
        """Remove-NetFirewallRule with -Name flag is classified."""
        action = _single("Remove-NetFirewallRule -Name Allow-SMB\n")
        assert action["action_type"] == "firewall_rule_remove"

    def test_remove_net_firewall_rule_case_insensitive(self) -> None:
        """remove-netfirewallrule (lower-case) is still classified."""
        action = _single("remove-netfirewallrule -displayname testrule\n")
        assert action["action_type"] == "firewall_rule_remove"


# ---------------------------------------------------------------------------
# Scheduled tasks
# ---------------------------------------------------------------------------


class TestScheduledTaskRegister:
    """Tests for the scheduled_task_register action type (Register-ScheduledTask)."""

    def test_basic_register_scheduled_task(self) -> None:
        """Register-ScheduledTask produces a scheduled_task_register action."""
        action = _single("Register-ScheduledTask -TaskName DailyBackup\n")
        assert action["action_type"] == "scheduled_task_register"
        assert "DailyBackup" in action["params"]["task_name"]

    def test_register_scheduled_task_quoted(self) -> None:
        """Register-ScheduledTask with a quoted name is parsed correctly."""
        action = _single('Register-ScheduledTask "Nightly Cleanup"\n')
        assert action["action_type"] == "scheduled_task_register"

    def test_register_scheduled_task_case_insensitive(self) -> None:
        """register-scheduledtask (lower-case) is still classified."""
        action = _single("register-scheduledtask -taskname mytask\n")
        assert action["action_type"] == "scheduled_task_register"

    def test_register_scheduled_task_source_line(self) -> None:
        """source_line is recorded for scheduled_task_register actions."""
        action = _single("Register-ScheduledTask -TaskName MyTask\n")
        assert action["source_line"] == 1


class TestScheduledTaskUnregister:
    """Tests for the scheduled_task_unregister action type (Unregister-ScheduledTask)."""

    def test_basic_unregister_scheduled_task(self) -> None:
        """Unregister-ScheduledTask produces a scheduled_task_unregister action."""
        action = _single("Unregister-ScheduledTask -TaskName DailyBackup\n")
        assert action["action_type"] == "scheduled_task_unregister"
        assert "DailyBackup" in action["params"]["task_name"]

    def test_unregister_scheduled_task_quoted(self) -> None:
        """Unregister-ScheduledTask with a quoted name is parsed correctly."""
        action = _single('Unregister-ScheduledTask "Old Cleanup"\n')
        assert action["action_type"] == "scheduled_task_unregister"

    def test_unregister_scheduled_task_case_insensitive(self) -> None:
        """unregister-scheduledtask (lower-case) is still classified."""
        action = _single("unregister-scheduledtask -taskname mytask\n")
        assert action["action_type"] == "scheduled_task_unregister"


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------


class TestEnvironmentSet:
    """Tests for the environment_set action type."""

    def test_set_environment_variable_system_api(self) -> None:
        """[System.Environment]::SetEnvironmentVariable produces environment_set."""
        action = _single(
            "[System.Environment]::SetEnvironmentVariable('MY_VAR', 'hello')\n"
        )
        assert action["action_type"] == "environment_set"
        assert action["params"]["name"] == "MY_VAR"
        assert "hello" in action["params"]["value"]

    def test_set_environment_variable_environment_api(self) -> None:
        """[Environment]::SetEnvironmentVariable (short form) produces environment_set."""
        action = _single(
            "[Environment]::SetEnvironmentVariable('APP_HOME', 'C:\\\\app')\n"
        )
        assert action["action_type"] == "environment_set"
        assert action["params"]["name"] == "APP_HOME"

    def test_set_item_env_colon(self) -> None:
        """Set-Item Env:VAR produces environment_set."""
        action = _single("Set-Item Env:MY_PATH 'C:\\\\tools'\n")
        assert action["action_type"] == "environment_set"
        assert action["params"]["name"] == "MY_PATH"

    def test_set_item_env_lowercase(self) -> None:
        """Set-Item env:VAR (lower-case prefix) produces environment_set."""
        action = _single("Set-Item env:MY_VAR myvalue\n")
        assert action["action_type"] == "environment_set"
        assert action["params"]["name"] == "MY_VAR"

    def test_environment_set_case_insensitive_api(self) -> None:
        """SetEnvironmentVariable is matched case-insensitively."""
        action = _single("[system.environment]::setenvironmentvariable('X', 'y')\n")
        assert action["action_type"] == "environment_set"


# ---------------------------------------------------------------------------
# PowerShell modules
# ---------------------------------------------------------------------------


class TestPsModuleInstall:
    """Tests for the psmodule_install action type (Install-Module)."""

    def test_basic_install_module(self) -> None:
        """Install-Module produces a psmodule_install action."""
        action = _single("Install-Module -Name PSWindowsUpdate\n")
        assert action["action_type"] == "psmodule_install"
        assert action["params"]["module_name"] == "PSWindowsUpdate"

    def test_install_module_no_flag(self) -> None:
        """Install-Module without -Name flag still captures the module name."""
        action = _single("Install-Module AzureAD\n")
        assert action["action_type"] == "psmodule_install"
        assert action["params"]["module_name"] == "AzureAD"

    def test_install_module_case_insensitive(self) -> None:
        """install-module (lower-case) is still classified."""
        action = _single("install-module -name mymodule\n")
        assert action["action_type"] == "psmodule_install"

    def test_install_module_dotted_name(self) -> None:
        """Install-Module with a dotted module name is parsed correctly."""
        action = _single("Install-Module -Name Az.Accounts\n")
        assert action["action_type"] == "psmodule_install"
        assert action["params"]["module_name"] == "Az.Accounts"


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------


class TestCertificateImport:
    """Tests for the certificate_import action type (Import-Certificate)."""

    def test_import_certificate_cer(self) -> None:
        """Import-Certificate for a .cer file produces certificate_import."""
        action = _single("Import-Certificate -FilePath C:\\\\certs\\\\server.cer\n")
        assert action["action_type"] == "certificate_import"
        assert action["params"]["certificate_path"].endswith(".cer")

    def test_import_pfx_certificate(self) -> None:
        """Import-PfxCertificate produces a certificate_import action."""
        action = _single("Import-PfxCertificate -FilePath C:\\\\certs\\\\server.pfx\n")
        assert action["action_type"] == "certificate_import"
        assert action["params"]["certificate_path"].endswith(".pfx")

    def test_import_certificate_p12(self) -> None:
        """Import-PfxCertificate for a .p12 file is classified."""
        action = _single("Import-PfxCertificate -FilePath /tmp/cert.p12\n")
        assert action["action_type"] == "certificate_import"
        assert action["params"]["certificate_path"].endswith(".p12")

    def test_import_certificate_case_insensitive(self) -> None:
        """import-certificate (lower-case) is still classified."""
        action = _single("import-certificate -filepath C:\\\\certs\\\\ca.cer\n")
        assert action["action_type"] == "certificate_import"


# ---------------------------------------------------------------------------
# WinRM
# ---------------------------------------------------------------------------


class TestWinrmEnable:
    """Tests for the winrm_enable action type (Enable-PSRemoting)."""

    def test_enable_psremoting(self) -> None:
        """Enable-PSRemoting produces a winrm_enable action."""
        action = _single("Enable-PSRemoting -Force\n")
        assert action["action_type"] == "winrm_enable"

    def test_enable_psremoting_case_insensitive(self) -> None:
        """enable-psremoting (lower-case) is still classified."""
        action = _single("enable-psremoting -force\n")
        assert action["action_type"] == "winrm_enable"

    def test_winrm_quickconfig(self) -> None:
        """Winrm quickconfig produces a winrm_enable action."""
        action = _single("winrm quickconfig -q\n")
        assert action["action_type"] == "winrm_enable"

    def test_winrm_enable_records_raw_command(self) -> None:
        """winrm_enable records the raw command in params."""
        action = _single("Enable-PSRemoting -Force\n")
        assert "raw_command" in action["params"]


# ---------------------------------------------------------------------------
# IIS
# ---------------------------------------------------------------------------


class TestIisWebsiteCreate:
    """Tests for the iis_website_create action type (New-WebSite)."""

    def test_basic_new_website(self) -> None:
        """New-WebSite produces an iis_website_create action."""
        action = _single("New-WebSite -Name DefaultSite\n")
        assert action["action_type"] == "iis_website_create"
        assert "DefaultSite" in action["params"]["site_name"]

    def test_new_website_quoted(self) -> None:
        """New-WebSite with a quoted name is parsed correctly."""
        action = _single('New-WebSite "My Application"\n')
        assert action["action_type"] == "iis_website_create"

    def test_new_website_case_insensitive(self) -> None:
        """new-website (lower-case) is still classified."""
        action = _single("new-website -name testsite\n")
        assert action["action_type"] == "iis_website_create"

    def test_new_website_source_line(self) -> None:
        """source_line is recorded for iis_website_create actions."""
        action = _single("New-WebSite -Name MySite\n")
        assert action["source_line"] == 1


# ---------------------------------------------------------------------------
# DNS
# ---------------------------------------------------------------------------


class TestDnsClientSet:
    """Tests for the dns_client_set action type (Set-DnsClientServerAddress)."""

    def test_basic_set_dns_client_server_address(self) -> None:
        """Set-DnsClientServerAddress produces a dns_client_set action."""
        action = _single(
            "Set-DnsClientServerAddress -InterfaceAlias Ethernet -ServerAddresses 8.8.8.8\n"
        )
        assert action["action_type"] == "dns_client_set"
        assert "8.8.8.8" in action["params"]["server_addresses"]

    def test_set_dns_client_multiple_addresses(self) -> None:
        """Set-DnsClientServerAddress with multiple IPs is parsed."""
        action = _single(
            "Set-DnsClientServerAddress -InterfaceIndex 5 -ServerAddresses 1.1.1.1,8.8.8.8\n"
        )
        assert action["action_type"] == "dns_client_set"

    def test_set_dns_client_case_insensitive(self) -> None:
        """set-dnsclientserveraddress (lower-case) is still classified."""
        action = _single(
            "set-dnsclientserveraddress -interfacealias eth0 -serveraddresses 9.9.9.9\n"
        )
        assert action["action_type"] == "dns_client_set"


# ---------------------------------------------------------------------------
# ACL
# ---------------------------------------------------------------------------


class TestAclSet:
    """Tests for the acl_set action type (Set-Acl / icacls)."""

    def test_basic_set_acl(self) -> None:
        """Set-Acl produces an acl_set action."""
        action = _single("Set-Acl C:\\\\app\\\\data $acl\n")
        assert action["action_type"] == "acl_set"
        assert action["params"]["path"] == "C:\\\\app\\\\data"

    def test_set_acl_quoted_path(self) -> None:
        """Set-Acl with a quoted path is parsed correctly."""
        action = _single('Set-Acl "C:\\\\Program Files\\\\MyApp" $acl\n')
        assert action["action_type"] == "acl_set"

    def test_icacls(self) -> None:
        """Icacls produces an acl_set action."""
        action = _single("icacls.exe C:\\\\app /grant Users:F\n")
        assert action["action_type"] == "acl_set"

    def test_acl_set_case_insensitive(self) -> None:
        """set-acl (lower-case) is still classified."""
        action = _single("set-acl c:\\\\data $acl\n")
        assert action["action_type"] == "acl_set"


# ---------------------------------------------------------------------------
# Mixed / multi-action scripts
# ---------------------------------------------------------------------------


class TestMultiActionScripts:
    """Tests for scripts containing multiple enterprise action types."""

    def test_user_and_group_in_same_script(self) -> None:
        """A script with user_create and group_member_add produces both actions."""
        script = (
            "New-LocalUser -Name svc_app\n"
            "Add-LocalGroupMember -Group Administrators -Member svc_app\n"
        )
        acts = _actions(script)
        types = [a["action_type"] for a in acts]
        assert "user_create" in types
        assert "group_member_add" in types

    def test_firewall_lifecycle(self) -> None:
        """Create, enable, disable, and remove firewall rules all classified."""
        script = (
            "New-NetFirewallRule -DisplayName Allow-80\n"
            "Enable-NetFirewallRule -DisplayName Allow-80\n"
            "Disable-NetFirewallRule -DisplayName Allow-80\n"
            "Remove-NetFirewallRule -DisplayName Allow-80\n"
        )
        types = [a["action_type"] for a in _actions(script)]
        assert types == [
            "firewall_rule_create",
            "firewall_rule_enable",
            "firewall_rule_disable",
            "firewall_rule_remove",
        ]

    def test_enterprise_mix(self) -> None:
        """A script mixing enterprise types produces all expected actions."""
        script = (
            "Install-Module -Name PSWindowsUpdate\n"
            "Register-ScheduledTask -TaskName AutoPatch\n"
            "[System.Environment]::SetEnvironmentVariable('PATCH_DIR', 'C:\\\\patches')\n"
            "Enable-PSRemoting -Force\n"
            "Import-Certificate -FilePath C:\\\\certs\\\\ca.cer\n"
            "New-WebSite -Name PatchPortal\n"
            "Set-DnsClientServerAddress -InterfaceAlias Eth0 -ServerAddresses 10.0.0.1\n"
            "Set-Acl C:\\\\patches $acl\n"
        )
        types = [a["action_type"] for a in _actions(script)]
        assert "psmodule_install" in types
        assert "scheduled_task_register" in types
        assert "environment_set" in types
        assert "winrm_enable" in types
        assert "certificate_import" in types
        assert "iis_website_create" in types
        assert "dns_client_set" in types
        assert "acl_set" in types

    def test_comments_not_classified(self) -> None:
        """Comment lines containing enterprise keywords are not classified."""
        script = "# New-LocalUser would create a user\n# Enable-PSRemoting -Force\n"
        acts = _actions(script)
        assert acts == []

    def test_line_numbers_are_correct(self) -> None:
        """source_line values reflect actual line numbers in the script."""
        script = (
            "# comment line 1\n"
            "New-LocalUser -Name svc\n"
            "Remove-LocalUser -Name olduser\n"
        )
        acts = _actions(script)
        assert acts[0]["source_line"] == 2
        assert acts[1]["source_line"] == 3
