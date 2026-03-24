"""Tests for background job queue utilities."""

from __future__ import annotations

import time
from typing import Any

from souschef.core.job_queue import BackgroundJobQueue


def _wait_for_terminal_status(
    queue: BackgroundJobQueue,
    job_id: str,
    timeout_seconds: float = 3.0,
) -> dict[str, Any]:
    """Poll a job until it reaches a terminal state."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        snapshot = queue.get(job_id)
        if snapshot is not None and snapshot["status"] in {"succeeded", "failed"}:
            return snapshot
        time.sleep(0.01)
    raise AssertionError("Job did not reach terminal state in time")


def test_background_job_queue_success_flow() -> None:
    """Submitted jobs should complete with result, progress, and logs."""
    queue = BackgroundJobQueue(max_workers=1)

    def _job(progress: Any, log: Any) -> dict[str, str]:
        log("step 1")
        progress(30, "running")
        progress(100, "done")
        return {"status": "ok"}

    job_id = queue.submit("demo", _job)
    snapshot = _wait_for_terminal_status(queue, job_id)

    assert snapshot["status"] == "succeeded"
    assert snapshot["progress"] == 100
    assert snapshot["result"] == {"status": "ok"}
    assert any("step 1" in line for line in snapshot["logs"])


def test_background_job_queue_failure_flow() -> None:
    """Failures should be captured with status, error, and log entries."""
    queue = BackgroundJobQueue(max_workers=1)

    def _job(progress: Any, log: Any) -> dict[str, str]:
        progress(20, "starting")
        log("about to fail")
        raise ValueError("boom")

    job_id = queue.submit("failing", _job)
    snapshot = _wait_for_terminal_status(queue, job_id)

    assert snapshot["status"] == "failed"
    assert "boom" in str(snapshot["error"])
    assert any("about to fail" in line for line in snapshot["logs"])


def test_background_job_queue_progress_is_clamped() -> None:
    """Progress callback should clamp values into 0..100 range."""
    queue = BackgroundJobQueue(max_workers=1)

    def _job(progress: Any, _log: Any) -> str:
        progress(-10, "too low")
        progress(150, "too high")
        return "done"

    job_id = queue.submit("clamped", _job)
    snapshot = _wait_for_terminal_status(queue, job_id)

    assert snapshot["status"] == "succeeded"
    assert snapshot["progress"] == 100
