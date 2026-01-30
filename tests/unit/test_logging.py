"""Tests for structured logging functionality."""

import json
import logging

import pytest

from souschef.core.logging import (
    LogContext,
    StructuredFormatter,
    clear_context,
    configure_logging,
    get_logger,
    log_operation,
    set_context,
)


class TestStructuredFormatter:
    """Test structured log formatting."""

    def test_text_format_basic(self):
        """Test basic text formatting."""
        formatter = StructuredFormatter(
            fmt="%(levelname)s - %(message)s",
            json_format=False,
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "INFO - Test message" in result

    def test_text_format_with_context(self):
        """Test text formatting with context variables."""
        set_context(
            request_id="req-123",
            operation="convert_recipe",
            cookbook="apache",
        )

        formatter = StructuredFormatter(
            fmt="%(levelname)s - %(message)s",
            json_format=False,
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "request_id=req-123" in result
        assert "operation=convert_recipe" in result
        assert "cookbook=apache" in result

        clear_context()

    def test_json_format_basic(self):
        """Test basic JSON formatting."""
        formatter = StructuredFormatter(json_format=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "test"
        assert log_data["line"] == 10

    def test_json_format_with_context(self):
        """Test JSON formatting with context variables."""
        set_context(
            request_id="req-456",
            operation="parse_metadata",
            cookbook="nginx",
        )

        formatter = StructuredFormatter(json_format=True)
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=20,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["request_id"] == "req-456"
        assert log_data["operation"] == "parse_metadata"
        assert log_data["cookbook"] == "nginx"

        clear_context()

    def test_json_format_with_exception(self):
        """Test JSON formatting with exception info."""
        formatter = StructuredFormatter(json_format=True)

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=30,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

            result = formatter.format(record)
            log_data = json.loads(result)

            assert log_data["level"] == "ERROR"
            assert log_data["message"] == "Error occurred"
            assert "exception" in log_data
            assert "ValueError: Test error" in log_data["exception"]

    def test_json_format_with_extra_fields(self):
        """Test JSON formatting with extra fields."""
        formatter = StructuredFormatter(json_format=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=40,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Add extra fields
        record.user_id = "user-123"
        record.duration_ms = 150

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["user_id"] == "user-123"
        assert log_data["duration_ms"] == 150

    def test_text_format_without_context(self):
        """Test text formatting when no context is set."""
        clear_context()

        formatter = StructuredFormatter(
            fmt="%(levelname)s - %(message)s",
            json_format=False,
        )
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=50,
            msg="Debug message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "DEBUG - Debug message" in result
        assert "request_id=" not in result
        assert "operation=" not in result


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_configure_logging_default(self):
        """Test default logging configuration."""
        configure_logging()
        logger = logging.getLogger()

        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_configure_logging_debug_level(self):
        """Test configuring DEBUG level."""
        configure_logging(level="DEBUG")
        logger = logging.getLogger()

        assert logger.level == logging.DEBUG

    def test_configure_logging_json_format(self):
        """Test configuring JSON format."""
        configure_logging(json_format=True)
        logger = logging.getLogger()

        # Check that formatter is StructuredFormatter with JSON
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, StructuredFormatter)
        assert handler.formatter.json_format is True

    def test_configure_logging_with_file(self, tmp_path):
        """Test configuring with file output."""
        log_file = tmp_path / "test.log"
        configure_logging(log_file=str(log_file))

        logger = logging.getLogger()
        logger.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_get_logger(self):
        """Test getting logger instance."""
        logger = get_logger("souschef.test")

        assert logger.name == "souschef.test"
        assert isinstance(logger, logging.Logger)


class TestContextManagement:
    """Test context management functionality."""

    def test_set_context(self):
        """Test setting context variables."""
        set_context(
            request_id="req-789",
            operation="test_operation",
            cookbook="test_cookbook",
        )

        # Context should be set
        from souschef.core.logging import (
            cookbook_var,
            operation_var,
            request_id_var,
        )

        assert request_id_var.get() == "req-789"
        assert operation_var.get() == "test_operation"
        assert cookbook_var.get() == "test_cookbook"

        clear_context()

    def test_clear_context(self):
        """Test clearing context variables."""
        set_context(request_id="req-abc", operation="test")
        clear_context()

        from souschef.core.logging import operation_var, request_id_var

        assert request_id_var.get() is None
        assert operation_var.get() is None

    def test_log_context_manager(self):
        """Test LogContext context manager."""
        # Set initial context
        set_context(request_id="initial")

        with LogContext(
            request_id="ctx-123", operation="context_test", cookbook="test"
        ):
            from souschef.core.logging import (
                cookbook_var,
                operation_var,
                request_id_var,
            )

            # Context should be set within manager
            assert request_id_var.get() == "ctx-123"
            assert operation_var.get() == "context_test"
            assert cookbook_var.get() == "test"

        # Context should be restored after exit
        from souschef.core.logging import (
            cookbook_var,
            operation_var,
            request_id_var,
        )

        assert request_id_var.get() == "initial"
        assert operation_var.get() is None
        assert cookbook_var.get() is None

        clear_context()

    def test_log_context_nested(self):
        """Test nested LogContext managers."""
        with LogContext(request_id="outer"):
            from souschef.core.logging import request_id_var

            assert request_id_var.get() == "outer"

            with LogContext(request_id="inner"):
                assert request_id_var.get() == "inner"

            # Should restore outer context
            assert request_id_var.get() == "outer"

        # Should restore to None
        assert request_id_var.get() is None


class TestLogOperationDecorator:
    """Test log_operation decorator."""

    def test_log_operation_success(self, caplog):
        """Test decorator logs successful operation."""

        @log_operation("test_operation")
        def test_function():
            return "result"

        # Capture logs at the test module logger level
        with caplog.at_level(logging.INFO):
            result = test_function()

        assert result == "result"
        # Check captured records instead of text
        messages = [record.message for record in caplog.records]
        assert any("Starting test_operation" in msg for msg in messages)
        assert any("Completed test_operation" in msg for msg in messages)

    def test_log_operation_failure(self, caplog):
        """Test decorator logs failed operation."""

        @log_operation("failing_operation")
        def failing_function():
            raise ValueError("Test error")

        with caplog.at_level(logging.ERROR), pytest.raises(ValueError):
            failing_function()

        # Check captured records
        messages = [record.message for record in caplog.records]
        assert any(
            "Failed failing_operation" in msg and "Test error" in msg
            for msg in messages
        )

    def test_log_operation_with_context(self, caplog):
        """Test decorator with context set."""

        @log_operation("context_operation")
        def context_function():
            return "result"

        set_context(cookbook="test_cookbook")

        with caplog.at_level(logging.INFO):
            context_function()

        # Check captured records for context
        assert any(record.cookbook == "test_cookbook" for record in caplog.records)

        clear_context()

    def test_log_operation_preserves_function_metadata(self):
        """Test decorator preserves function metadata."""

        @log_operation("test_op")
        def documented_function():
            """Document function for testing."""
            pass

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "Document function for testing."


class TestIntegration:
    """Integration tests for structured logging."""

    def test_end_to_end_text_logging(self, tmp_path):
        """Test end-to-end text logging."""
        log_file = tmp_path / "integration.log"
        configure_logging(level="INFO", json_format=False, log_file=str(log_file))

        logger = get_logger("souschef.test")

        with LogContext(request_id="int-123", operation="integration_test"):
            logger.info("Starting test")
            logger.warning("Test warning")
            logger.info("Completed test")

        content = log_file.read_text()
        assert "Starting test" in content
        assert "Test warning" in content
        assert "request_id=int-123" in content
        assert "operation=integration_test" in content

    def test_end_to_end_json_logging(self, tmp_path):
        """Test end-to-end JSON logging."""
        log_file = tmp_path / "integration.json"
        configure_logging(level="DEBUG", json_format=True, log_file=str(log_file))

        logger = get_logger("souschef.test")

        with LogContext(cookbook="apache", operation="json_test"):
            logger.debug("Debug message")
            logger.info("Info message")

        content = log_file.read_text()
        lines = content.strip().split("\n")

        # Parse JSON logs
        log_entries = [json.loads(line) for line in lines]

        assert len(log_entries) == 2
        assert log_entries[0]["level"] == "DEBUG"
        assert log_entries[0]["message"] == "Debug message"
        assert log_entries[0]["cookbook"] == "apache"
        assert log_entries[1]["level"] == "INFO"
        assert log_entries[1]["operation"] == "json_test"

    def test_logging_with_exception_context(self, tmp_path):
        """Test logging exceptions with context."""
        log_file = tmp_path / "exception.log"
        configure_logging(level="ERROR", json_format=False, log_file=str(log_file))

        logger = get_logger("souschef.test")

        with LogContext(request_id="exc-123"):
            try:
                raise RuntimeError("Test exception")
            except RuntimeError:
                logger.exception("Exception occurred")

        content = log_file.read_text()
        assert "Exception occurred" in content
        assert "RuntimeError: Test exception" in content
        assert "request_id=exc-123" in content
