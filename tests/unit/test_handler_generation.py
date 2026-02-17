"""Tests for V2.2 handler generation module."""

from souschef.converters.handler_generation import (
    build_handler_routing_table,
    detect_handler_patterns,
    generate_ansible_handler_from_chef,
    generate_handler_conversion_report,
    parse_chef_handler_class,
)


class TestParseChefHandlerClass:
    """Tests for Chef handler class parsing."""

    def test_parse_basic_exception_handler(self) -> None:
        """Test parsing basic exception handler class."""
        handler_code = """
        class MyExceptionHandler < Chef::Handler
          def report
            puts "Exception occurred"
          end
        end
        """
        result = parse_chef_handler_class(handler_code)

        assert result["name"] == "MyExceptionHandler"
        assert result["type"] == "exception_handler"
        assert result["parent_class"] == "Chef::Handler"
        assert "report" in result["methods"]
        assert "end_of_converge" in result["callbacks"]

    def test_parse_report_handler(self) -> None:
        """Test parsing report handler class."""
        handler_code = """
        class MyReportHandler < Chef::Report::Handler
          def report_run
            puts "Converge complete"
          end
        end
        """
        result = parse_chef_handler_class(handler_code)

        assert result["name"] == "MyReportHandler"
        assert result["type"] == "report_handler"
        assert "report_run" in result["methods"]

    def test_parse_event_handler(self) -> None:
        """Test parsing event handler class."""
        handler_code = """
        class MyEventHandler < Chef::Event::Handler
          def handler_exception
            puts "Event occurred"
          end
        end
        """
        result = parse_chef_handler_class(handler_code)

        assert result["name"] == "MyEventHandler"
        assert result["type"] == "event_handler"

    def test_parse_handler_with_attributes(self) -> None:
        """Test parsing handler with attributes."""
        handler_code = """
        class MyHandler < Chef::Handler
          attr_reader :config
          attr_writer :status
          attr_accessor :enabled

          def report
            puts config
          end
        end
        """
        result = parse_chef_handler_class(handler_code)

        assert "config" in result["attributes"]
        assert "status" in result["attributes"]
        assert "enabled" in result["attributes"]

    def test_parse_handler_with_exceptions(self) -> None:
        """Test parsing handler with exception handling."""
        handler_code = """
        class MyHandler < Chef::Handler
          def report
            begin
              do_something
            rescue StandardError => e
              handle_error(e)
            rescue IOError => io_e
              handle_io_error(io_e)
            end
          end
        end
        """
        result = parse_chef_handler_class(handler_code)

        assert "StandardError" in result["exceptions_handled"]
        assert "IOError" in result["exceptions_handled"]

    def test_parse_empty_handler(self) -> None:
        """Test parsing empty handler class."""
        handler_code = ""
        result = parse_chef_handler_class(handler_code)

        assert result["name"] == ""
        assert result["type"] == "unknown"
        assert result["methods"] == []


class TestDetectHandlerPatterns:
    """Tests for handler pattern detection."""

    def test_detect_exception_handler_registration(self) -> None:
        """Test detecting exception handler registration pattern."""
        recipe_code = """
        run_context.exception_handlers.register(MyHandler.new)
        """
        patterns = detect_handler_patterns(recipe_code)

        assert len(patterns) == 1
        assert patterns[0]["pattern"] == "exception_handler_registration"
        assert patterns[0]["handler_class"] == "MyHandler"

    def test_detect_notification_handler(self) -> None:
        """Test detecting notification handler pattern."""
        recipe_code = """
        package 'apache2' do
          action :install
          notifies :restart, 'service[apache2]', :immediately
        end
        """
        patterns = detect_handler_patterns(recipe_code)

        notification_patterns = [
            p for p in patterns if p["pattern"] == "notification_handler"
        ]
        assert len(notification_patterns) > 0
        assert notification_patterns[0]["timing"] == "immediately"

    def test_detect_rescue_handler(self) -> None:
        """Test detecting rescue handler pattern."""
        recipe_code = """
        begin
          execute 'risky_command'
        rescue RuntimeError => e
          log "Error: #{e.message}"
        end
        """
        patterns = detect_handler_patterns(recipe_code)

        rescue_patterns = [p for p in patterns if p["pattern"] == "rescue_handler"]
        assert len(rescue_patterns) > 0
        assert rescue_patterns[0]["exception_type"] == "RuntimeError"

    def test_detect_log_handler(self) -> None:
        """Test detecting log handler pattern."""
        recipe_code = """
        Chef::Log.info("Starting converge")
        Chef::Log.warn("Deprecation warning")
        Chef::Log.error("An error occurred")
        """
        patterns = detect_handler_patterns(recipe_code)

        log_patterns = [p for p in patterns if p["pattern"] == "log_handler"]
        assert len(log_patterns) >= 2
        assert "info" in [p.get("level") for p in log_patterns]
        assert "warn" in [p.get("level") for p in log_patterns]

    def test_detect_multiple_patterns(self) -> None:
        """Test detecting multiple handler patterns."""
        recipe_code = """
        run_context.exception_handlers.register(MyHandler.new)

        package 'httpd' do
          notifies :restart, 'service[httpd]', :delayed
        end

        begin
          execute 'test'
        rescue StandardError => e
          puts e
        end

        Chef::Log.error("Failed")
        """
        patterns = detect_handler_patterns(recipe_code)

        assert len(patterns) >= 3
        pattern_types = {p["pattern"] for p in patterns}
        assert "exception_handler_registration" in pattern_types
        assert "notification_handler" in pattern_types
        assert "log_handler" in pattern_types


