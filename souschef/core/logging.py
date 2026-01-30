"""
Structured logging configuration for SousChef.

This module provides structured logging with JSON output support,
contextual information, and integration with monitoring systems.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any, Literal

# Context variables for structured logging
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
operation_var: ContextVar[str | None] = ContextVar("operation", default=None)
cookbook_var: ContextVar[str | None] = ContextVar("cookbook", default=None)


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs structured log records.

    Supports both JSON and human-readable text formats.
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        json_format: bool = False,
    ):
        """
        Initialise structured formatter.

        Args:
            fmt: Log format string (ignored if json_format=True).
            datefmt: Date format string.
            style: Format style ('%', '{', or '$').
            json_format: Whether to output JSON format.

        """
        super().__init__(fmt, datefmt, style)
        self.json_format = json_format

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured output.

        Args:
            record: Log record to format.

        Returns:
            Formatted log string (JSON or text).

        """
        # Add context variables to record
        record.request_id = request_id_var.get()
        record.operation = operation_var.get()
        record.cookbook = cookbook_var.get()

        if self.json_format:
            return self._format_json(record)
        else:
            return self._format_text(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """Format record as JSON."""
        import json

        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context if available
        request_id = getattr(record, "request_id", None)
        operation = getattr(record, "operation", None)
        cookbook = getattr(record, "cookbook", None)

        if request_id:
            log_data["request_id"] = request_id
        if operation:
            log_data["operation"] = operation
        if cookbook:
            log_data["cookbook"] = cookbook

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "msecs",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "processName",
                "process",
                "threadName",
                "thread",
                "request_id",
                "operation",
                "cookbook",
                "message",
                "asctime",
                "relativeCreated",
            } and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data, default=str)

    def _format_text(self, record: logging.LogRecord) -> str:
        """Format record as human-readable text."""
        # Use parent formatter for base formatting
        base_msg = super().format(record)

        # Add context if available
        context_parts = []
        request_id = getattr(record, "request_id", None)
        operation = getattr(record, "operation", None)
        cookbook = getattr(record, "cookbook", None)

        if request_id:
            context_parts.append(f"request_id={request_id}")
        if operation:
            context_parts.append(f"operation={operation}")
        if cookbook:
            context_parts.append(f"cookbook={cookbook}")

        if context_parts:
            context_str = " [" + ", ".join(context_parts) + "]"
            return base_msg + context_str

        return base_msg


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: str | None = None,
) -> None:
    """
    Configure structured logging for SousChef.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: Whether to output JSON format.
        log_file: Optional file path for log output.

    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    if json_format:
        formatter = StructuredFormatter(json_format=True)
    else:
        formatter = StructuredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure SousChef logger
    souschef_logger = logging.getLogger("souschef")
    souschef_logger.setLevel(numeric_level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.

    """
    return logging.getLogger(name)


def set_context(
    request_id: str | None = None,
    operation: str | None = None,
    cookbook: str | None = None,
) -> None:
    """
    Set context variables for structured logging.

    Args:
        request_id: Unique request/operation ID.
        operation: Current operation name.
        cookbook: Cookbook being processed.

    """
    if request_id is not None:
        request_id_var.set(request_id)
    if operation is not None:
        operation_var.set(operation)
    if cookbook is not None:
        cookbook_var.set(cookbook)


def clear_context() -> None:
    """Clear all context variables."""
    request_id_var.set(None)
    operation_var.set(None)
    cookbook_var.set(None)


class LogContext:
    """
    Context manager for temporary logging context.

    Example:
        with LogContext(operation="convert_recipe", cookbook="apache"):
            logger.info("Converting recipe")

    """

    def __init__(
        self,
        request_id: str | None = None,
        operation: str | None = None,
        cookbook: str | None = None,
    ):
        """
        Initialise log context.

        Args:
            request_id: Unique request/operation ID.
            operation: Current operation name.
            cookbook: Cookbook being processed.

        """
        self.request_id = request_id
        self.operation = operation
        self.cookbook = cookbook
        self.previous_context: dict[str, Any] = {}

    def __enter__(self) -> "LogContext":
        """Enter context and save previous values."""
        self.previous_context = {
            "request_id": request_id_var.get(),
            "operation": operation_var.get(),
            "cookbook": cookbook_var.get(),
        }
        set_context(
            request_id=self.request_id,
            operation=self.operation,
            cookbook=self.cookbook,
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous values."""
        request_id_var.set(self.previous_context["request_id"])
        operation_var.set(self.previous_context["operation"])
        cookbook_var.set(self.previous_context["cookbook"])


def log_operation(operation_name: str):
    """
    Decorate functions to log operations with structured context.

    Args:
        operation_name: Name of the operation being logged.

    Example:
        @log_operation("convert_recipe")
        def convert_recipe(recipe_path: str) -> str:
            # Operation is logged with context
            return playbook_content

    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)

            with LogContext(operation=operation_name):
                logger.info(
                    f"Starting {operation_name}",
                    extra={"function": func.__name__},
                )
                try:
                    result = func(*args, **kwargs)
                    logger.info(
                        f"Completed {operation_name}",
                        extra={"function": func.__name__},
                    )
                    return result
                except Exception as e:
                    logger.error(
                        f"Failed {operation_name}: {e}",
                        extra={"function": func.__name__},
                        exc_info=True,
                    )
                    raise

        return wrapper

    return decorator
