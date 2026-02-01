"""Tests for AI Pydantic schemas."""

import pytest
from pydantic import ValidationError

from souschef.core.ai_schemas import (
    AnsibleHandler,
    AnsiblePlaybook,
    AnsibleTask,
    ConversionResult,
    TemplateConversion,
)


class TestAnsibleTask:
    """Tests for AnsibleTask schema."""

    def test_minimal_task(self):
        """Test creating a minimal task."""
        # Note: Pylance flags missing optional parameters, but Pydantic's Field(None, ...)
        # makes them optional. This is a Pylance limitation with Pydantic schemas.
        task = AnsibleTask(name="Install package", module="package")  # type: ignore[call-arg]
        assert task.name == "Install package"
        assert task.module == "package"
        assert task.parameters == {}
        assert task.when is None
        assert task.notify is None
        assert task.tags is None
        assert task.become is None
        assert task.register is None

    def test_full_task(self):
        """Test creating a task with all fields."""
        task = AnsibleTask(
            name="Install nginx",
            module="package",
            parameters={"name": "nginx", "state": "present"},
            when="ansible_os_family == 'Debian'",
            notify=["restart nginx"],
            tags=["packages", "nginx"],
            become=True,
            register="nginx_result",
        )
        assert task.name == "Install nginx"
        assert task.module == "package"
        assert task.parameters["name"] == "nginx"
        assert task.when == "ansible_os_family == 'Debian'"
        assert task.notify == ["restart nginx"]
        assert task.tags == ["packages", "nginx"]
        assert task.become is True
        assert task.register == "nginx_result"

    def test_task_missing_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            AnsibleTask()  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            AnsibleTask(name="Test")  # Missing module  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            AnsibleTask(module="package")  # Missing name  # type: ignore[call-arg]


class TestAnsibleHandler:
    """Tests for AnsibleHandler schema."""

    def test_minimal_handler(self):
        """Test creating a minimal handler."""
        handler = AnsibleHandler(name="restart nginx", module="service")
        assert handler.name == "restart nginx"
        assert handler.module == "service"
        assert handler.parameters == {}

    def test_full_handler(self):
        """Test creating a handler with parameters."""
        handler = AnsibleHandler(
            name="restart nginx",
            module="service",
            parameters={"name": "nginx", "state": "restarted"},
        )
        assert handler.name == "restart nginx"
        assert handler.module == "service"
        assert handler.parameters["name"] == "nginx"
        assert handler.parameters["state"] == "restarted"

    def test_handler_missing_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            AnsibleHandler()  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            AnsibleHandler(name="Test")  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            AnsibleHandler(module="service")  # type: ignore[call-arg]


class TestAnsiblePlaybook:
    """Tests for AnsiblePlaybook schema."""

    def test_minimal_playbook(self):
        """Test creating a minimal playbook."""
        playbook = AnsiblePlaybook(name="Test Playbook")  # type: ignore[call-arg]
        assert playbook.name == "Test Playbook"
        assert playbook.hosts == "all"
        assert playbook.become is None
        assert playbook.vars is None
        assert playbook.tasks == []
        assert playbook.handlers is None

    def test_full_playbook(self):
        """Test creating a complete playbook."""
        task = AnsibleTask(name="Install nginx", module="package")  # type: ignore[call-arg]
        handler = AnsibleHandler(name="restart nginx", module="service")

        playbook = AnsiblePlaybook(
            name="Web Server Setup",
            hosts="webservers",
            become=True,
            vars={"nginx_port": 80},
            tasks=[task],
            handlers=[handler],
        )

        assert playbook.name == "Web Server Setup"
        assert playbook.hosts == "webservers"
        assert playbook.become is True
        assert playbook.vars is not None
        assert playbook.vars["nginx_port"] == 80
        assert len(playbook.tasks) == 1
        assert playbook.tasks[0].name == "Install nginx"
        assert playbook.handlers is not None
        assert len(playbook.handlers) == 1
        assert playbook.handlers[0].name == "restart nginx"

    def test_playbook_with_multiple_tasks(self):
        """Test playbook with multiple tasks."""
        tasks = [
            AnsibleTask(name="Task 1", module="package"),  # type: ignore[call-arg]
            AnsibleTask(name="Task 2", module="service"),  # type: ignore[call-arg]
            AnsibleTask(name="Task 3", module="template"),  # type: ignore[call-arg]
        ]
        playbook = AnsiblePlaybook(name="Multi-task", tasks=tasks)  # type: ignore[call-arg]
        assert len(playbook.tasks) == 3
        assert playbook.tasks[0].name == "Task 1"
        assert playbook.tasks[1].name == "Task 2"
        assert playbook.tasks[2].name == "Task 3"

    def test_playbook_missing_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            AnsiblePlaybook()  # Missing name  # type: ignore[call-arg]