class TestGenerateAnsibleHandlerFromChef:
    """Tests for Ansible handler YAML generation."""

    def test_generate_basic_handler(self) -> None:
        """Test generating basic Ansible handler YAML."""
        handler_info = {
            "name": "MyHandler",
            "type": "exception_handler",
            "parent_class": "Chef::Handler",
            "methods": ["report"],
            "attributes": [],
            "exceptions_handled": [],
            "callbacks": ["end_of_converge"],
        }

        yaml_output = generate_ansible_handler_from_chef(handler_info)

        assert "handlers:" in yaml_output
        assert "MyHandler_handler" in yaml_output
        assert "end_of_converge" in yaml_output
        assert "debug:" in yaml_output

    def test_generate_handler_with_exceptions(self) -> None:
        """Test generating handler YAML with exception handling."""
        handler_info = {
            "name": "ErrorHandler",
            "type": "exception_handler",
            "parent_class": "Chef::Handler",
            "methods": ["report"],
            "attributes": [],
            "exceptions_handled": ["StandardError", "IOError"],
            "callbacks": [],
        }

        yaml_output = generate_ansible_handler_from_chef(handler_info)

        assert "rescue:" in yaml_output
        assert "ErrorHandler_handler" in yaml_output

    def test_generate_handler_without_callbacks(self) -> None:
        """Test handler generation with no callbacks."""
        handler_info = {
            "name": "SimpleHandler",
            "type": "unknown",
            "parent_class": "CustomHandler",
            "methods": [],
            "attributes": [],
            "exceptions_handled": [],
            "callbacks": [],
        }

        yaml_output = generate_ansible_handler_from_chef(handler_info)

        assert "default_handler" in yaml_output
        assert "SimpleHandler_handler" in yaml_output


class TestBuildHandlerRoutingTable:
    """Tests for handler routing table building."""

    def test_build_routing_from_patterns(self) -> None:
        """Test building routing table from handler patterns."""
        patterns = [
            {
                "pattern": "exception_handler_registration",
                "handler_class": "MyHandler",
                "location": 0,
            },
            {
                "pattern": "notification_handler",
                "action": "restart",
                "resource_type": "service",
                "resource_name": "httpd",
                "timing": "immediately",
                "location": 50,
            },
        ]

        routing = build_handler_routing_table(patterns)

        assert "exception_routes" in routing
        assert "notification_routes" in routing
        assert routing["summary"]["total_patterns"] == 2
        assert routing["summary"]["exception_handlers"] == 1
        assert routing["summary"]["notification_handlers"] == 1

    def test_build_routing_with_rescue_handlers(self) -> None:
        """Test routing table with rescue handlers."""
        patterns = [
            {
                "pattern": "rescue_handler",
                "exception_type": "RuntimeError",
                "variable": "e",
                "location": 0,
            }
        ]

        routing = build_handler_routing_table(patterns)

        assert routing["summary"]["rescue_handlers"] == 1
        assert "RuntimeError" in routing["exception_routes"]

    def test_build_routing_with_log_handlers(self) -> None:
        """Test routing table with log handlers."""
        patterns = [
            {
                "pattern": "log_handler",
                "level": "info",
                "message": "Test",
                "location": 0,
            },
            {
                "pattern": "log_handler",
                "level": "error",
                "message": "Error",
                "location": 50,
            },
        ]

        routing = build_handler_routing_table(patterns)

        assert routing["summary"]["log_handlers"] == 2
        assert "info" in routing["event_routes"]
        assert "error" in routing["event_routes"]

    def test_build_empty_routing_table(self) -> None:
        """Test building routing table with no patterns."""
        patterns: list = []

        routing = build_handler_routing_table(patterns)

        assert routing["summary"]["total_patterns"] == 0
        assert len(routing["exception_routes"]) == 0
        assert len(routing["notification_routes"]) == 0


