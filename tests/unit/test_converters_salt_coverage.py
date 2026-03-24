"""Coverage tests for uncovered paths in souschef/converters/salt.py."""

import json
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# _extract_group_name_from_grain
# ---------------------------------------------------------------------------


def test_extract_group_name_from_grain_valid() -> None:
    """G@key:value returns normalised group name."""
    from souschef.converters.salt import _extract_group_name_from_grain

    result = _extract_group_name_from_grain("G@os_family:Debian")
    assert result == "os_family_Debian"


def test_extract_group_name_from_grain_no_prefix() -> None:
    """Non-G@ target returns None."""
    from souschef.converters.salt import _extract_group_name_from_grain

    result = _extract_group_name_from_grain("webserver-01")
    assert result is None


def test_extract_group_name_from_grain_no_colon() -> None:
    """G@ target without colon returns None."""
    from souschef.converters.salt import _extract_group_name_from_grain

    result = _extract_group_name_from_grain("G@osname")
    assert result is None


def test_extract_group_name_from_grain_normalises_dash_and_dot() -> None:
    """Dashes and dots in key/value are replaced with underscores."""
    from souschef.converters.salt import _extract_group_name_from_grain

    result = _extract_group_name_from_grain("G@os-family:Red.Hat")
    assert result == "os_family_Red_Hat"


# ---------------------------------------------------------------------------
# _append_inventory_target_lines
# ---------------------------------------------------------------------------


def test_append_inventory_target_lines_plain_host() -> None:
    """Plain hostname is appended directly."""
    from souschef.converters.salt import _append_inventory_target_lines

    lines: list[str] = []
    _append_inventory_target_lines(lines, {"webserver01": ["base"]})
    assert "webserver01" in lines


def test_append_inventory_target_lines_grain_with_colon() -> None:
    """G@ target with colon becomes a comment with group reference."""
    from souschef.converters.salt import _append_inventory_target_lines

    lines: list[str] = []
    _append_inventory_target_lines(lines, {"G@os_family:Debian": ["base"]})
    assert any("grain target" in line for line in lines)
    assert any("group" in line for line in lines)


def test_append_inventory_target_lines_grain_no_colon() -> None:
    """G@ target without colon becomes a comment without group."""
    from souschef.converters.salt import _append_inventory_target_lines

    lines: list[str] = []
    _append_inventory_target_lines(lines, {"G@osname": ["base"]})
    assert any("grain target" in line for line in lines)


def test_append_inventory_target_lines_glob() -> None:
    """Glob pattern becomes a comment."""
    from souschef.converters.salt import _append_inventory_target_lines

    lines: list[str] = []
    _append_inventory_target_lines(lines, {"web*": ["base"]})
    assert any("glob target" in line for line in lines)


def test_append_inventory_target_lines_question_mark_glob() -> None:
    """Question-mark glob pattern becomes a comment."""
    from souschef.converters.salt import _append_inventory_target_lines

    lines: list[str] = []
    _append_inventory_target_lines(lines, {"web?01": ["base"]})
    assert any("glob target" in line for line in lines)


# ---------------------------------------------------------------------------
# _append_inventory_grain_groups
# ---------------------------------------------------------------------------


def test_append_inventory_grain_groups_has_grain() -> None:
    """G@ target with colon produces a group section."""
    from souschef.converters.salt import _append_inventory_grain_groups

    lines: list[str] = []
    _append_inventory_grain_groups(lines, {"G@os_family:Debian": ["base"]})
    assert "[os_family_Debian]" in lines


def test_append_inventory_grain_groups_no_grain() -> None:
    """Non-grain target produces no output."""
    from souschef.converters.salt import _append_inventory_grain_groups

    lines: list[str] = []
    _append_inventory_grain_groups(lines, {"webserver01": ["base"]})
    assert lines == []


# ---------------------------------------------------------------------------
# _extract_watch_handlers
# ---------------------------------------------------------------------------


def test_extract_watch_handlers_service_state() -> None:
    """Service state produces a restart handler."""
    from souschef.converters.salt import _extract_watch_handlers

    states = [
        {
            "id": "nginx",
            "module": "service",
            "function": "running",
            "args": {"name": "nginx"},
        }
    ]
    handlers = _extract_watch_handlers(states)
    assert len(handlers) == 1
    assert handlers[0]["name"] == "Restart nginx"


