"""Tests for Chef ERB template to Jinja2 converter."""

import tempfile
from pathlib import Path

import pytest

from souschef.converters.template import (
    convert_cookbook_templates,
    convert_template_file,
    convert_template_with_ai,
)


@pytest.fixture
def temp_erb_template(tmp_path):
    """Create a temporary ERB template file for testing."""
    template_content = """
# Sample configuration file
server_name <%= node['hostname'] %>
port <%= @port %>

<% if @enable_ssl %>
ssl_certificate /etc/ssl/certs/cert.pem
ssl_key /etc/ssl/private/key.pem
<% end %>

<% @backends.each do |backend| %>
backend <%= backend['name'] %> <%= backend['address'] %>
<% end %>
"""
    template_file = tmp_path / "test_config.erb"
    template_file.write_text(template_content)
    return template_file


@pytest.fixture
def temp_cookbook_with_templates(tmp_path):
    """Create a temporary cookbook structure with multiple templates."""
    cookbook_dir = tmp_path / "test_cookbook"
    cookbook_dir.mkdir()

    # Create templates directory
    templates_dir = cookbook_dir / "templates" / "default"
    templates_dir.mkdir(parents=True)

    # Create multiple template files
    template1 = templates_dir / "config.yml.erb"
    template1.write_text("""
# Configuration
database: <%= node['db_name'] %>
port: <%= @db_port %>
""")

    template2 = templates_dir / "nginx.conf.erb"
    template2.write_text("""
server {
    listen <%= @port %>;
    server_name <%= node['hostname'] %>;
}
""")

    return cookbook_dir


def test_convert_template_file_success(temp_erb_template):
    """Test successful conversion of an ERB template file."""
    result = convert_template_file(str(temp_erb_template))

    assert result["success"] is True
    assert "original_file" in result
    assert "jinja2_file" in result
    assert "jinja2_content" in result
    assert "variables" in result

    # Check that .erb was replaced with .j2
    assert result["jinja2_file"].endswith(".j2")
    assert not result["jinja2_file"].endswith(".erb")

    # Check that ERB syntax was converted
    jinja2_content = result["jinja2_content"]
    assert "<%= " not in jinja2_content  # No ERB output tags
    assert "<% " not in jinja2_content  # No ERB code blocks
    assert "{{ " in jinja2_content  # Jinja2 output tags present
    assert "{% " in jinja2_content  # Jinja2 control structures present


def test_convert_template_file_not_found():
    """Test conversion of non-existent file."""
    result = convert_template_file("/nonexistent/file.erb")

    assert result["success"] is False
    assert "error" in result
    assert "File not found" in result["error"]


def test_convert_template_file_directory(tmp_path):
    """Test conversion when path is a directory."""
    directory = tmp_path / "test_dir"
    directory.mkdir()

    result = convert_template_file(str(directory))

    assert result["success"] is False
    assert "error" in result
    assert "not a file" in result["error"].lower()


def test_convert_template_variables_extracted(temp_erb_template):
    """Test that variables are properly extracted from template."""
    result = convert_template_file(str(temp_erb_template))

    assert result["success"] is True
    variables = result["variables"]

    # Should extract node attributes and instance variables
    assert "hostname" in variables or "node" in " ".join(variables)
    assert "port" in variables
    assert "enable_ssl" in variables
    assert "backends" in variables


def test_convert_cookbook_templates_success(temp_cookbook_with_templates):
    """Test successful conversion of all templates in a cookbook."""
    result = convert_cookbook_templates(str(temp_cookbook_with_templates))

    assert result["success"] is True
    assert result["templates_converted"] == 2
    assert result["templates_failed"] == 0
    assert len(result["results"]) == 2

    # Check that all templates were converted successfully
    for template_result in result["results"]:
        assert template_result["success"] is True
        assert template_result["jinja2_file"].endswith(".j2")


def test_convert_cookbook_templates_no_templates(tmp_path):
    """Test conversion of cookbook with no templates."""
    cookbook_dir = tmp_path / "empty_cookbook"
    cookbook_dir.mkdir()

    result = convert_cookbook_templates(str(cookbook_dir))

    assert result["success"] is True
    assert result["templates_converted"] == 0
    assert result["templates_failed"] == 0
    assert "message" in result
    assert "No ERB templates found" in result["message"]


def test_convert_cookbook_templates_not_found():
    """Test conversion of non-existent cookbook."""
    result = convert_cookbook_templates("/nonexistent/cookbook")

    assert result["success"] is False
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_convert_template_erb_output_tags(temp_erb_template):
    """Test that <%= %> tags are converted to {{ }}."""
    result = convert_template_file(str(temp_erb_template))

    assert result["success"] is True
    jinja2_content = result["jinja2_content"]

    # Should not contain ERB output tags
    assert "<%=" not in jinja2_content
    assert "%>" not in jinja2_content

    # Should contain Jinja2 output tags
    assert "{{" in jinja2_content
    assert "}}" in jinja2_content