class TestConversionResult:
    """Tests for ConversionResult schema."""

    def test_minimal_conversion_result(self):
        """Test creating a minimal conversion result."""
        playbook = AnsiblePlaybook(name="Test")  # type: ignore[call-arg]
        result = ConversionResult(playbook=playbook)  # type: ignore[call-arg]
        assert result.playbook.name == "Test"
        assert result.notes is None
        assert result.confidence is None

    def test_full_conversion_result(self):
        """Test creating a complete conversion result."""
        task = AnsibleTask(name="Install package", module="package")  # type: ignore[call-arg]
        playbook = AnsiblePlaybook(name="Test", tasks=[task])  # type: ignore[call-arg]

        result = ConversionResult(
            playbook=playbook,
            notes=["Manual verification needed for X", "Check Y configuration"],
            confidence=0.85,
        )

        assert result.playbook.name == "Test"
        assert len(result.playbook.tasks) == 1
        assert result.notes is not None
        assert len(result.notes) == 2
        assert result.notes[0] == "Manual verification needed for X"
        assert result.confidence is not None
        assert abs(result.confidence - 0.85) < 0.001

    def test_confidence_validation(self):
        """Test confidence score validation."""
        playbook = AnsiblePlaybook(name="Test")  # type: ignore[call-arg]

        # Valid confidence scores
        result1 = ConversionResult(playbook=playbook, confidence=0.0)  # type: ignore[call-arg]
        assert result1.confidence is not None
        assert abs(result1.confidence - 0.0) < 0.001

        result2 = ConversionResult(playbook=playbook, confidence=1.0)  # type: ignore[call-arg]
        assert result2.confidence is not None
        assert abs(result2.confidence - 1.0) < 0.001

        result3 = ConversionResult(playbook=playbook, confidence=0.5)  # type: ignore[call-arg]
        assert result3.confidence is not None
        assert abs(result3.confidence - 0.5) < 0.001

        # Invalid confidence scores
        with pytest.raises(ValidationError):
            ConversionResult(playbook=playbook, confidence=-0.1)  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ConversionResult(playbook=playbook, confidence=1.5)  # type: ignore[call-arg]

    def test_conversion_result_missing_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ConversionResult()  # Missing playbook  # type: ignore[call-arg]


class TestTemplateConversion:
    """Tests for TemplateConversion schema."""

    def test_minimal_template_conversion(self):
        """Test creating a minimal template conversion."""
        conversion = TemplateConversion(jinja2_template="Hello {{ name }}")  # type: ignore[call-arg]
        assert conversion.jinja2_template == "Hello {{ name }}"
        assert conversion.variable_mappings is None
        assert conversion.notes is None

    def test_full_template_conversion(self):
        """Test creating a complete template conversion."""
        conversion = TemplateConversion(
            jinja2_template="Server: {{ server_name }}:{{ port }}",
            variable_mappings={
                "node['hostname']": "server_name",
                "node['port']": "port",
            },
            notes=["ERB syntax converted to Jinja2", "Verify variable scoping"],
        )  # type: ignore[call-arg]

        assert conversion.jinja2_template == "Server: {{ server_name }}:{{ port }}"
        assert conversion.variable_mappings is not None
        assert len(conversion.variable_mappings) == 2
        assert conversion.variable_mappings["node['hostname']"] == "server_name"
        assert conversion.notes is not None
        assert len(conversion.notes) == 2
        assert conversion.notes[0] == "ERB syntax converted to Jinja2"

    def test_complex_variable_mappings(self):
        """Test template conversion with complex variable mappings."""
        conversion = TemplateConversion(
            jinja2_template="Config content",
            variable_mappings={
                "node['app']['version']": "app_version",
                "node['app']['port']": "app_port",
                "node['app']['user']": "app_user",
            },
        )  # type: ignore[call-arg]  # type: ignore[call-arg]

        assert conversion.variable_mappings is not None
        assert len(conversion.variable_mappings) == 3
        assert conversion.variable_mappings["node['app']['version']"] == "app_version"

    def test_template_conversion_missing_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            TemplateConversion()  # Missing jinja2_template  # type: ignore[call-arg]


class TestSchemaIntegration:
    """Integration tests for schema composition."""

    def test_complete_conversion_workflow(self):
        """Test a complete conversion workflow using all schemas."""
        # Create tasks
        tasks = [
            AnsibleTask(
                name="Install nginx",
                module="package",
                parameters={"name": "nginx", "state": "present"},
                notify=["restart nginx"],
            ),  # type: ignore[call-arg]
            AnsibleTask(
                name="Configure nginx",
                module="template",
                parameters={
                    "src": "nginx.conf.j2",
                    "dest": "/etc/nginx/nginx.conf",
                },
                notify=["restart nginx"],
            ),  # type: ignore[call-arg]
        ]

        # Create handler
        handlers = [
            AnsibleHandler(
                name="restart nginx",
                module="service",
                parameters={"name": "nginx", "state": "restarted"},
            )
        ]

        # Create playbook
        playbook = AnsiblePlaybook(
            name="Nginx Setup",
            hosts="webservers",
            become=True,
            vars={"nginx_port": 80},
            tasks=tasks,
            handlers=handlers,
        )

        # Create conversion result
        result = ConversionResult(
            playbook=playbook,
            notes=["Verify nginx configuration paths", "Test on staging first"],
            confidence=0.9,
        )

        # Validate the complete structure
        assert result.playbook.name == "Nginx Setup"
        assert len(result.playbook.tasks) == 2
        assert result.playbook.handlers is not None
        assert len(result.playbook.handlers) == 1
        assert result.confidence is not None
        assert abs(result.confidence - 0.9) < 0.001
        assert result.notes is not None
        assert len(result.notes) == 2

    def test_serialization(self):
        """Test that schemas can be serialized to dict."""
        task = AnsibleTask(
            name="Test task", module="package", parameters={"name": "nginx"}
        )  # type: ignore[call-arg]
        task_dict = task.model_dump()

        assert task_dict["name"] == "Test task"
        assert task_dict["module"] == "package"
        assert task_dict["parameters"]["name"] == "nginx"