def test_extract_watch_handlers_non_service_skipped() -> None:
    """Non-service states produce no handlers."""
    from souschef.converters.salt import _extract_watch_handlers

    states = [{"id": "vim", "module": "pkg", "function": "installed", "args": {}}]
    handlers = _extract_watch_handlers(states)
    assert handlers == []


def test_extract_watch_handlers_deduplicates() -> None:
    """Duplicate service names produce only one handler."""
    from souschef.converters.salt import _extract_watch_handlers

    states = [
        {
            "id": "nginx",
            "module": "service",
            "function": "running",
            "args": {"name": "nginx"},
        },
        {
            "id": "nginx2",
            "module": "service",
            "function": "running",
            "args": {"name": "nginx"},
        },
    ]
    handlers = _extract_watch_handlers(states)
    assert len(handlers) == 1


def test_extract_watch_handlers_uses_id_when_no_name() -> None:
    """State id is used as service name when args has no 'name' key."""
    from souschef.converters.salt import _extract_watch_handlers

    states = [{"id": "httpd", "module": "service", "function": "running", "args": {}}]
    handlers = _extract_watch_handlers(states)
    assert handlers[0]["name"] == "Restart httpd"


# ---------------------------------------------------------------------------
# _top_to_ansible_inventory
# ---------------------------------------------------------------------------


def test_top_to_ansible_inventory_basic() -> None:
    """Plain host targets map to env group."""
    from souschef.converters.salt import _top_to_ansible_inventory

    top_data = {
        "environments": {"base": {"webserver01": ["nginx"], "dbserver01": ["mysql"]}}
    }
    result = _top_to_ansible_inventory(top_data)
    assert "[env_base]" in result
    assert "webserver01" in result
    assert "dbserver01" in result


def test_top_to_ansible_inventory_skips_non_dict_targets() -> None:
    """Environments with non-dict targets are skipped."""
    from souschef.converters.salt import _top_to_ansible_inventory

    top_data = {"environments": {"base": "not_a_dict"}}
    result = _top_to_ansible_inventory(top_data)
    assert "[env_base]" not in result


def test_top_to_ansible_inventory_empty() -> None:
    """Empty environments produce header only."""
    from souschef.converters.salt import _top_to_ansible_inventory

    result = _top_to_ansible_inventory({"environments": {}})
    assert "Ansible inventory" in result


# ---------------------------------------------------------------------------
# _render_nested_yaml_value
# ---------------------------------------------------------------------------


def test_render_nested_yaml_value_flat_dict() -> None:
    """Flat dict is rendered as YAML key-value lines."""
    from souschef.converters.salt import _render_nested_yaml_value

    lines = _render_nested_yaml_value({"host": "localhost", "port": 5432}, indent=2)
    assert any("host" in line for line in lines)
    assert any("port" in line for line in lines)


def test_render_nested_yaml_value_nested_dict() -> None:
    """Nested dicts recurse properly."""
    from souschef.converters.salt import _render_nested_yaml_value

    lines = _render_nested_yaml_value({"db": {"host": "localhost"}}, indent=2)
    assert any("db:" in line for line in lines)
    assert any("host" in line for line in lines)


def test_render_nested_yaml_value_list() -> None:
    """List values are rendered as YAML list items."""
    from souschef.converters.salt import _render_nested_yaml_value

    lines = _render_nested_yaml_value({"items": ["a", "b"]}, indent=2)
    assert any("items:" in line for line in lines)
    assert any("- a" in line for line in lines)


def test_render_nested_yaml_value_bool() -> None:
    """Bool values are lowercased."""
    from souschef.converters.salt import _render_nested_yaml_value

    lines = _render_nested_yaml_value({"enabled": True}, indent=2)
    assert any("enabled: true" in line for line in lines)


def test_render_nested_yaml_value_none() -> None:
    """None value renders as empty YAML."""
    from souschef.converters.salt import _render_nested_yaml_value

    lines = _render_nested_yaml_value({"val": None}, indent=2)
    assert any("val:" in line for line in lines)


def test_render_nested_yaml_value_number() -> None:
    """Numeric values render without quotes."""
    from souschef.converters.salt import _render_nested_yaml_value

    lines = _render_nested_yaml_value({"count": 42}, indent=2)
    assert any("count: 42" in line for line in lines)


def test_render_nested_yaml_value_non_dict_input() -> None:
    """Non-dict input returns empty list."""
    from souschef.converters.salt import _render_nested_yaml_value

    lines = _render_nested_yaml_value("not_a_dict", indent=2)  # type: ignore[arg-type]
    assert lines == []