class TestGenerateHandlerConversionReport:
    """Tests for handler conversion report generation."""

    def test_generate_basic_report(self) -> None:
        """Test generating basic conversion report."""
        handler_info = {
            "name": "MyHandler",
            "type": "exception_handler",
            "parent_class": "Chef::Handler",
            "methods": ["report"],
            "attributes": ["config"],
            "exceptions_handled": ["StandardError"],
            "callbacks": ["end_of_converge"],
        }
        routing = {
            "summary": {
                "total_patterns": 1,
                "exception_handlers": 1,
                "notification_handlers": 0,
                "rescue_handlers": 0,
                "log_handlers": 0,
            },
            "event_routes": {},
            "exception_routes": {},
            "notification_routes": {},
        }

        report = generate_handler_conversion_report(
            "/path/to/handler.rb", handler_info, routing
        )

        assert "# Handler Conversion Report" in report
        assert "MyHandler" in report
        assert "exception_handler" in report
        assert "Chef::Handler" in report
        assert "Methods" in report
        assert "report" in report
        assert "Attributes" in report
        assert "config" in report
        assert "Exceptions Handled" in report
        assert "StandardError" in report
        assert "Callbacks" in report
        assert "end_of_converge" in report
        assert "Conversion Recommendations" in report
        assert "```yaml" in report

    def test_report_without_exceptions_or_attributes(self) -> None:
        """Test report with minimal handler info."""
        handler_info = {
            "name": "SimpleHandler",
            "type": "unknown",
            "parent_class": "CustomHandler",
            "methods": [],
            "attributes": [],
            "exceptions_handled": [],
            "callbacks": [],
        }
        routing = {"summary": {"total_patterns": 0}, "event_routes": {}}

        report = generate_handler_conversion_report(
            "/path/to/handler.rb", handler_info, routing
        )

        assert "SimpleHandler" in report
        assert "# Handler Conversion Report" in report
        assert "Ansible Conversion Output" in report

    def test_report_includes_recommendations(self) -> None:
        """Test that report includes type-specific recommendations."""
        handler_info = {
            "name": "ReportHandler",
            "type": "report_handler",
            "parent_class": "Chef::Report::Handler",
            "methods": [],
            "attributes": [],
            "exceptions_handled": [],
            "callbacks": [],
        }
        routing = {"summary": {"total_patterns": 0}}

        report = generate_handler_conversion_report(
            "/path/to/handler.rb", handler_info, routing
        )

        assert "callback plugin" in report or "report" in report


class TestHandlerIntegration:
    """Integration tests for handler conversion workflow."""

    def test_full_handler_conversion_workflow(self) -> None:
        """Test complete handler parsing and conversion workflow."""
        handler_code = """
        class NotificationHandler < Chef::Handler
          attr_reader :run_status

          def report
            log_event
          end

          private

          def log_event
            Chef::Log.info("Converge completed")
          end
        end
        """

        # Parse handler
        handler_info = parse_chef_handler_class(handler_code)
        assert handler_info["name"] == "NotificationHandler"
        assert handler_info["type"] == "exception_handler"
        assert "report" in handler_info["methods"]

        # Generate Ansible YAML
        yaml_output = generate_ansible_handler_from_chef(handler_info)
        assert "NotificationHandler_handler" in yaml_output

        # Generate report
        routing = {"summary": {"total_patterns": 0}}
        report = generate_handler_conversion_report(
            "/test/handler.rb", handler_info, routing
        )
        assert "NotificationHandler" in report

    def test_handler_pattern_detection_and_routing(self) -> None:
        """Test pattern detection and routing table building."""
        recipe_code = """
        run_context.exception_handlers.register(MyHandler.new)

        service 'nginx' do
          action :enable
          notifies :run, 'execute[reload_nginx]', :delayed
        end

        begin
          execute 'test_command'
        rescue Errno::ENOENT => e
          Chef::Log.error("File not found: #{e}")
        end
        """

        # Detect patterns
        patterns = detect_handler_patterns(recipe_code)
        assert len(patterns) >= 3

        # Build routing
        routing = build_handler_routing_table(patterns)
        assert routing["summary"]["exception_handlers"] >= 1
        assert routing["summary"]["notification_handlers"] >= 1
        assert routing["summary"]["rescue_handlers"] >= 1
