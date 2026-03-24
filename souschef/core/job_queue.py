"""In-memory background job queue with progress and logs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

JobTarget = Callable[[Callable[[int, str | None], None], Callable[[str], None]], Any]


@dataclass
class BackgroundJob:
    """Represents one submitted background job."""

    job_id: str
    name: str
    status: str = "queued"
    progress: int = 0
    logs: list[str] = field(default_factory=list)
    result: Any = None
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: str | None = None
    finished_at: str | None = None


class BackgroundJobQueue:
    """Thread-backed queue for long-running UI jobs."""

    def __init__(self, max_workers: int = 2) -> None:
        """Initialise queue with bounded worker pool."""
        self._lock = Lock()
        self._jobs: dict[str, BackgroundJob] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, name: str, target: JobTarget) -> str:
        """Submit a callable job and return the created job id."""
        job_id = str(uuid4())
        with self._lock:
            self._jobs[job_id] = BackgroundJob(job_id=job_id, name=name)
        self._executor.submit(self._run_job, job_id, target)
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        """Get a serialisable snapshot of a job by id."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                "job_id": job.job_id,
                "name": job.name,
                "status": job.status,
                "progress": job.progress,
                "logs": list(job.logs),
                "result": job.result,
                "error": job.error,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
            }

    def _run_job(self, job_id: str, target: JobTarget) -> None:
        """Execute a submitted job and keep status/progress updated."""

        def progress(value: int, message: str | None = None) -> None:
            clamped = max(0, min(100, int(value)))
            with self._lock:
                job = self._jobs[job_id]
                job.progress = clamped
                if message:
                    job.logs.append(message)

        def log(message: str) -> None:
            with self._lock:
                self._jobs[job_id].logs.append(message)

        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = datetime.now(timezone.utc).isoformat()
            job.logs.append("Job started")

        try:
            result = target(progress, log)
            with self._lock:
                job = self._jobs[job_id]
                job.result = result
                job.status = "succeeded"
                job.progress = 100
                job.logs.append("Job completed successfully")
        except Exception as exc:  # pragma: no cover - exception paths tested via status
            with self._lock:
                job = self._jobs[job_id]
                job.status = "failed"
                job.error = str(exc)
                job.logs.append(f"Job failed: {exc}")
        finally:
            with self._lock:
                self._jobs[job_id].finished_at = datetime.now(timezone.utc).isoformat()


background_job_queue = BackgroundJobQueue()
