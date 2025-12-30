"""Property-based tests using Hypothesis."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from souschef.server import (
    _convert_erb_to_jinja2,
    _extract_resource_actions,
    _extract_resource_properties,
    _extract_template_variables,
    _parse_inspec_control,
    convert_inspec_to_test,
    generate_inspec_from_recipe,
    list_directory,
    parse_attributes,
    parse_custom_resource,
    parse_inspec_profile,
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".erb", delete=False) as f:
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


# Custom resource property-based tests


@given(st.text())
@settings(max_examples=50)
def test_parse_custom_resource_handles_any_content(content):
    """Test that parse_custom_resource doesn't crash on any file content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(content)
            f.flush()

            result = parse_custom_resource(f.name)
            # Should always return a string
            assert isinstance(result, str)
        finally:
            Path(f.name).unlink(missing_ok=True)


@given(
    prop_name=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            min_codepoint=65,
            max_codepoint=122,
        ),
        min_size=1,
        max_size=20,
    ),
    prop_type=st.sampled_from(["String", "Integer", "Boolean", "Array", "Hash"]),
)
@settings(max_examples=50)
def test_extract_property_modern_syntax(prop_name, prop_type):
    """Test extracting modern property definitions with random names."""
    # Skip if property name starts with digit
    if prop_name[0].isdigit():
        prop_name = "p" + prop_name

    content = f"property :{prop_name}, {prop_type}"
    properties = _extract_resource_properties(content)

    # Should extract at least one property
    assert len(properties) >= 1
    # Should contain the property name
    assert any(p["name"] == prop_name for p in properties)


@given(
    attr_name=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            min_codepoint=65,
            max_codepoint=122,
        ),
        min_size=1,
        max_size=20,
    ),
    attr_type=st.sampled_from(
        ["String", "Integer", "TrueClass", "FalseClass", "Array"]
    ),
)
@settings(max_examples=50)
def test_extract_attribute_lwrp_syntax(attr_name, attr_type):
    """Test extracting LWRP attribute definitions with random names."""
    # Skip if attribute name starts with digit
    if attr_name[0].isdigit():
        attr_name = "a" + attr_name

    content = f"attribute :{attr_name}, kind_of: {attr_type}"
    properties = _extract_resource_properties(content)

    # Should extract at least one property
    assert len(properties) >= 1
    # Should contain the attribute name
    assert any(p["name"] == attr_name for p in properties)


@given(
    action_name=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll"),
            min_codepoint=97,
            max_codepoint=122,
        ),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=50)
def test_extract_action_blocks(action_name):
    """Test extracting action blocks with random action names."""
    content = f"""
action :{action_name} do
  log "Action {action_name}"
end
"""
    actions = _extract_resource_actions(content)

    # Should extract the action
    assert action_name in actions["actions"]


@given(
    action_list=st.lists(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                min_codepoint=97,
                max_codepoint=122,
            ),
            min_size=1,
            max_size=15,
        ),
        min_size=1,
        max_size=5,
    )
)
@settings(max_examples=50)
def test_extract_lwrp_actions_declaration(action_list):
    """Test extracting LWRP actions declarations with random action names."""
    # Create actions declaration string
    actions_str = ", ".join(f":{action}" for action in action_list)
    content = f"actions {actions_str}"

    result = _extract_resource_actions(content)

    # Should extract all actions
    for action in action_list:
        assert action in result["actions"]


@given(
    default_val=st.sampled_from(["8080", "true", "false", "'default'", "[]", "{}"]),
)
@settings(max_examples=50)
def test_extract_property_with_defaults(default_val):
    """Test extracting properties with various default values."""
    content = f"property :config, String, default: {default_val}"
    properties = _extract_resource_properties(content)

    # Should extract the property with default
    assert len(properties) >= 1
    config_prop = next((p for p in properties if p["name"] == "config"), None)
    assert config_prop is not None
    assert "default" in config_prop


# InSpec Property-Based Tests


@given(st.text())
@settings(max_examples=50)
def test_parse_inspec_profile_handles_any_content(content):
    """Test that parse_inspec_profile doesn't crash on any file content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(content)
            f.flush()

            result = parse_inspec_profile(f.name)
            # Should always return a string (JSON or error)
            assert isinstance(result, str)
        finally:
            Path(f.name).unlink()


@given(st.text(min_size=1, max_size=1000))
@settings(max_examples=50)
def test_parse_inspec_control_handles_any_content(content):
    """Test that _parse_inspec_control handles any content without crashing."""
    result = _parse_inspec_control(content)
    # Should always return a list
    assert isinstance(result, list)


@given(
    control_id=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z"))
        | st.characters(min_codepoint=ord("A"), max_codepoint=ord("Z"))
        | st.characters(min_codepoint=ord("0"), max_codepoint=ord("9"))
        | st.just("-")
        | st.just("_"),
    ),
    resource_type=st.sampled_from(
        ["package", "service", "file", "directory", "user", "group", "port"]
    ),
    resource_name=st.text(
        min_size=1,
        max_size=20,
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.-_",
    ),
)
@settings(max_examples=50)
def test_parse_valid_inspec_control(control_id, resource_type, resource_name):
    """Test parsing well-formed InSpec controls with random data."""
    content = f"""
