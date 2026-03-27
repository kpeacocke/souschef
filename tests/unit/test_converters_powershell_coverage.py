"""
Tests for coverage gaps in souschef/converters/powershell.py.

Covers lines: 525-526, 536-537, 547-549, 559-561, 582-583, 593-594,
604-605, 615-616, 626-627, 649-650, 660-661, 671-672, 682-683,
693-699, 713-742.
"""

from __future__ import annotations

from souschef.converters.powershell import (
    _convert_acl_set,
    _convert_certificate_import,
    _convert_dns_client_set,
    _convert_firewall_rule_disable,
    _convert_firewall_rule_enable,
    _convert_firewall_rule_remove,
    _convert_group_member_add,
    _convert_group_member_remove,
    _convert_iis_website_create,
    _convert_psmodule_install,
    _convert_scheduled_task_register,
    _convert_scheduled_task_unregister,
    _convert_user_modify,
    _convert_user_remove,
    _convert_winrm_enable,
)

# ---------------------------------------------------------------------------
# _convert_user_modify — lines 525-526
# ---------------------------------------------------------------------------


def test_convert_user_modify_with_username() -> None:
    """_convert_user_modify returns win_user present task (lines 525-526)."""
    name, args = _convert_user_modify({"username": "alice"}, "")
    assert "alice" in name
    assert args["state"] == "present"
    assert args["update_password"] == "on_create"


def test_convert_user_modify_missing_username() -> None:
    """_convert_user_modify falls back to 'unknown' for missing username."""
    name, _ = _convert_user_modify({}, "")
    assert "unknown" in name


# ---------------------------------------------------------------------------
# _convert_user_remove — lines 536-537
# ---------------------------------------------------------------------------


def test_convert_user_remove_with_username() -> None:
    """_convert_user_remove returns win_user absent task (lines 536-537)."""
    name, args = _convert_user_remove({"username": "bob"}, "")
    assert "bob" in name
    assert args["state"] == "absent"


def test_convert_user_remove_missing_username() -> None:
    """_convert_user_remove falls back to 'unknown'."""
    name, _ = _convert_user_remove({}, "")
    assert "unknown" in name


# ---------------------------------------------------------------------------
# _convert_group_member_add — lines 547-549
# ---------------------------------------------------------------------------


def test_convert_group_member_add() -> None:
    """_convert_group_member_add returns win_group_membership present task (lines 547-549)."""
    name, args = _convert_group_member_add(
        {"group": "Administrators", "member": "alice"}, ""
    )
    assert "alice" in name
    assert "Administrators" in name
    assert args["state"] == "present"
    assert "alice" in args["members"]


def test_convert_group_member_add_defaults() -> None:
    """_convert_group_member_add falls back to 'unknown' for missing inputs."""
    name, _ = _convert_group_member_add({}, "")
    assert "unknown" in name


# ---------------------------------------------------------------------------
# _convert_group_member_remove — lines 559-561
# ---------------------------------------------------------------------------


def test_convert_group_member_remove() -> None:
    """_convert_group_member_remove returns win_group_membership absent task (lines 559-561)."""
    name, args = _convert_group_member_remove({"group": "Admins", "member": "bob"}, "")
    assert "bob" in name
    assert "Admins" in name
    assert args["state"] == "absent"


# ---------------------------------------------------------------------------
# _convert_firewall_rule_enable — lines 582-583
# ---------------------------------------------------------------------------


def test_convert_firewall_rule_enable() -> None:
    """_convert_firewall_rule_enable returns enabled=True task (lines 582-583)."""
    name, args = _convert_firewall_rule_enable({"rule_name": "HTTP-In"}, "")
    assert "HTTP-In" in name
    assert args["enabled"] is True
    assert args["state"] == "present"


# ---------------------------------------------------------------------------
# _convert_firewall_rule_disable — lines 593-594
# ---------------------------------------------------------------------------


def test_convert_firewall_rule_disable() -> None:
    """_convert_firewall_rule_disable returns enabled=False task (lines 593-594)."""
    name, args = _convert_firewall_rule_disable({"rule_name": "Telnet"}, "")
    assert "Telnet" in name
    assert args["enabled"] is False
    assert args["state"] == "present"


# ---------------------------------------------------------------------------
# _convert_firewall_rule_remove — lines 604-605
# ---------------------------------------------------------------------------


def test_convert_firewall_rule_remove() -> None:
    """_convert_firewall_rule_remove returns state=absent task (lines 604-605)."""
    name, args = _convert_firewall_rule_remove({"rule_name": "OldRule"}, "")
    assert "OldRule" in name
    assert args["state"] == "absent"


# ---------------------------------------------------------------------------
# _convert_scheduled_task_register — lines 615-616
# ---------------------------------------------------------------------------


def test_convert_scheduled_task_register() -> None:
    """_convert_scheduled_task_register returns state=present task (lines 615-616)."""
    name, args = _convert_scheduled_task_register({"task_name": "Backup"}, "")
    assert "Backup" in name
    assert args["state"] == "present"


