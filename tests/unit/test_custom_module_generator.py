"""Tests for V2.2 custom module generator."""

from souschef.converters.custom_module_generator import (
    analyse_resource_complexity,
    build_module_collection,
    extract_module_interface,
    generate_ansible_module_scaffold,
    generate_module_documentation,
    generate_module_manifest,
    validate_module_code,
)


class TestAnalyseResourceComplexity:
    """Tests for resource complexity analysis."""

    def test_simple_resource_no_custom_module(self) -> None:
        """Test simple resource doesn't need custom module."""
        resource_body = """
        package 'apache2' do
          action :install
        end
        """
        result = analyse_resource_complexity(resource_body)

        assert result["needs_custom_module"] is False
        assert result["complexity_score"] < 3

    def test_complex_resource_with_ruby_block(self) -> None:
        """Test resource with ruby block increases complexity."""
        resource_body = """
        ruby_block 'complex_logic' do
          block do
            # Complex Ruby code
          end
        end
        """
        result = analyse_resource_complexity(resource_body)

        assert result["complexity_score"] >= 3
        assert "ruby_logic" in result["custom_logic_required"]

    def test_resource_with_multiple_actions(self) -> None:
        """Test resource with multiple actions."""
        resource_body = """
        action :start do
          # Start logic
        end

        action :restart do
          # Restart logic
        end

        action :reload do
          # Reload logic
        end
        """
        result = analyse_resource_complexity(resource_body)

        assert "multiple_actions" in result["custom_logic_required"]

    def test_resource_with_state_tracking(self) -> None:
        """Test resource with converge_if_changed."""
        resource_body = """
        property :config_content

        action :run do
          converge_if_changed :config_content
        end
        """
        result = analyse_resource_complexity(resource_body)

        assert "state_tracking" in result["custom_logic_required"]

    def test_complexity_score_calculation(self) -> None:
        """Test complexity score is calculated correctly."""
        resource_body = """
        ruby_block 'test' do
          block { puts 'test' }
        end

        action :custom do
        end

        action :other do
        end

        property :validation
        """
        result = analyse_resource_complexity(resource_body)

        # ruby_block (3) >= minimum threshold
        assert result["complexity_score"] >= 3
        assert result["needs_custom_module"] is True
        assert result["estimated_module_size"] > 150


class TestExtractModuleInterface:
    """Tests for module interface extraction."""

    def test_extract_resource_type(self) -> None:
        """Test extracting resource type."""
        resource_body = """
        resource_name :my_resource

        property :name
        property :path
        """
        interface = extract_module_interface(resource_body)

        assert interface["resource_type"] == "my_resource"

    def test_extract_properties(self) -> None:
        """Test extracting properties from resource."""
        resource_body = """
        property :name
        property :path, required: true
        property :owner
        """
        interface = extract_module_interface(resource_body)

        assert "name" in interface["properties"]
        assert "path" in interface["properties"]
        assert "owner" in interface["properties"]

    def test_extract_actions(self) -> None:
        """Test extracting actions from resource."""
        resource_body = """
        actions :create, :delete, :update
        default_action :create
        """
        interface = extract_module_interface(resource_body)

        assert "create" in interface["actions"]
        assert "delete" in interface["actions"]
        assert "update" in interface["actions"]
        assert interface["defaults"]["action"] == "create"

    def test_extract_default_action(self) -> None:
        """Test extracting default action."""
        resource_body = """
        default_action :install
        """
        interface = extract_module_interface(resource_body)

        assert interface["defaults"]["action"] == "install"

    def test_interface_with_no_actions_specified(self) -> None:
        """Test interface defaults actions when none specified."""
        resource_body = """
        property :name
        """
        interface = extract_module_interface(resource_body)

        assert interface["actions"] == ["default"]


class TestGenerateAnsibleModuleScaffold:
    """Tests for Ansible module scaffold generation."""

    def test_generate_basic_module(self) -> None:
        """Test generating basic module scaffold."""
        interface = {
            "resource_type": "custom_service",
            "properties": {"name": {"type": "str"}, "port": {"type": "int"}},
            "actions": ["start", "stop"],
            "defaults": {},
        }

        module_code = generate_ansible_module_scaffold("custom_service", interface)

        assert "#!/usr/bin/python" in module_code
        assert "DOCUMENTATION" in module_code
        assert "EXAMPLES" in module_code
        assert "RETURN" in module_code
        assert "def main():" in module_code
        assert "AnsibleModule" in module_code
        assert "name:" in module_code

    def test_generated_module_has_properties(self) -> None:
        """Test that generated module includes properties."""
        interface = {
            "resource_type": "test",
            "properties": {"config": {"type": "str"}},
            "actions": ["default"],
            "defaults": {},
        }

        module_code = generate_ansible_module_scaffold("test_module", interface)

        assert "config" in module_code

    def test_module_has_execution_structure(self) -> None:
        """Test module has proper execution structure."""
        interface = {
            "resource_type": "service",
            "properties": {},
            "actions": ["start"],
            "defaults": {},
        }

        module_code = generate_ansible_module_scaffold("service", interface)

        assert "try:" in module_code
        assert "except" in module_code
        assert "module.exit_json" in module_code
        assert "module.fail_json" in module_code