control '{control_id}' do
  title 'Test control'
  desc 'Test description'
  impact 1.0

  describe {resource_type}('{resource_name}') do
    it {{ should be_installed }}
  end
end
"""

    controls = _parse_inspec_control(content)

    # Should find exactly one control
    assert len(controls) == 1

    control = controls[0]
    assert control["id"] == control_id
    assert control["title"] == "Test control"
    assert control["desc"] == "Test description"
    assert control["impact"] == 1.0
    assert len(control["tests"]) == 1

    test = control["tests"][0]
    assert test["resource_type"] == resource_type
    assert test["resource_name"] == resource_name


@given(st.text())
@settings(max_examples=50)
def test_convert_inspec_to_test_handles_any_content(content):
    """Test that convert_inspec_to_test handles any file content without crashing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(content)
            f.flush()

            result_testinfra = convert_inspec_to_test(f.name, "testinfra")
            result_ansible = convert_inspec_to_test(f.name, "ansible_assert")

            # Should always return strings
            assert isinstance(result_testinfra, str)
            assert isinstance(result_ansible, str)
        finally:
            Path(f.name).unlink()


@given(
    format_type=st.sampled_from(["testinfra", "ansible_assert", "invalid_format"]),
)
@settings(max_examples=30)
def test_convert_inspec_different_formats(format_type):
    """Test InSpec conversion with different output formats."""
    simple_control = """
control 'test' do
  describe package('test-pkg') do
    it { should be_installed }
  end
end
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(simple_control)
            f.flush()

            result = convert_inspec_to_test(f.name, format_type)

            # Should always return a string
            assert isinstance(result, str)

            if format_type == "testinfra":
                # Valid testinfra should contain pytest imports
                if "Error:" not in result:
                    assert "import pytest" in result
            elif format_type == "ansible_assert":
                # Valid ansible should contain YAML
                if "Error:" not in result:
                    assert "---" in result
            else:
                # Invalid format should return error
                assert result.startswith("Error:")
        finally:
            Path(f.name).unlink()


@given(st.text())
@settings(max_examples=50)
def test_generate_inspec_from_recipe_handles_any_content(content):
    """Test that generate_inspec_from_recipe handles any recipe content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(content)
            f.flush()

            result = generate_inspec_from_recipe(f.name)

            # Should always return a string
            assert isinstance(result, str)
        finally:
            Path(f.name).unlink()


@given(
    resource_type=st.sampled_from(
        ["package", "service", "file", "directory", "user", "group"]
    ),
    resource_name=st.text(
        min_size=1,
        max_size=20,
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.-_",
    ),
    action=st.sampled_from(
        [":install", ":create", ":start", ":enable", "[:install]", "[:start, :enable]"]
    ),
)
@settings(max_examples=50)
def test_generate_inspec_from_valid_chef_resources(
    resource_type, resource_name, action
):
    """Test generating InSpec from well-formed Chef resources."""
    chef_content = f"""
{resource_type} '{resource_name}' do
  action {action}
end
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        try:
            f.write(chef_content)
            f.flush()

            result = generate_inspec_from_recipe(f.name)

            # Should generate InSpec content
            assert isinstance(result, str)

            # If successful, should contain control structure
            if "Error:" not in result:
                assert (
                    f"control '{resource_type}-" in result
                    or f"control '{resource_type}--" in result
                )
                assert (
                    f"describe {resource_type}(" in result or "describe file(" in result
                )
        finally:
            Path(f.name).unlink()


@given(
    matchers=st.lists(
        st.sampled_from(
            [
                "should be_installed",
                "should be_running",
                "should be_enabled",
                "should exist",
                "should be_file",
                "should be_directory",
            ]
        ),
        min_size=1,
        max_size=5,
    ),
)
@settings(max_examples=30)
def test_inspec_multiple_expectations(matchers):
    """Test InSpec parsing with multiple expectations."""
    content = """
control 'multi-test' do
  describe package('test') do
"""
    for matcher in matchers:
        content += f"    it {{ {matcher} }}\n"

    content += """  end
end
"""

    controls = _parse_inspec_control(content)

    # Should parse successfully
    assert len(controls) == 1
    control = controls[0]
    assert len(control["tests"]) == 1

    test = control["tests"][0]
    # Should capture all expectations
    assert len(test["expectations"]) == len(matchers)