# ---------------------------------------------------------------------------
# _render_pillar_var_line
# ---------------------------------------------------------------------------


def test_render_pillar_var_line_string() -> None:
    """String value is quoted in output."""
    from souschef.converters.salt import _render_pillar_var_line

    lines: list[str] = []
    _render_pillar_var_line("db_host", "localhost", lines)
    assert lines == ["db_host: 'localhost'"]


def test_render_pillar_var_line_dict() -> None:
    """Dict value renders as nested YAML."""
    from souschef.converters.salt import _render_pillar_var_line

    lines: list[str] = []
    _render_pillar_var_line("db", {"host": "localhost"}, lines)
    assert lines
    assert lines[0] == "db:"


def test_render_pillar_var_line_list() -> None:
    """List value renders as YAML list."""
    from souschef.converters.salt import _render_pillar_var_line

    lines: list[str] = []
    _render_pillar_var_line("packages", ["nginx", "vim"], lines)
    assert lines
    assert "packages:" in lines[0]
    assert any("- nginx" in line for line in lines)


def test_render_pillar_var_line_bool() -> None:
    """Bool value is lowercased."""
    from souschef.converters.salt import _render_pillar_var_line

    lines: list[str] = []
    _render_pillar_var_line("enabled", True, lines)
    assert lines == ["enabled: true"]


def test_render_pillar_var_line_none() -> None:
    """None value renders as empty."""
    from souschef.converters.salt import _render_pillar_var_line

    lines: list[str] = []
    _render_pillar_var_line("val", None, lines)
    assert lines == ["val:"]


def test_render_pillar_var_line_int() -> None:
    """Integer renders without quotes."""
    from souschef.converters.salt import _render_pillar_var_line

    lines: list[str] = []
    _render_pillar_var_line("port", 5432, lines)
    assert lines == ["port: 5432"]


# ---------------------------------------------------------------------------
# _pillar_to_vault_vars
# ---------------------------------------------------------------------------


def test_pillar_to_vault_vars_basic() -> None:
    """Basic pillar dict produces YAML with header."""
    from souschef.converters.salt import _pillar_to_vault_vars

    result = _pillar_to_vault_vars({"db_host": "localhost", "db_port": 5432})
    assert "---" in result
    assert "db_host" in result
    assert "db_port" in result


def test_pillar_to_vault_vars_with_prefix() -> None:
    """Prefix is prepended to variable names."""
    from souschef.converters.salt import _pillar_to_vault_vars

    result = _pillar_to_vault_vars({"host": "localhost"}, prefix="myapp")
    assert "myapp_host" in result


def test_pillar_to_vault_vars_empty() -> None:
    """Empty dict produces just the YAML header."""
    from souschef.converters.salt import _pillar_to_vault_vars

    result = _pillar_to_vault_vars({})
    assert "---" in result
    assert "Converted from SaltStack pillar" in result


# ---------------------------------------------------------------------------
# convert_salt_pillar_to_vars
# ---------------------------------------------------------------------------


def test_convert_salt_pillar_to_vars_file_not_found(tmp_path: Path) -> None:
    """Missing file returns error JSON."""
    from souschef.converters.salt import convert_salt_pillar_to_vars

    result = json.loads(convert_salt_pillar_to_vars(str(tmp_path / "missing.sls")))
    assert "error" in result


def test_convert_salt_pillar_to_vars_directory(tmp_path: Path) -> None:
    """Directory path returns error JSON."""
    from souschef.converters.salt import convert_salt_pillar_to_vars

    result = json.loads(convert_salt_pillar_to_vars(str(tmp_path)))
    assert "error" in result


def test_convert_salt_pillar_to_vars_valid(tmp_path: Path) -> None:
    """Valid pillar file returns vars_file, variable_count, format."""
    pillar_file = tmp_path / "common.sls"
    pillar_file.write_text("db_host: localhost\ndb_port: 5432\n")

    with patch(
        "souschef.parsers.salt._parse_sls_yaml",
        return_value={"db_host": "localhost", "db_port": 5432},
    ):
        from souschef.converters.salt import convert_salt_pillar_to_vars

        result = json.loads(convert_salt_pillar_to_vars(str(pillar_file)))
    assert "vars_file" in result
    assert result["variable_count"] == 2
    assert result["format"] == "yaml"


