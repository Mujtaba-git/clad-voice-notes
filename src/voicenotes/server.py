"""Local web app: FastAPI backend + a single-page UI for recording and reviewing notes."""
from __future__ import annotations

import re
import time
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from . import __version__
from .asr import available_backends, create_transcriber
from .config import Settings, data_dir, load_settings, save_settings
from .jobs import JobManager
from .llm import LLMError, OllamaClient
from .pipeline import Pipeline


class Engine:
    """Holds settings and caches the loaded Whisper model between jobs."""

    def __init__(self, settings: Settings | None = None, transcriber_factory=create_transcriber,
                 llm_factory=None, persist: bool = True):
        self.settings = settings or load_settings()
        self.persist = persist
        self._tf = transcriber_factory
        self._lf = llm_factory or (lambda s: OllamaClient(s.ollama_url, s.llm_model, timeout=s.llm_timeout))
        self._cache: dict[tuple[str, str], object] = {}

    def transcriber(self):
        key = (self.settings.asr_backend, self.settings.asr_model)
        if key not in self._cache:
            self._cache.clear()  # free the previous model's memory
            self._cache[key] = self._tf(*key)
        return self._cache[key]

    def llm(self):
        return self._lf(self.settings)

    def update(self, changes: dict) -> Settings:
        self.settings = self.settings.updated(**changes)
        if self.persist:
            save_settings(self.settings)
        return self.settings

    def run(self, job, progress):
        pipe = Pipeline(self.settings, transcriber=self.transcriber(), llm=self.llm())
        return pipe.run(job.audio_path, progress=progress, language=job.language)


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[-60:] or "recording"


def create_app(engine: Engine | None = None) -> FastAPI:
    engine = engine or Engine()
    jobs = JobManager(engine.run)
    app = FastAPI(title="VoiceNotes", version=__version__)
    app.state.engine, app.state.jobs = engine, jobs

    @app.get("/", response_class=HTMLResponse)
    def index():
        return files("voicenotes").joinpath("static/index.html").read_text(encoding="utf-8")

    @app.get("/api/status")
    def status():
        s = engine.settings
        llm = engine.llm()
        ollama = llm.is_available()
        model_ok = False
        if ollama:
            try:
                model_ok = llm.has_model()
            except LLMError:
                pass
        return {
            "version": __version__,
            "backends": available_backends(),
            "ollama": ollama,
            "llm_model": s.llm_model,
            "llm_model_installed": model_ok,
            "notes_dir": str(s.notes_dir()),
        }

    @app.get("/api/settings")
    def get_settings():
        return asdict(engine.settings)

    @app.put("/api/settings")
    def put_settings(changes: dict):
        try:
            return asdict(engine.update(changes))
        except (ValueError, TypeError) as e:
            raise HTTPException(400, str(e))

    @app.post("/api/jobs")
    async def create_job(file: UploadFile = File(...), language: str = Form("")):
        if language not in ("", "auto", "ur", "en"):
            raise HTTPException(400, "language must be auto, ur or en")
        rec_dir = data_dir() / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True)
        name = file.filename or "recording.webm"
        dest = rec_dir / f"{time.strftime('%Y-%m-%d_%H%M%S')}_{_safe_name(name)}"
        with dest.open("wb") as out:  # stored before processing so nothing is ever lost
            while chunk := await file.read(1 << 20):
                out.write(chunk)
        if dest.stat().st_size == 0:
            dest.unlink()
            raise HTTPException(400, "empty upload")
        job = jobs.submit(dest, name, language if language in ("ur", "en") else None)
        return job.to_dict()

    @app.get("/api/jobs")
    def list_jobs():
        return [j.to_dict() for j in jobs.list()]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "no such job")
        return job.to_dict()

    @app.post("/api/jobs/{job_id}/retry")
    def retry_job(job_id: str):
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "no such job")
        if not Path(job.audio_path).exists():
            raise HTTPException(410, "audio no longer available")
        return jobs.submit(job.audio_path, job.filename, job.language).to_dict()

    return app
