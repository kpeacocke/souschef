"""Tests for Ruby value parsing helpers in playbook conversion."""

from souschef.converters.playbook import (
    _convert_chef_attr_path_to_ansible_var,
    _convert_primitive_value,
    _convert_ruby_array_to_yaml,
    _convert_ruby_hash_to_yaml,
    _convert_ruby_value_to_yaml,
    _split_by_commas_with_nesting,
)


def test_convert_primitive_value_quotes_strings() -> None:
    """Test primitive conversion quotes unquoted strings."""
    assert _convert_primitive_value("nginx") == '"nginx"'


def test_convert_primitive_value_preserves_quoted_strings() -> None:
    """Test primitive conversion keeps quoted strings."""
    assert _convert_primitive_value("'nginx'") == "'nginx'"
    assert _convert_primitive_value('"nginx"') == '"nginx"'


def test_convert_primitive_value_handles_numbers() -> None:
    """Test primitive conversion handles numeric values."""
    assert _convert_primitive_value("42") == "42"
    assert _convert_primitive_value("3.14") == "3.14"


def test_convert_primitive_value_handles_booleans_and_nil() -> None:
    """Test primitive conversion handles booleans and nil."""
    assert _convert_primitive_value("TRUE") == "true"
    assert _convert_primitive_value("false") == "false"
    assert _convert_primitive_value("nil") == "null"


def test_convert_ruby_value_to_yaml_hash() -> None:
    """Test Ruby hash conversion to YAML flow style."""
    result = _convert_ruby_value_to_yaml("{ 'key' => 'value', 'count' => 2 }")

    assert "key:" in result
    assert "count: 2" in result


def test_convert_ruby_value_to_yaml_array() -> None:
    """Test Ruby array conversion to YAML flow style."""
    result = _convert_ruby_value_to_yaml("[1, 'two', 3]")

    assert result.startswith("[")
    assert "1" in result
    assert "'two'" in result
    assert "3" in result


def test_convert_ruby_hash_to_yaml_handles_malformed_pairs() -> None:
    """Test malformed hash pairs are preserved as unparsed fields."""
    result = _convert_ruby_hash_to_yaml("{ 'valid' => 'ok', malformed }")

    assert "valid:" in result
    assert "unparsed_" in result


def test_convert_ruby_hash_to_yaml_empty() -> None:
    """Test empty hash returns empty YAML object."""
    assert _convert_ruby_hash_to_yaml("{}") == "{}"


def test_convert_ruby_array_to_yaml_nested_structures() -> None:
    """Test array conversion with nested structures."""
    result = _convert_ruby_array_to_yaml("[1, {a => 2}, [3, 4]]")

    assert result.startswith("[")
    assert "{a: 2}" in result
    assert "[3, 4]" in result


def test_split_by_commas_with_nesting() -> None:
    """Test comma splitting respects nesting and quotes."""
    content = "a, {b => 1, c => [2,3]}, 'x,y', [4,5]"
    parts = _split_by_commas_with_nesting(content)

    assert len(parts) == 4
    assert parts[0] == "a"
    assert parts[1].startswith("{b => 1")
    assert parts[2] == "'x,y'"
    assert parts[3] == "[4,5]"


def test_convert_attr_path_to_ansible_var_numbers() -> None:
    """Test attribute path conversion handles numeric cookbook names."""
    result = _convert_chef_attr_path_to_ansible_var("301.version")

    assert result == "threezeroone_version"


def test_convert_attr_path_to_ansible_var_simple() -> None:
    """Test attribute path conversion for simple paths."""
    result = _convert_chef_attr_path_to_ansible_var("app.config.timeout")

    assert result == "app_config_timeout"