def test_convert_salt_pillar_to_vars_vault_format(tmp_path: Path) -> None:
    """Vault format adds vault annotation header."""
    pillar_file = tmp_path / "secrets.sls"
    pillar_file.write_text("api_key: secret\n")

    with patch(
        "souschef.parsers.salt._parse_sls_yaml",
        return_value={"api_key": "secret"},
    ):
        from souschef.converters.salt import convert_salt_pillar_to_vars

        result = json.loads(
            convert_salt_pillar_to_vars(str(pillar_file), output_format="vault")
        )
    assert "Vault" in result["vars_file"] or "vault" in result["vars_file"].lower()
    assert result["format"] == "vault"


def test_convert_salt_pillar_to_vars_permission_error(tmp_path: Path) -> None:
    """PermissionError returns error JSON."""
    with patch(
        "souschef.converters.salt._ensure_within_base_path",
        side_effect=PermissionError("denied"),
    ):
        from souschef.converters.salt import convert_salt_pillar_to_vars

        result = json.loads(convert_salt_pillar_to_vars("/srv/salt/pillar.sls"))
    assert "error" in result


def test_convert_salt_pillar_to_vars_value_error(tmp_path: Path) -> None:
    """ValueError returns error JSON."""
    with patch(
        "souschef.converters.salt._ensure_within_base_path",
        side_effect=ValueError("bad path"),
    ):
        from souschef.converters.salt import convert_salt_pillar_to_vars

        result = json.loads(convert_salt_pillar_to_vars("/srv/salt/pillar.sls"))
    assert "error" in result
    assert "bad path" in result["error"]


# ---------------------------------------------------------------------------
# _collect_role_data
# ---------------------------------------------------------------------------


def test_collect_role_data_basic(tmp_path: Path) -> None:
    """Reads SLS files and converts states to tasks."""
    sls_file = tmp_path / "init.sls"
    sls_file.write_text("nginx:\n  pkg.installed\n")

    mock_state = {"id": "nginx", "module": "pkg", "function": "installed", "args": {}}

    from souschef.converters.salt import _collect_role_data

    tasks, _, _ = _collect_role_data(
        rel_paths=["init.sls"],
        safe_salt=tmp_path,
        workspace_root=tmp_path.parent,
        warnings=[],
        parse_sls_states=lambda _: [mock_state],
        extract_pillars=lambda _: [],
    )
    assert len(tasks) == 1


def test_collect_role_data_oserror_adds_warning(tmp_path: Path) -> None:
    """OSError when reading a file appends a warning and continues."""
    from souschef.converters.salt import _collect_role_data

    warnings: list[str] = []
    _, _, _ = _collect_role_data(
        rel_paths=["missing.sls"],
        safe_salt=tmp_path,
        workspace_root=tmp_path.parent,
        warnings=warnings,
        parse_sls_states=lambda _: [],
        extract_pillars=lambda _: [],
    )
    assert len(warnings) == 1
    assert "missing.sls" in warnings[0]


def test_collect_role_data_pillars_become_defaults(tmp_path: Path) -> None:
    """Pillar references are added to role defaults."""
    sls_file = tmp_path / "init.sls"
    sls_file.write_text("placeholder\n")

    from souschef.converters.salt import _collect_role_data

    _, _, defaults = _collect_role_data(
        rel_paths=["init.sls"],
        safe_salt=tmp_path,
        workspace_root=tmp_path.parent,
        warnings=[],
        parse_sls_states=lambda _: [],
        extract_pillars=lambda _: ["db.host"],
    )
    assert "db_host" in defaults


def test_collect_role_data_handlers_extracted(tmp_path: Path) -> None:
    """Service states produce handlers via _extract_watch_handlers."""
    sls_file = tmp_path / "init.sls"
    sls_file.write_text("nginx:\n  service.running\n")

    mock_state = {
        "id": "nginx",
        "module": "service",
        "function": "running",
        "args": {"name": "nginx"},
    }

    from souschef.converters.salt import _collect_role_data

    _, handlers, _ = _collect_role_data(
        rel_paths=["init.sls"],
        safe_salt=tmp_path,
        workspace_root=tmp_path.parent,
        warnings=[],
        parse_sls_states=lambda _: [mock_state],
        extract_pillars=lambda _: [],
    )
    assert len(handlers) == 1
    assert handlers[0]["name"] == "Restart nginx"


# ---------------------------------------------------------------------------
# _write_role_files
# ---------------------------------------------------------------------------