class TestGenerateModuleDocumentation:
    """Tests for module documentation generation."""

    def test_generate_documentation(self) -> None:
        """Test generating module documentation."""
        interface = {
            "properties": {"name": {}, "path": {}},
            "actions": ["install", "remove"],
        }
        complexity = {
            "complexity_score": 5,
            "custom_logic_required": ["ruby_logic"],
            "estimated_module_size": 250,
        }

        doc = generate_module_documentation("my_module", interface, complexity)

        assert "# Custom Ansible Module: my_module" in doc
        assert "Overview" in doc
        assert "Complexity Analysis" in doc
        assert "5/10" in doc
        assert "Properties" in doc
        assert "name" in doc
        assert "path" in doc
        assert "Actions" in doc
        assert "install" in doc
        assert "Usage Example" in doc

    def test_documentation_includes_recommendations(self) -> None:
        """Test documentation includes implementation recommendations."""
        interface = {"properties": {}, "actions": []}
        complexity = {
            "complexity_score": 0,
            "custom_logic_required": [],
            "estimated_module_size": 0,
        }

        doc = generate_module_documentation("test", interface, complexity)

        assert "Implementation Notes" in doc
        assert "error handling" in doc


class TestGenerateModuleManifest:
    """Tests for module manifest generation."""

    def test_generate_manifest(self) -> None:
        """Test generating module manifest."""
        modules = ["module1", "module2", "module3"]
        manifest = generate_module_manifest("custom_resource", modules)

        assert manifest["namespace"] == "souschef"
        assert "custom_resource" in manifest["name"]
        assert manifest["version"] == "1.0.0"
        assert len(manifest["modules"]) == 3
        assert "module1" in manifest["modules"]

    def test_manifest_has_metadata(self) -> None:
        """Test manifest includes required metadata."""
        manifest = generate_module_manifest("test", [])

        assert "author" in manifest
        assert "license" in manifest
        assert "repository" in manifest
        assert "documentation" in manifest


class TestValidateModuleCode:
    """Tests for module code validation."""

    def test_validate_complete_module(self) -> None:
        """Test validating complete module code."""
        module_code = '''#!/usr/bin/python
"""Module documentation"""

DOCUMENTATION = r"""
---
module: test
"""

EXAMPLES = r"""
- name: test
"""

from ansible.module_utils.basic import AnsibleModule

def main():
    try:
        module.exit_json(changed=False)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == "__main__":
    main()
'''
        validation = validate_module_code(module_code)

        assert validation["valid"] is True
        assert validation["checklist"]["has_documentation"] is True
        assert validation["checklist"]["has_examples"] is True
        assert validation["checklist"]["has_error_handling"] is True
        assert validation["checklist"]["has_return_statement"] is True

    def test_validate_incomplete_module(self) -> None:
        """Test validating incomplete module."""
        module_code = """
def main():
    pass

if __name__ == "__main__":
    main()
"""
        validation = validate_module_code(module_code)

        assert validation["checklist"]["has_documentation"] is False
        assert validation["checklist"]["has_examples"] is False
        assert len(validation["warnings"]) > 0


class TestBuildModuleCollection:
    """Tests for building module collection."""

    def test_build_collection_with_complex_resources(self) -> None:
        """Test building collection with multiple resources."""
        resources = [
            {
                "name": "complex_resource1",
                "body": "ruby_block 'test' do\nblock { puts 'test' }\nend",
            },
            {
                "name": "complex_resource2",
                "body": "action :start do\nend\naction :stop do\nend",
            },
        ]

        collection = build_module_collection(resources)

        assert collection["collection_name"] == "souschef_custom"
        assert collection["summary"]["total_resources"] == 2
        assert collection["summary"]["modules_generated"] >= 1

    def test_collection_summary_statistics(self) -> None:
        """Test collection includes proper statistics."""
        resources = [
            {
                "name": "test1",
                "body": "ruby_block 'test' do\nblock { puts 'x' }\nend",
            },
        ]

        collection = build_module_collection(resources)

        assert "total_resources" in collection["summary"]
        assert "modules_generated" in collection["summary"]
        assert "total_lines_of_code" in collection["summary"]
        assert collection["summary"]["total_resources"] == 1

    def test_collection_with_no_complex_resources(self) -> None:
        """Test collection with simple resources."""
        resources = [
            {
                "name": "simple_package",
                "body": "package 'apache2' do\naction :install\nend",
            },
        ]

        collection = build_module_collection(resources)

        assert collection["summary"]["modules_generated"] == 0
        assert collection["summary"]["total_resources"] == 1


class TestCustomModuleIntegration:
    """Integration tests for custom module generation."""

    def test_full_workflow_resource_to_module(self) -> None:
        """Test complete workflow from resource to module."""
        resource_body = """
        resource_name :custom_deploy

        property :app_name, required: true
        property :version
        property :config_path

        action :deploy do
          ruby_block 'deploy_logic' do
            block do
              # Complex deployment logic
            end
          end
        end
        """

        # Analyse complexity
        complexity = analyse_resource_complexity(resource_body)
        assert complexity["needs_custom_module"] is True

        # Extract interface
        interface = extract_module_interface(resource_body)
        assert interface["resource_type"] == "custom_deploy"

        # Generate module
        module_code = generate_ansible_module_scaffold("custom_deploy", interface)
        assert "#!/usr/bin/python" in module_code

        # Generate documentation
        doc = generate_module_documentation("custom_deploy", interface, complexity)
        assert "custom_deploy" in doc

        # Validate module
        validation = validate_module_code(module_code)
        assert validation["valid"] is True