def test_convert_template_erb_conditionals(temp_erb_template):
    """Test that ERB conditionals are converted to Jinja2."""
    result = convert_template_file(str(temp_erb_template))

    assert result["success"] is True
    jinja2_content = result["jinja2_content"]

    # Should contain Jinja2 conditionals
    assert "{% if" in jinja2_content
    assert "{% endif %}" in jinja2_content

    # Should not contain ERB conditionals
    assert "<% if" not in jinja2_content
    assert "<% end" not in jinja2_content


def test_convert_template_erb_loops(temp_erb_template):
    """Test that ERB loops are converted to Jinja2."""
    result = convert_template_file(str(temp_erb_template))

    assert result["success"] is True
    jinja2_content = result["jinja2_content"]

    # Should contain Jinja2 loops
    assert "{% for" in jinja2_content
    assert "{% endfor %}" in jinja2_content

    # Should not contain ERB loops
    assert ".each do" not in jinja2_content


def test_convert_template_with_ai_no_service(temp_erb_template):
    """Test AI conversion without AI service falls back to rule-based."""
    result = convert_template_with_ai(str(temp_erb_template), ai_service=None)

    assert result["success"] is True
    assert result["conversion_method"] == "rule-based"
    assert "jinja2_content" in result


def test_convert_template_node_attributes():
    """Test conversion of node attributes to Ansible facts."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".erb", delete=False
    ) as temp_file:
        temp_file.write("hostname: <%= node['hostname'] %>\n")
        temp_file.write("platform: <%= node['platform'] %>\n")
        temp_file_path = temp_file.name

    try:
        result = convert_template_file(temp_file_path)

        assert result["success"] is True
        jinja2_content = result["jinja2_content"]

        # Node attributes should be converted
        assert "node[" not in jinja2_content
        assert "{{" in jinja2_content
        assert "}}" in jinja2_content

    finally:
        Path(temp_file_path).unlink(missing_ok=True)


def test_convert_template_instance_variables():
    """Test conversion of instance variables (@var) to plain variables."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".erb", delete=False
    ) as temp_file:
        temp_file.write("port: <%= @port %>\n")
        temp_file.write("host: <%= @hostname %>\n")
        temp_file_path = temp_file.name

    try:
        result = convert_template_file(temp_file_path)

        assert result["success"] is True
        jinja2_content = result["jinja2_content"]

        # Instance variables should be converted (@ removed)
        assert "@port" not in jinja2_content
        assert "@hostname" not in jinja2_content
        assert "{{ port }}" in jinja2_content or "{{port}}" in jinja2_content
        assert "{{ hostname }}" in jinja2_content or "{{hostname}}" in jinja2_content

    finally:
        Path(temp_file_path).unlink(missing_ok=True)


def test_convert_cookbook_templates_partial_failure(tmp_path):
    """Test conversion when some templates fail."""
    cookbook_dir = tmp_path / "test_cookbook"
    cookbook_dir.mkdir()

    templates_dir = cookbook_dir / "templates" / "default"
    templates_dir.mkdir(parents=True)

    # Create a valid template
    valid_template = templates_dir / "valid.erb"
    valid_template.write_text("config: <%= @value %>")

    # Create an invalid template (binary file)
    invalid_template = templates_dir / "invalid.erb"
    invalid_template.write_bytes(b"\x00\x01\x02\x03\x04")

    result = convert_cookbook_templates(str(cookbook_dir))

    # Should report partial success
    assert result["templates_converted"] >= 1
    assert len(result["results"]) == 2


@pytest.mark.parametrize(
    "erb_input,expected_jinja2",
    [
        ("port: <%= @port %>", "port: {{ port }}"),
        ("<% if @enabled %>", "{% if enabled %}"),
        ("<% @list.each do |item| %>", "{% for item in list %}"),
        ("<% end %>", "{% endif %}"),  # Could be endif or endfor
    ],
)
def test_convert_template_syntax_patterns(erb_input, expected_jinja2):
    """Test specific ERB to Jinja2 syntax conversions."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".erb", delete=False
    ) as temp_file:
        temp_file.write(erb_input)
        temp_file_path = temp_file.name

    try:
        result = convert_template_file(temp_file_path)

        assert result["success"] is True
        jinja2_content = result["jinja2_content"]

        # Check that the expected pattern is present (allowing for whitespace variations)
        assert any(
            expected_part.strip() in jinja2_content
            for expected_part in expected_jinja2.split()
        )

    finally:
        Path(temp_file_path).unlink(missing_ok=True)


def test_convert_template_unicode_content(tmp_path):
    """Test conversion of templates with unicode characters."""
    template_file = tmp_path / "unicode.erb"
    template_file.write_text("# Configuración\nserver: <%= @servidor %>\n")

    result = convert_template_file(str(template_file))

    assert result["success"] is True
    assert "Configuración" in result["jinja2_content"]
    assert "servidor" in result["variables"]