def test_write_role_files_creates_structure(tmp_path: Path) -> None:
    """All four role files are created and returned."""
    from souschef.converters.salt import _write_role_files

    role_dir = tmp_path / "roles" / "webserver"
    files_written: list[str] = []
    warnings: list[str] = []

    result = _write_role_files(
        role_name="webserver",
        role_dir=role_dir,
        safe_out=tmp_path,
        workspace_root=tmp_path.parent,
        all_tasks=[
            {
                "name": "Install nginx",
                "ansible.builtin.package": {"name": "nginx", "state": "present"},
            }
        ],
        all_handlers=[],
        all_defaults={"db_host": "localhost"},
        files_written=files_written,
        warnings=warnings,
    )
    assert result is not None
    assert len(result) == 4
    assert (role_dir / "tasks" / "main.yml").exists()
    assert (role_dir / "handlers" / "main.yml").exists()


def test_write_role_files_with_handlers(tmp_path: Path) -> None:
    """When handlers exist, they are written to handlers/main.yml."""
    from souschef.converters.salt import _write_role_files

    role_dir = tmp_path / "roles" / "webserver"
    files_written: list[str] = []

    _write_role_files(
        role_name="webserver",
        role_dir=role_dir,
        safe_out=tmp_path,
        workspace_root=tmp_path.parent,
        all_tasks=[],
        all_handlers=[
            {
                "name": "Restart nginx",
                "ansible.builtin.service": {"name": "nginx", "state": "restarted"},
            }
        ],
        all_defaults={},
        files_written=files_written,
        warnings=[],
    )
    handlers_content = (role_dir / "handlers" / "main.yml").read_text()
    assert "nginx" in handlers_content


def test_write_role_files_permission_error_returns_none(tmp_path: Path) -> None:
    """PermissionError when creating dirs returns None."""
    from souschef.converters.salt import _write_role_files

    warnings: list[str] = []
    with patch(
        "souschef.converters.salt.safe_mkdir",
        side_effect=PermissionError("denied"),
    ):
        result = _write_role_files(
            role_name="webserver",
            role_dir=tmp_path / "roles" / "webserver",
            safe_out=tmp_path,
            workspace_root=tmp_path.parent,
            all_tasks=[],
            all_handlers=[],
            all_defaults={},
            files_written=[],
            warnings=warnings,
        )
    assert result is None
    assert len(warnings) == 1


# ---------------------------------------------------------------------------
# _write_site_yml
# ---------------------------------------------------------------------------


def test_write_site_yml_creates_file(tmp_path: Path) -> None:
    """site.yml is created with role plays."""
    from souschef.converters.salt import _write_site_yml

    files_written: list[str] = []
    _write_site_yml(
        safe_out=tmp_path,
        workspace_root=tmp_path.parent,
        roles_created=["webserver", "db"],
        files_written=files_written,
        warnings=[],
    )
    site_yml = tmp_path / "site.yml"
    assert site_yml.exists()
    content = site_yml.read_text()
    assert "webserver" in content
    assert "db" in content
    assert "site.yml" in files_written


def test_write_site_yml_permission_error_adds_warning(tmp_path: Path) -> None:
    """PermissionError adds a warning."""
    from souschef.converters.salt import _write_site_yml

    warnings: list[str] = []
    with patch(
        "souschef.converters.salt.safe_write_text",
        side_effect=PermissionError("denied"),
    ):
        _write_site_yml(
            safe_out=tmp_path,
            workspace_root=tmp_path.parent,
            roles_created=["webserver"],
            files_written=[],
            warnings=warnings,
        )
    assert len(warnings) == 1
    assert "site.yml" in warnings[0]


# ---------------------------------------------------------------------------
# _write_inventory_from_top
# ---------------------------------------------------------------------------


def test_write_inventory_from_top_no_top_sls(tmp_path: Path) -> None:
    """When top.sls is absent, nothing is written."""
    from souschef.converters.salt import _write_inventory_from_top

    files_written: list[str] = []
    _write_inventory_from_top(
        safe_salt=tmp_path,
        safe_out=tmp_path / "out",
        workspace_root=tmp_path.parent,
        files_written=files_written,
        warnings=[],
        parse_sls_yaml=lambda c: {},
        parse_top_environments=lambda d: {},
    )
    assert files_written == []


