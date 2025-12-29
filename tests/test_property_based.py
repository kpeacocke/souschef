"""Property-based tests using Hypothesis."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from souschef.server import (
    _convert_erb_to_jinja2,
    _extract_template_variables,
    list_directory,
    parse_attributes,
    parse_recipe,
    parse_template,
    read_file,
)


@given(st.text(min_size=1, max_size=100))
def test_read_file_handles_any_string_path(path_str):
    """Test that read_file handles any string path without crashing."""
    result = read_file(path_str)
    # Should always return a string (content or error message)
    assert isinstance(result, str)


@given(st.text(min_size=1, max_size=100))
def test_list_directory_handles_any_string_path(path_str):
    """Test that list_directory handles any string path without crashing."""
    result = list_directory(path_str)
    # Should return either a list or an error string
    assert isinstance(result, (list, str))


@given(st.text())
@settings(max_examples=50)
def test_parse_recipe_handles_any_content(content):
    """Test that parse_recipe doesn't crash on any file content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(content)
            f.flush()

            result = parse_recipe(f.name)
            # Should always return a string
            assert isinstance(result, str)
        finally:
            Path(f.name).unlink(missing_ok=True)


@given(st.text())
@settings(max_examples=50)
def test_parse_attributes_handles_any_content(content):
    """Test that parse_attributes doesn't crash on any file content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(content)
            f.flush()

            result = parse_attributes(f.name)
            # Should always return a string
            assert isinstance(result, str)
        finally:
            Path(f.name).unlink(missing_ok=True)


@given(
    precedence=st.sampled_from(["default", "override", "normal"]),
    key1=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=65, max_codepoint=122
        ),
        min_size=1,
        max_size=20,
    ),
    key2=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=65, max_codepoint=122
        ),
        min_size=1,
        max_size=20,
    ),
    value=st.integers(min_value=0, max_value=65535),
)
@settings(max_examples=50)
def test_parse_attributes_with_generated_attributes(precedence, key1, key2, value):
    """Test attribute parsing with randomly generated but valid attributes."""
    attr_content = f"{precedence}['{key1}']['{key2}'] = {value}\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(attr_content)
            f.flush()

            result = parse_attributes(f.name)

            # Should parse successfully
            assert precedence in result
            assert key1 in result
            assert key2 in result
            assert str(value) in result
        finally:
            Path(f.name).unlink(missing_ok=True)


@given(
    resource_type=st.sampled_from(
        ["package", "service", "template", "file", "directory", "user", "group"]
    ),
    resource_name=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd", "Pd"),
            min_codepoint=45,
            max_codepoint=122,
        ),
        min_size=1,
        max_size=50,
    ),
)
@settings(max_examples=50)
def test_parse_recipe_with_generated_resources(resource_type, resource_name):
    """Test recipe parsing with randomly generated but valid resources."""
    # Filter out problematic characters
    if not resource_name or resource_name.isspace():
        resource_name = "test"

    recipe_content = f"{resource_type} '{resource_name}' do\n  action :create\nend\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(recipe_content)
            f.flush()

            result = parse_recipe(f.name)

            # Should find the resource
            assert "Resource 1:" in result
            assert f"Type: {resource_type}" in result
            assert f"Name: {resource_name}" in result
        finally:
            Path(f.name).unlink(missing_ok=True)


# Template parsing property-based tests


@given(st.text())
@settings(max_examples=50)
def test_extract_template_variables_doesnt_crash(content):
    """Test that variable extraction handles any input without crashing."""
    variables = _extract_template_variables(content)

    # Should always return a set
    assert isinstance(variables, set)


@given(st.text())
@settings(max_examples=50)
def test_convert_erb_to_jinja2_doesnt_crash(content):
    """Test that ERB to Jinja2 conversion handles any input."""
    result = _convert_erb_to_jinja2(content)

    # Should always return a string
    assert isinstance(result, str)


@given(st.text())
@settings(max_examples=50)
def test_parse_template_handles_any_content(content):
    """Test that parse_template doesn't crash on any file content."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".erb", delete=False
    ) as f:
        try:
            f.write(content)
            f.flush()

            result = parse_template(f.name)
            # Should always return a string (JSON or error)
            assert isinstance(result, str)
        finally:
            Path(f.name).unlink(missing_ok=True)


@given(
    var_name=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            min_codepoint=65,
            max_codepoint=122,
        ),
        min_size=1,
        max_size=30,
    )
)
@settings(max_examples=50)
def test_erb_variable_extraction(var_name):
    """Test extracting variables from valid ERB syntax."""
    # Skip if var_name contains only digits (invalid as first char)
    if var_name[0].isdigit():
        var_name = "v" + var_name

    erb_content = f"Hello <%=@{var_name} %>!"
    variables = _extract_template_variables(erb_content)

    # Should extract the variable name
    assert var_name in variables


@given(
    var_name=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            min_codepoint=65,
            max_codepoint=122,
        ),
        min_size=1,
        max_size=30,
    )
)
@settings(max_examples=50)
def test_erb_to_jinja2_variable_conversion(var_name):
    """Test converting ERB variables to Jinja2 format."""
    # Skip if var_name starts with digit
    if var_name[0].isdigit():
        var_name = "v" + var_name

    erb_content = f"Value: <%= @{var_name} %>"
    jinja2 = _convert_erb_to_jinja2(erb_content)

    # Should convert to Jinja2 format
    assert "{{" in jinja2
    assert "}}" in jinja2
    assert var_name in jinja2
    assert "<%=" not in jinja2


@given(
    condition=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            min_codepoint=65,
            max_codepoint=122,
        ),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=50)
def test_erb_conditional_conversion(condition):
    """Test converting ERB conditionals to Jinja2."""
    # Skip if condition starts with digit
    if condition[0].isdigit():
        condition = "v" + condition

    erb_content = f"<% if {condition} %>Yes<% end %>"
    jinja2 = _convert_erb_to_jinja2(erb_content)

    # Should convert to Jinja2 format
    assert "{%" in jinja2
    assert "%}" in jinja2
    assert "if" in jinja2
    assert condition in jinja2
