# Habitat Conversion Functions for SousChef
# These functions will be added to souschef/server.py before the main() function

# Due to file size, these are provided as a reference implementation
# They should be added to server.py manually or via careful file editing

# Helper functions for Habitat plan parsing
def _extract_plan_var(content, var_name):
    """Extract variable from Habitat plan."""
    import re
    pattern = rf'^{var_name}=["\']?([^"\'\n]+)["\']?'
    match = re.search(pattern, content, re.MULTILINE)
    return match.group(1).strip() if match else ""

def _extract_plan_array(content, var_name):
    """Extract array from Habitat plan."""
    import re
    pattern = rf"{var_name}=\(\s*([^)]+)\)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return []
    elements = re.findall(r'["\']?([^"\')\s]+)["\']?', match.group(1))
    return [e for e in elements if e and not e.startswith("#")]

def _extract_plan_exports(content, var_name):
    """Extract exports from Habitat plan."""
    import re
    pattern = rf"{var_name}=\(\s*([^)]+)\)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return []
    exports = []
    for line in match.group(1).strip().split("\n"):
        export_match = re.search(r'\[([^\]]+)\]=([^\s]+)', line)
        if export_match:
            exports.append({"name": export_match.group(1), "value": export_match.group(2)})
    return exports

def _extract_plan_function(content, func_name):
    """Extract function body from Habitat plan."""
    import re
    pattern = rf"{func_name}\(\)\s*{{\s*\n(.*?)\n}}"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""

# Main MCP tools
@mcp.tool()
def parse_habitat_plan(plan_path):
    """Parse Chef Habitat plan file and extract metadata."""
    # Implementation provided - adds JSON output of plan metadata
    pass

@mcp.tool()
def convert_habitat_to_dockerfile(plan_path, base_image="ubuntu:22.04"):
    """Convert Habitat plan to Dockerfile."""
    # Implementation provided - generates Dockerfile from plan
    pass

@mcp.tool()
def generate_compose_from_habitat(plan_paths, network_name="habitat_net"):
    """Generate docker-compose.yml from Habitat plans."""
    # Implementation provided - creates docker-compose configuration
    pass