def test_write_inventory_from_top_with_top_sls(tmp_path: Path) -> None:
    """Parses top.sls and writes inventory/hosts."""
    top_sls = tmp_path / "top.sls"
    top_sls.write_text("base:\n  '*':\n    - common\n")
    out_dir = tmp_path / "out"

    files_written: list[str] = []
    from souschef.converters.salt import _write_inventory_from_top

    _write_inventory_from_top(
        safe_salt=tmp_path,
        safe_out=out_dir,
        workspace_root=tmp_path.parent,
        files_written=files_written,
        warnings=[],
        parse_sls_yaml=lambda c: {"base": {}},
        parse_top_environments=lambda d: {"base": {"webserver01": ["common"]}},
    )
    assert "inventory/hosts" in files_written


def test_write_inventory_from_top_oserror_adds_warning(tmp_path: Path) -> None:
    """OSError during write adds a warning."""
    top_sls = tmp_path / "top.sls"
    top_sls.write_text("base:\n  '*':\n    - common\n")

    warnings: list[str] = []
    from souschef.converters.salt import _write_inventory_from_top

    with patch(
        "souschef.converters.salt.safe_write_text",
        side_effect=OSError("disk full"),
    ):
        _write_inventory_from_top(
            safe_salt=tmp_path,
            safe_out=tmp_path / "out",
            workspace_root=tmp_path.parent,
            files_written=[],
            warnings=warnings,
            parse_sls_yaml=lambda c: {},
            parse_top_environments=lambda d: {"base": {"host": ["common"]}},
        )
    assert len(warnings) == 1


# ---------------------------------------------------------------------------
# convert_salt_directory_to_roles
# ---------------------------------------------------------------------------


def test_convert_salt_directory_to_roles_not_found(tmp_path: Path) -> None:
    """Non-existent salt_dir returns error JSON."""
    from souschef.converters.salt import convert_salt_directory_to_roles

    result = json.loads(
        convert_salt_directory_to_roles(
            str(tmp_path / "missing"), str(tmp_path / "out")
        )
    )
    assert "error" in result


def test_convert_salt_directory_to_roles_not_a_dir(tmp_path: Path) -> None:
    """File path for salt_dir returns error JSON."""
    salt_file = tmp_path / "init.sls"
    salt_file.write_text("nginx:\n  pkg.installed\n")

    from souschef.converters.salt import convert_salt_directory_to_roles

    result = json.loads(
        convert_salt_directory_to_roles(str(salt_file), str(tmp_path / "out"))
    )
    assert "error" in result


def test_convert_salt_directory_to_roles_permission_error() -> None:
    """PermissionError returns error JSON."""
    with patch(
        "souschef.converters.salt._ensure_within_base_path",
        side_effect=PermissionError("denied"),
    ):
        from souschef.converters.salt import convert_salt_directory_to_roles

        result = json.loads(convert_salt_directory_to_roles("/srv/salt", "/output"))
    assert "error" in result


def test_convert_salt_directory_to_roles_value_error() -> None:
    """ValueError returns error JSON."""
    with patch(
        "souschef.converters.salt._ensure_within_base_path",
        side_effect=ValueError("bad path"),
    ):
        from souschef.converters.salt import convert_salt_directory_to_roles

        result = json.loads(convert_salt_directory_to_roles("/srv/salt", "/output"))
    assert "error" in result
    assert "bad path" in result["error"]


def test_convert_salt_directory_to_roles_success(tmp_path: Path) -> None:
    """Valid salt dir produces roles, files_written, warnings, and structure."""
    salt_dir = tmp_path / "salt"
    salt_dir.mkdir()
    (salt_dir / "init.sls").write_text("nginx:\n  pkg.installed:\n    - name: nginx\n")
    out_dir = tmp_path / "out"

    from souschef.converters.salt import convert_salt_directory_to_roles

    result = json.loads(convert_salt_directory_to_roles(str(salt_dir), str(out_dir)))
    assert "roles_created" in result
    assert "files_written" in result
    assert "warnings" in result
    assert "structure" in result


def test_convert_salt_directory_to_roles_with_top_sls(tmp_path: Path) -> None:
    """top.sls triggers inventory generation."""
    salt_dir = tmp_path / "salt"
    salt_dir.mkdir()
    (salt_dir / "top.sls").write_text("base:\n  'webserver01':\n    - nginx\n")
    (salt_dir / "nginx.sls").write_text("nginx:\n  pkg.installed:\n    - name: nginx\n")
    out_dir = tmp_path / "out"

    from souschef.converters.salt import convert_salt_directory_to_roles

    result = json.loads(convert_salt_directory_to_roles(str(salt_dir), str(out_dir)))
    assert "inventory/hosts" in result.get("files_written", [])
