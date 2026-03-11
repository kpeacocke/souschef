"""
Unit tests for the Puppet manifest parser.

Tests cover:
- parse_puppet_manifest: single file parsing
- parse_puppet_module: directory parsing
- Resource extraction (package, file, service, user, group, exec, etc.)
- Class and variable extraction
- Unsupported construct detection
- Error handling (file not found, directory, permission errors)
- Helper functions
"""

from pathlib import Path
from unittest.mock import patch

from souschef.parsers.puppet import (
    _build_line_index,
    _detect_unsupported_constructs,
    _extract_puppet_classes,
    _extract_puppet_resources,
    _extract_puppet_variables,
    _format_manifest_results,
    _get_line_number,
    _parse_class_params,
    _parse_manifest_content,
    _parse_puppet_attributes,
    _parse_resource_titles,
    get_puppet_resource_types,
    parse_puppet_manifest,
    parse_puppet_module,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_MANIFEST = """\
class webserver {
  $port = 80

  package { 'nginx':
    ensure => installed,
  }

  service { 'nginx':
    ensure => running,
    enable => true,
  }

  file { '/etc/nginx/nginx.conf':
    owner  => 'root',
    group  => 'root',
    mode   => '0644',
  }
}
"""

FULL_MANIFEST = """\
class myapp (
  String $app_name = 'myapp',
  Integer $port = 8080,
) {
  $config_dir = '/etc/myapp'

  package { 'myapp':
    ensure => latest,
  }

  user { 'myapp':
    ensure  => present,
    home    => '/home/myapp',
    shell   => '/bin/bash',
  }

  group { 'myapp':
    ensure => present,
    gid    => '1001',
  }

  exec { 'setup-myapp':
    command => '/usr/local/bin/setup.sh',
    creates => '/etc/myapp/.configured',
  }

  file { '/etc/myapp':
    ensure => directory,
    owner  => 'myapp',
    mode   => '0750',
  }

  cron { 'myapp-cleanup':
    command => '/usr/local/bin/cleanup.sh',
    hour    => '2',
    minute  => '30',
  }

  host { 'db.internal':
    ip     => '10.0.0.10',
    ensure => present,
  }
}
"""

UNSUPPORTED_MANIFEST = """\
class complex {
  $data = hiera('myapp::data')
  $val  = lookup('myapp::val')
  create_resources('file', $file_data)
  $tpl = inline_template('<%= @foo %>')

  @@file { '/tmp/exported':
    ensure => present,
  }
}
"""

MULTI_TITLE_MANIFEST = """\
package { ['nginx', 'curl', 'vim']:
  ensure => installed,
}
"""

EMPTY_MANIFEST = "# Just a comment, no resources\n"

CLASS_NO_PARAMS = """\
class simple {
  package { 'vim': ensure => installed }
}
"""


# ---------------------------------------------------------------------------
# Tests: parse_puppet_manifest
# ---------------------------------------------------------------------------


def test_parse_puppet_manifest_simple(tmp_path: Path) -> None:
    """Test parsing a simple manifest with common resource types."""
    manifest = tmp_path / "webserver.pp"
    manifest.write_text(SIMPLE_MANIFEST, encoding="utf-8")

    result = parse_puppet_manifest(str(manifest))

    assert "Puppet Manifest Analysis" in result
    assert "package { 'nginx' }" in result
    assert "service { 'nginx' }" in result
    assert "file { '/etc/nginx/nginx.conf' }" in result
    assert "Unsupported Constructs: none detected" in result


def test_parse_puppet_manifest_full(tmp_path: Path) -> None:
    """Test parsing a manifest with all supported resource types."""
    manifest = tmp_path / "full.pp"
    manifest.write_text(FULL_MANIFEST, encoding="utf-8")

    result = parse_puppet_manifest(str(manifest))

    assert "package { 'myapp' }" in result
    assert "user { 'myapp' }" in result
    assert "group { 'myapp' }" in result
    assert "exec { 'setup-myapp' }" in result
    assert "file { '/etc/myapp' }" in result
    assert "cron { 'myapp-cleanup' }" in result
    assert "host { 'db.internal' }" in result
    assert "Total resources:" in result


def test_parse_puppet_manifest_unsupported(tmp_path: Path) -> None:
    """Test that unsupported constructs are detected and reported."""
    manifest = tmp_path / "complex.pp"
    manifest.write_text(UNSUPPORTED_MANIFEST, encoding="utf-8")

    result = parse_puppet_manifest(str(manifest))

    assert "Unsupported Constructs" in result
    assert "Hiera lookup" in result
    assert "create_resources" in result
    assert "inline_template" in result
    assert "Exported resource" in result
    assert "manual review" in result


def test_parse_puppet_manifest_multi_title(tmp_path: Path) -> None:
    """Test that multi-title resource declarations are expanded."""
    manifest = tmp_path / "multi.pp"
    manifest.write_text(MULTI_TITLE_MANIFEST, encoding="utf-8")

    result = parse_puppet_manifest(str(manifest))

    assert "nginx" in result
    assert "curl" in result
    assert "vim" in result


def test_parse_puppet_manifest_empty(tmp_path: Path) -> None:
    """Test that an empty manifest returns a no-resources warning."""
    manifest = tmp_path / "empty.pp"
    manifest.write_text(EMPTY_MANIFEST, encoding="utf-8")

    result = parse_puppet_manifest(str(manifest))

    # No resources found → summary shows 0
    assert "Total resources: 0" in result


def test_parse_puppet_manifest_file_not_found(tmp_path: Path) -> None:
    """Test that a missing file returns an error message."""
    result = parse_puppet_manifest(str(tmp_path / "nonexistent.pp"))
    assert "Error" in result or "not found" in result.lower()


def test_parse_puppet_manifest_is_directory(tmp_path: Path) -> None:
    """Test that passing a directory returns an error message."""
    result = parse_puppet_manifest(str(tmp_path))
    assert "Error" in result or "directory" in result.lower()


def test_parse_puppet_manifest_too_large(tmp_path: Path) -> None:
    """Test that oversized manifests are rejected."""
    manifest = tmp_path / "huge.pp"
    manifest.write_bytes(b"x" * (2_100_000))

    result = parse_puppet_manifest(str(manifest))
    assert "too large" in result.lower()


def test_parse_puppet_manifest_permission_error(tmp_path: Path) -> None:
    """Test handling of permission denied errors."""
    manifest = tmp_path / "secret.pp"
    manifest.write_text("package { 'vim': ensure => installed }", encoding="utf-8")

    with patch(
        "souschef.parsers.puppet.safe_read_text",
        side_effect=PermissionError("denied"),
    ):
        result = parse_puppet_manifest(str(manifest))
    assert "Error" in result or "Permission" in result or "denied" in result


def test_parse_puppet_manifest_generic_exception(tmp_path: Path) -> None:
    """Test that generic exceptions return an error message."""
    manifest = tmp_path / "test.pp"
    manifest.write_text("package { 'vim': ensure => installed }", encoding="utf-8")

    with patch(
        "souschef.parsers.puppet._parse_manifest_content",
        side_effect=RuntimeError("unexpected"),
    ):
        result = parse_puppet_manifest(str(manifest))
    assert "error occurred" in result.lower()


# ---------------------------------------------------------------------------
# Tests: parse_puppet_module
# ---------------------------------------------------------------------------


def test_parse_puppet_module_success(tmp_path: Path) -> None:
    """Test parsing a module directory with multiple manifests."""
    (tmp_path / "init.pp").write_text(SIMPLE_MANIFEST, encoding="utf-8")
    (tmp_path / "config.pp").write_text(FULL_MANIFEST, encoding="utf-8")

    result = parse_puppet_module(str(tmp_path))

    assert "Puppet Manifest Analysis" in result
    assert "nginx" in result


def test_parse_puppet_module_no_manifests(tmp_path: Path) -> None:
    """Test that a directory without .pp files returns a warning."""
    result = parse_puppet_module(str(tmp_path))
    assert "Warning" in result or "No Puppet manifests" in result


def test_parse_puppet_module_not_found(tmp_path: Path) -> None:
    """Test that a missing directory returns an error."""
    result = parse_puppet_module(str(tmp_path / "missing"))
    assert "Error" in result or "not found" in result.lower()


def test_parse_puppet_module_is_file(tmp_path: Path) -> None:
    """Test that passing a file path (not dir) returns an error."""
    manifest = tmp_path / "file.pp"
    manifest.write_text("", encoding="utf-8")
    result = parse_puppet_module(str(manifest))
    assert "Error" in result or "directory" in result.lower()


def test_parse_puppet_module_generic_exception(tmp_path: Path) -> None:
    """Test that generic exceptions during module parsing return an error."""
    with patch(
        "souschef.parsers.puppet._normalize_path",
        side_effect=Exception("boom"),
    ):
        result = parse_puppet_module("/some/path")
    assert "error occurred" in result.lower()


def test_parse_puppet_module_value_error(tmp_path: Path) -> None:
    """Test that ValueError during module parsing returns an error."""
    with patch(
        "souschef.parsers.puppet._ensure_within_base_path",
        side_effect=ValueError("path traversal"),
    ):
        result = parse_puppet_module("/some/path")
    assert "Error" in result


def test_parse_puppet_module_file_not_found_error(tmp_path: Path) -> None:
    """Test that FileNotFoundError during module parsing returns an error."""
    with patch(
        "souschef.parsers.puppet._ensure_within_base_path",
        side_effect=FileNotFoundError("not found"),
    ):
        result = parse_puppet_module("/some/path")
    assert "Error" in result or "not found" in result.lower()


def test_parse_puppet_module_permission_error(tmp_path: Path) -> None:
    """Test handling of PermissionError during module parsing."""
    (tmp_path / "init.pp").write_text("package { 'vim': ensure => installed }", encoding="utf-8")

    with patch(
        "souschef.parsers.puppet._get_workspace_root",
        side_effect=PermissionError("denied"),
    ):
        result = parse_puppet_module(str(tmp_path))
    assert "Error" in result


def test_parse_puppet_module_skips_unreadable_file(tmp_path: Path) -> None:
    """Test that unreadable manifest files within a module are skipped."""
    good = tmp_path / "good.pp"
    bad = tmp_path / "bad.pp"
    good.write_text("package { 'vim': ensure => installed }", encoding="utf-8")
    bad.write_text("package { 'curl': ensure => installed }", encoding="utf-8")

    original_safe_read = __import__(
        "souschef.core.path_utils", fromlist=["safe_read_text"]
    ).safe_read_text

    def _selective_read(path: Path, *args: object, **kwargs: object) -> str:
        if "bad" in str(path):
            raise OSError("cannot read")
        return original_safe_read(path, *args, **kwargs)

    with patch("souschef.parsers.puppet.safe_read_text", side_effect=_selective_read):
        result = parse_puppet_module(str(tmp_path))

    # Should still process good.pp and not crash
    assert "vim" in result or "Puppet Manifest Analysis" in result


# ---------------------------------------------------------------------------
# Tests: _extract_puppet_resources
# ---------------------------------------------------------------------------


def test_extract_puppet_resources_basic() -> None:
    """Test extraction of basic Puppet resources."""
    resources = _extract_puppet_resources(SIMPLE_MANIFEST, "test.pp")
    types = {r["type"] for r in resources}
    assert "package" in types
    assert "service" in types
    assert "file" in types


def test_extract_puppet_resources_with_attributes() -> None:
    """Test that resource attributes are correctly extracted."""
    resources = _extract_puppet_resources(SIMPLE_MANIFEST, "test.pp")
    nginx_pkg = next(r for r in resources if r["title"] == "nginx")
    assert nginx_pkg["attributes"]["ensure"] == "installed"


def test_extract_puppet_resources_unknown_type() -> None:
    """Test that unknown resource types are ignored."""
    content = "unknowntype { 'thing': ensure => present }"
    resources = _extract_puppet_resources(content, "test.pp")
    assert len(resources) == 0


def test_extract_puppet_resources_line_numbers() -> None:
    """Test that resource line numbers are captured."""
    resources = _extract_puppet_resources(FULL_MANIFEST, "test.pp")
    for r in resources:
        assert r["line"] >= 1


def test_extract_puppet_resources_max_limit() -> None:
    """Test that resource extraction stops at MAX_RESOURCES."""
    # Build a manifest with many resources
    lines = [f"package {{ 'pkg{i}': ensure => installed }}" for i in range(15000)]
    content = "\n".join(lines)
    resources = _extract_puppet_resources(content, "test.pp")
    assert len(resources) <= 10000


def test_extract_puppet_resources_multi_title() -> None:
    """Test multi-title resource expansion."""
    resources = _extract_puppet_resources(MULTI_TITLE_MANIFEST, "test.pp")
    titles = {r["title"] for r in resources}
    assert "nginx" in titles
    assert "curl" in titles
    assert "vim" in titles


# ---------------------------------------------------------------------------
# Tests: _extract_puppet_classes
# ---------------------------------------------------------------------------


def test_extract_puppet_classes_basic() -> None:
    """Test extraction of class definitions."""
    classes = _extract_puppet_classes(SIMPLE_MANIFEST, "test.pp")
    assert len(classes) == 1
    assert classes[0]["name"] == "webserver"


def test_extract_puppet_classes_with_params() -> None:
    """Test that class parameters are extracted correctly."""
    classes = _extract_puppet_classes(FULL_MANIFEST, "test.pp")
    assert len(classes) == 1
    cls = classes[0]
    assert cls["name"] == "myapp"
    param_names = [p["name"] for p in cls["parameters"]]
    assert "app_name" in param_names
    assert "port" in param_names


def test_extract_puppet_classes_no_params() -> None:
    """Test extraction of class with no parameters."""
    classes = _extract_puppet_classes(CLASS_NO_PARAMS, "test.pp")
    assert len(classes) == 1
    assert classes[0]["parameters"] == []


def test_extract_puppet_classes_empty_manifest() -> None:
    """Test that empty manifests return no classes."""
    classes = _extract_puppet_classes(EMPTY_MANIFEST, "test.pp")
    assert classes == []


# ---------------------------------------------------------------------------
# Tests: _extract_puppet_variables
# ---------------------------------------------------------------------------


def test_extract_puppet_variables_basic() -> None:
    """Test extraction of variable assignments."""
    variables = _extract_puppet_variables(SIMPLE_MANIFEST, "test.pp")
    names = {v["name"] for v in variables}
    assert "port" in names


def test_extract_puppet_variables_full() -> None:
    """Test extraction from a manifest with multiple variables."""
    variables = _extract_puppet_variables(FULL_MANIFEST, "test.pp")
    names = {v["name"] for v in variables}
    assert "config_dir" in names


def test_extract_puppet_variables_values() -> None:
    """Test that variable values are correctly captured."""
    variables = _extract_puppet_variables(SIMPLE_MANIFEST, "test.pp")
    port_var = next(v for v in variables if v["name"] == "port")
    assert "80" in port_var["value"]


# ---------------------------------------------------------------------------
# Tests: _detect_unsupported_constructs
# ---------------------------------------------------------------------------


def test_detect_unsupported_hiera() -> None:
    """Test detection of Hiera lookups."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_MANIFEST, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "Hiera lookup" in constructs


def test_detect_unsupported_create_resources() -> None:
    """Test detection of create_resources calls."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_MANIFEST, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "create_resources function" in constructs


def test_detect_unsupported_exported_resource() -> None:
    """Test detection of exported resources."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_MANIFEST, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "Exported resource" in constructs


def test_detect_unsupported_inline_template() -> None:
    """Test detection of inline_template calls."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_MANIFEST, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "inline_template function" in constructs


def test_detect_unsupported_none_in_clean_manifest() -> None:
    """Test that a clean manifest has no unsupported constructs."""
    unsupported = _detect_unsupported_constructs(SIMPLE_MANIFEST, "test.pp")
    assert len(unsupported) == 0


def test_detect_unsupported_lookup_function() -> None:
    """Test detection of the lookup() function."""
    content = "lookup('key')"
    unsupported = _detect_unsupported_constructs(content, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "Hiera lookup (lookup function)" in constructs


def test_detect_unsupported_virtual_resource() -> None:
    """Test detection of virtual resource declarations."""
    content = "@package { 'virtual-pkg': ensure => installed }\nvirtual resource here"
    unsupported = _detect_unsupported_constructs(content, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "Virtual resource declaration" in constructs


def test_detect_unsupported_generate_function() -> None:
    """Test detection of the generate() function."""
    content = "generate('/usr/bin/myscript', 'arg')"
    unsupported = _detect_unsupported_constructs(content, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "generate function" in constructs


def test_detect_unsupported_defined_function() -> None:
    """Test detection of the defined() function."""
    content = "if defined(Package['nginx']) { }"
    unsupported = _detect_unsupported_constructs(content, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "defined() function" in constructs


def test_detect_unsupported_realize() -> None:
    """Test detection of realize calls."""
    content = "realize Package['nginx']"
    unsupported = _detect_unsupported_constructs(content, "test.pp")
    constructs = {item["construct"] for item in unsupported}
    assert "Virtual resource realization" in constructs


# ---------------------------------------------------------------------------
# Tests: helper functions
# ---------------------------------------------------------------------------


def test_parse_resource_titles_single() -> None:
    """Test parsing single resource titles."""
    titles = _parse_resource_titles("'nginx'")
    assert titles == ["nginx"]


def test_parse_resource_titles_double_quote() -> None:
    """Test parsing double-quoted resource titles."""
    titles = _parse_resource_titles('"nginx"')
    assert titles == ["nginx"]


def test_parse_resource_titles_array() -> None:
    """Test parsing array resource titles."""
    titles = _parse_resource_titles("['nginx', 'curl', 'vim']")
    assert titles == ["nginx", "curl", "vim"]


def test_parse_resource_titles_array_empty_items() -> None:
    """Test parsing array resource titles with spaces."""
    titles = _parse_resource_titles("['a', 'b']")
    assert "a" in titles
    assert "b" in titles


def test_parse_puppet_attributes_basic() -> None:
    """Test parsing basic puppet attributes."""
    attrs = _parse_puppet_attributes("ensure => installed,\nowner => 'root',")
    assert attrs["ensure"] == "installed"
    assert attrs["owner"] == "root"


def test_parse_puppet_attributes_empty() -> None:
    """Test parsing empty attribute string."""
    attrs = _parse_puppet_attributes("")
    assert attrs == {}


def test_parse_class_params_with_types() -> None:
    """Test parsing class parameters with types."""
    params = _parse_class_params("String $name = 'default', Integer $port = 80")
    assert len(params) >= 2
    names = [p["name"] for p in params]
    assert "name" in names
    assert "port" in names


def test_parse_class_params_empty() -> None:
    """Test parsing empty class parameters."""
    params = _parse_class_params("")
    assert params == []


def test_parse_class_params_no_type() -> None:
    """Test parsing class parameters without type annotations."""
    params = _parse_class_params("$my_param = 'val'")
    assert len(params) >= 1
    assert params[0]["name"] == "my_param"


def test_build_line_index_basic() -> None:
    """Test line index construction."""
    content = "line1\nline2\nline3"
    idx = _build_line_index(content)
    assert idx[0] == 0
    assert idx[1] == 6  # after 'line1\n'
    assert idx[2] == 12  # after 'line2\n'


def test_get_line_number_first_line() -> None:
    """Test getting line number for first character."""
    idx = _build_line_index("abc\ndef\nghi")
    assert _get_line_number(0, idx) == 1


def test_get_line_number_second_line() -> None:
    """Test getting line number for a second-line character."""
    idx = _build_line_index("abc\ndef\nghi")
    assert _get_line_number(4, idx) == 2


def test_get_line_number_last_line() -> None:
    """Test getting line number for last-line character."""
    idx = _build_line_index("abc\ndef\nghi")
    assert _get_line_number(8, idx) == 3


def test_format_manifest_results_with_unsupported() -> None:
    """Test formatting with unsupported constructs shows review note."""
    results = {
        "resources": [],
        "classes": [],
        "variables": [],
        "unsupported": [
            {
                "construct": "Hiera lookup",
                "text": "hiera('key')",
                "source_file": "test.pp",
                "line": 5,
            }
        ],
    }
    output = _format_manifest_results(results, "test.pp")
    assert "Hiera lookup" in output
    assert "manual review" in output.lower() or "NOTE:" in output


def test_format_manifest_results_many_variables() -> None:
    """Test that >20 variables show a truncation indicator."""
    variables = [
        {"name": f"var{i}", "value": str(i), "source_file": "x.pp", "line": i}
        for i in range(25)
    ]
    results = {
        "resources": [],
        "classes": [],
        "variables": variables,
        "unsupported": [],
    }
    output = _format_manifest_results(results, "x.pp")
    assert "and" in output and "more" in output


def test_format_manifest_results_no_resources() -> None:
    """Test formatting when no resources are found."""
    results = {"resources": [], "classes": [], "variables": [], "unsupported": []}
    output = _format_manifest_results(results, "empty.pp")
    assert "none found" in output or "Total resources: 0" in output


def test_get_puppet_resource_types() -> None:
    """Test that get_puppet_resource_types returns expected types."""
    types = get_puppet_resource_types()
    assert "package" in types
    assert "file" in types
    assert "service" in types
    assert "user" in types
    assert "group" in types
    assert "exec" in types
    assert isinstance(types, list)
    assert types == sorted(types)


def test_parse_manifest_content_structure() -> None:
    """Test that _parse_manifest_content returns correct structure."""
    result = _parse_manifest_content(SIMPLE_MANIFEST, "test.pp")
    assert "resources" in result
    assert "classes" in result
    assert "variables" in result
    assert "unsupported" in result
