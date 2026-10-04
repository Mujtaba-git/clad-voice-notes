"""Orchestrates: audio -> transcript -> English -> clean text + insights -> note."""
from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from .asr import Transcriber, create_transcriber
from .audio import AudioError, duration_seconds, is_silent, load_audio
from .config import Settings, data_dir
from .llm import LLMError, OllamaClient
from .models import NoteResult
from .notes import save_note
from .refine import Refiner
from .translate import GoogleTranslator, LLMTranslator, TranslationError

log = logging.getLogger(__name__)

# (stage, overall fraction 0..1, human message)
ProgressFn = Callable[[str, float, str], None]

# Share of the progress bar each stage occupies.
WEIGHTS = {"load": 0.03, "detect": 0.02, "transcribe": 0.50, "translate": 0.20,
           "clean": 0.15, "insights": 0.08, "save": 0.02}


class _Progress:
    def __init__(self, fn: ProgressFn | None):
        self.fn = fn
        self.done = 0.0

    def stage(self, name: str, message: str):
        weight = WEIGHTS[name]
        start = self.done
        self.done += weight
        self._emit(name, start, message)

        def sub(frac: float):
            self._emit(name, start + weight * max(0.0, min(frac, 1.0)), message)

        return sub

    def _emit(self, name, value, message):
        if self.fn:
            self.fn(name, round(min(value, 1.0), 4), message)


class Pipeline:
    def __init__(self, settings: Settings, transcriber: Transcriber | None = None, llm=None,
                 translator=None, now: Callable[[], datetime] = datetime.now):
        self.settings = settings
        self._transcriber = transcriber
        self.llm = llm if llm is not None else OllamaClient(
            settings.ollama_url, settings.llm_model, timeout=settings.llm_timeout)
        self._translator = translator
        self.now = now

    @property
    def transcriber(self) -> Transcriber:
        if self._transcriber is None:
            self._transcriber = create_transcriber(self.settings.asr_backend, self.settings.asr_model)
        return self._transcriber

    def _keep_audio(self, path: Path, created: datetime) -> str | None:
        if not self.settings.keep_audio:
            return None
        rec_dir = data_dir() / "recordings"
        if rec_dir in path.parents:
            return str(path)
        rec_dir.mkdir(parents=True, exist_ok=True)
        dest = rec_dir / f"{created.strftime('%Y-%m-%d_%H%M%S')}{path.suffix}"
        shutil.copy2(path, dest)
        return str(dest)

    def llm_problem(self) -> str | None:
        """None if the local LLM is ready, else a short explanation (checked once per run)."""
        if not hasattr(self, "_llm_problem"):
            s = self.settings
            problem = None
            if not self.llm.is_available():
                problem = f"Ollama is not running at {s.ollama_url}"
            else:
                try:
                    if not self.llm.has_model():
                        problem = f"AI model '{s.llm_model}' is not downloaded (run: ollama pull {s.llm_model})"
                except LLMError as e:
                    problem = str(e)
            self._llm_problem = problem
        return self._llm_problem

    def _to_english(self, samples, transcript_text: str, warnings: list[str], prog) -> str:
        mode = self.settings.translator
        if mode == "none":
            return ""
        if mode == "llm":
            if not self.llm_problem():
                try:
                    tr = self._translator or LLMTranslator(self.llm)
                    return tr.translate(transcript_text, progress=prog)
                except (LLMError, TranslationError) as e:
                    warnings.append(f"LLM translation failed ({e}); used Whisper's translation instead.")
            else:
                warnings.append(f"{self.llm_problem()}; used Whisper's built-in translation instead.")
        elif mode == "google":
            try:
                tr = self._translator or GoogleTranslator()
                return tr.translate(transcript_text, progress=prog)
            except TranslationError as e:
                warnings.append(f"{e}; used Whisper's translation instead.")
        # "whisper" mode, or fallback
        if "turbo" in self.settings.asr_model:
            warnings.append("Whisper large-v3-turbo translates poorly; choose large-v3 for Whisper translation.")
        return self.transcriber.transcribe(samples, "ur", task="translate", progress=prog).text

    def run(self, audio_path: str | Path, progress: ProgressFn | None = None, save: bool = True,
            language: str | None = None) -> NoteResult:
        s = self.settings
        p = _Progress(progress)
        created = self.now()
        audio_path = Path(audio_path)

        p.stage("load", "Reading audio")
        samples = load_audio(audio_path)
        if is_silent(samples):
            raise AudioError("The recording is empty or silent.")
        duration = duration_seconds(samples)
        warnings: list[str] = []

        p.stage("detect", "Detecting language")
        lang = language or s.language
        if lang == "auto":
            lang = self.transcriber.detect_language(samples)

        sub = p.stage("transcribe", f"Transcribing {'Urdu' if lang == 'ur' else 'English'} speech")
        transcript = self.transcriber.transcribe(samples, lang, progress=sub)
        original = transcript.text
        if not original.strip():
            raise AudioError("No speech was recognised in the recording.")

        sub = p.stage("translate", "Translating to English")
        english = self._to_english(samples, original, warnings, sub) if lang == "ur" else original

        wants_llm = (s.clean_text or s.extract_insights) and bool(english)
        llm_ok = wants_llm and not self.llm_problem()
        if wants_llm and not llm_ok:
            warnings.append(f"{self.llm_problem()}; skipped grammar cleanup and key points.")
        refiner = Refiner(self.llm)

        sub = p.stage("clean", "Correcting grammar and structure")
        clean = ""
        if s.clean_text and llm_ok:
            try:
                clean = refiner.clean(english, progress=sub)
            except LLMError as e:
                warnings.append(f"Cleanup failed: {e}")

        sub = p.stage("insights", "Extracting key points and to-dos")
        result = NoteResult(language=lang, duration=duration, original=original, english=english, clean=clean)
        if s.extract_insights and llm_ok:
            try:
                result.insights = refiner.insights(clean or english, progress=sub)
            except LLMError as e:
                warnings.append(f"Key-point extraction failed: {e}")
        result.warnings = warnings + refiner.warnings

        p.stage("save", "Saving note")
        if save:
            result.audio_path = self._keep_audio(audio_path, created)
            tags = [t for t in s.tags.split(",") if t.strip()]
            result.note_path = str(save_note(result, s.notes_dir(), created, tags))
        if progress:
            progress("done", 1.0, "Done")
        return result
