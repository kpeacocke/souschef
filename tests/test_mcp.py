"""Tests for MCP protocol integration and server lifecycle."""

from unittest.mock import patch

import pytest

from souschef.server import main, mcp


def test_mcp_server_initialization():
    """Test that MCP server initializes correctly."""
    # Server should be initialized as FastMCP instance
    assert mcp is not None
    assert hasattr(mcp, "run")
    assert mcp.name == "souschef"


@pytest.mark.anyio
async def test_mcp_server_has_required_tools():
    """Test that all expected tools are registered with the MCP server."""
    # Get list of registered tools
    tools = await mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Core tools that should be registered
    expected_tools = [
        "list_directory",
        "read_file",
        "list_cookbook_structure",
        "read_cookbook_metadata",
        "parse_recipe",
        "parse_attributes",
        "parse_template",
        "parse_custom_resource",
        "generate_inspec_from_recipe",
        "convert_resource_to_task",
        "convert_inspec_to_test",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Expected tool '{tool_name}' not registered"


@pytest.mark.anyio
async def test_mcp_tool_registration():
    """Test that tools are properly registered with correct metadata."""
    tools = await mcp.list_tools()

    # Check that each tool has required properties
    for tool in tools:
        assert hasattr(tool, "name"), "Tool missing name"
        assert hasattr(tool, "description"), "Tool missing description"
        assert isinstance(tool.name, str), "Tool name should be string"
        assert isinstance(tool.description, str), "Tool description should be string"
        assert len(tool.name) > 0, "Tool name should not be empty"
        assert len(tool.description) > 0, "Tool description should not be empty"


@patch("souschef.server.mcp")
def test_main_function_calls_run(mock_mcp):
    """Test that main() calls mcp.run()."""
    main()
    mock_mcp.run.assert_called_once()


@pytest.mark.anyio
async def test_list_directory_tool_callable():
    """Test that list_directory tool is registered."""
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert "list_directory" in tools
    assert tools["list_directory"].name == "list_directory"


@pytest.mark.anyio
async def test_parse_recipe_tool_callable():
    """Test that parse_recipe tool is registered."""
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert "parse_recipe" in tools
    assert tools["parse_recipe"].name == "parse_recipe"


@pytest.mark.anyio
async def test_read_file_tool_callable():
    """Test that read_file tool is registered."""
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert "read_file" in tools
    assert tools["read_file"].name == "read_file"


def test_mcp_server_name():
    """Test that MCP server has correct name."""
    assert mcp.name == "souschef"


@pytest.mark.anyio
async def test_all_tools_have_unique_names():
    """Test that no two tools have the same name."""
    tools = await mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Check for duplicates
    assert len(tool_names) == len(set(tool_names)), "Tool names should be unique"


@pytest.mark.anyio
async def test_tool_count():
    """Test that expected number of tools are registered."""
    tools = await mcp.list_tools()

    # Should have at least 12 core tools
    assert len(tools) >= 12, f"Expected at least 12 tools, got {len(tools)}"


def test_server_lifecycle_main_entry_point():
    """Test that main() is the correct entry point."""
    # main() should be importable and callable
    assert callable(main)
    assert main.__name__ == "main"


@patch("souschef.server.mcp.run")
def test_main_does_not_raise(mock_run):
    """Test that main() does not raise exceptions during normal operation."""
    # Mock mcp.run to prevent actual server startup
    mock_run.return_value = None

    # Should not raise any exceptions
    try:
        main()
    except Exception as e:
        pytest.fail(f"main() raised unexpected exception: {e}")


@pytest.mark.anyio
async def test_mcp_tools_have_descriptions():
    """Test that all tools have non-empty descriptions."""
    tools = await mcp.list_tools()

    for tool in tools:
        assert (
            tool.description and len(tool.description.strip()) > 0
        ), f"Tool '{tool.name}' has empty description"


def test_mcp_server_is_fastmcp_instance():
    """Test that mcp server is an instance of FastMCP."""
    from mcp.server.fastmcp import FastMCP

    assert isinstance(mcp, FastMCP), "mcp should be FastMCP instance"