# ---------------------------------------------------------------------------
# _convert_scheduled_task_unregister — lines 626-627
# ---------------------------------------------------------------------------


def test_convert_scheduled_task_unregister() -> None:
    """_convert_scheduled_task_unregister returns state=absent task (lines 626-627)."""
    name, args = _convert_scheduled_task_unregister({"task_name": "OldTask"}, "")
    assert "OldTask" in name
    assert args["state"] == "absent"


# ---------------------------------------------------------------------------
# _convert_psmodule_install — lines 649-650
# ---------------------------------------------------------------------------


def test_convert_psmodule_install() -> None:
    """_convert_psmodule_install returns win_psmodule present task (lines 649-650)."""
    name, args = _convert_psmodule_install({"module_name": "Az"}, "")
    assert "Az" in name
    assert args["state"] == "present"


# ---------------------------------------------------------------------------
# _convert_certificate_import — lines 660-661
# ---------------------------------------------------------------------------


def test_convert_certificate_import() -> None:
    """_convert_certificate_import returns win_certificate_store task (lines 660-661)."""
    name, args = _convert_certificate_import(
        {"certificate_path": "C:\\certs\\my.pfx"}, ""
    )
    assert "my.pfx" in name
    assert args["state"] == "present"


# ---------------------------------------------------------------------------
# _convert_winrm_enable — lines 671-672
# ---------------------------------------------------------------------------


def test_convert_winrm_enable_with_command() -> None:
    """_convert_winrm_enable returns win_shell task with raw command (lines 671-672)."""
    name, args = _convert_winrm_enable(
        {"raw_command": "Enable-PSRemoting -Force"}, "fallback"
    )
    assert "WinRM" in name
    assert args["cmd"] == "Enable-PSRemoting -Force"


def test_convert_winrm_enable_fallback_to_raw() -> None:
    """_convert_winrm_enable falls back to raw param when no raw_command."""
    name, args = _convert_winrm_enable({}, "some raw string")
    assert "WinRM" in name
    assert args["cmd"] == "some raw string"


# ---------------------------------------------------------------------------
# _convert_iis_website_create — lines 682-683
# ---------------------------------------------------------------------------


def test_convert_iis_website_create() -> None:
    """_convert_iis_website_create returns win_iis_website task (lines 682-683)."""
    name, args = _convert_iis_website_create({"site_name": "MySite"}, "")
    assert "MySite" in name
    assert args["state"] == "started"


def test_convert_iis_website_create_default_name() -> None:
    """_convert_iis_website_create uses default site name when not specified."""
    _, args = _convert_iis_website_create({}, "")
    assert args["name"] == "Default Web Site"


# ---------------------------------------------------------------------------
# _convert_dns_client_set — lines 693-699
# ---------------------------------------------------------------------------


def test_convert_dns_client_set_with_addresses() -> None:
    """_convert_dns_client_set parses space/comma-separated addresses (lines 693-699)."""
    name, args = _convert_dns_client_set({"server_addresses": "8.8.8.8, 8.8.4.4"}, "")
    assert "DNS" in name
    assert "8.8.8.8" in args["ipv4_addresses"]
    assert "8.8.4.4" in args["ipv4_addresses"]
    assert args["adapter_names"] == "*"


def test_convert_dns_client_set_empty_addresses() -> None:
    """_convert_dns_client_set falls back to 127.0.0.1 for empty addresses."""
    _, args = _convert_dns_client_set({"server_addresses": ""}, "")
    assert args["ipv4_addresses"] == ["127.0.0.1"]


def test_convert_dns_client_set_quoted_addresses() -> None:
    """_convert_dns_client_set strips quotes and brackets from addresses."""
    _, args = _convert_dns_client_set(
        {"server_addresses": "['1.1.1.1', '1.0.0.1']"}, ""
    )
    assert "1.1.1.1" in args["ipv4_addresses"]


# ---------------------------------------------------------------------------
# _convert_acl_set — lines 713-742
# ---------------------------------------------------------------------------


def test_convert_acl_set_with_user_and_rights() -> None:
    """_convert_acl_set with user and rights includes them in args (lines 722-729)."""
    name, args = _convert_acl_set(
        {"path": "C:\\data", "user": "DOMAIN\\alice", "rights": "Read"}, ""
    )
    assert "C:\\data" in name
    assert args["user"] == "DOMAIN\\alice"
    assert args["rights"] == "Read"
    assert args["type"] == "allow"
    assert args["state"] == "present"


def test_convert_acl_set_without_user_requires_review() -> None:
    """_convert_acl_set without user/rights adds review_required marker (lines 730-740)."""
    name, args = _convert_acl_set({"path": "C:\\data"}, "")
    assert "C:\\data" in name
    assert args["review_required"] is True
    assert "notes" in args
    assert "win_acl" in args["notes"]


def test_convert_acl_set_empty_params() -> None:
    """_convert_acl_set with empty params returns a fallback task."""
    _, args = _convert_acl_set({}, "")
    assert args["review_required"] is True
    assert args["path"] == ""
