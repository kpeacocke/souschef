"""Audit component for SousChef architecture boundaries."""

from souschef.audit.events import log_event, log_role_change

__all__ = ["log_event", "log_role_change"]
