"""A tiny in-process job queue: one worker, so only one model is busy at a time."""
from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from .models import NoteResult


@dataclass
class Job:
    id: str
    filename: str
    audio_path: str
    language: str | None = None
    status: str = "queued"  # queued | running | done | error
    stage: str = ""
    progress: float = 0.0
    message: str = "Waiting"
    error: str | None = None
    result: dict | None = None
    created: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


Runner = Callable[[Job, Callable[[str, float, str], None]], NoteResult]


class JobManager:
    def __init__(self, runner: Runner):
        self.runner = runner
        self.jobs: dict[str, Job] = {}
        self._q: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._loop, daemon=True, name="voicenotes-worker")
        self._worker.start()

    def submit(self, audio_path: str | Path, filename: str, language: str | None = None) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], filename=filename, audio_path=str(audio_path), language=language)
        with self._lock:
            self.jobs[job.id] = job
        self._q.put(job.id)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def list(self) -> list[Job]:
        return sorted(self.jobs.values(), key=lambda j: j.created, reverse=True)

    def wait(self, job_id: str, timeout: float = 30) -> Job:
        end = time.time() + timeout
        while time.time() < end:
            j = self.jobs[job_id]
            if j.status in ("done", "error"):
                return j
            time.sleep(0.02)
        raise TimeoutError(job_id)

    def _loop(self):
        while True:
            job = self.jobs[self._q.get()]
            job.status, job.message = "running", "Starting"

            def progress(stage, frac, msg, job=job):
                job.stage, job.progress, job.message = stage, frac, msg

            try:
                result = self.runner(job, progress)
                job.result = asdict(result)
                job.status, job.progress, job.message = "done", 1.0, "Done"
            except Exception as e:  # report every failure to the UI
                job.status, job.error, job.message = "error", str(e) or type(e).__name__, "Failed"
                traceback.print_exc()
