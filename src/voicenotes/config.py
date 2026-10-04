"""User settings, persisted as JSON in the app's data directory."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

LANGUAGES = ("auto", "ur", "en")
ASR_BACKENDS = ("auto", "mlx", "faster-whisper", "sherpa-onnx")
TRANSLATORS = ("llm", "whisper", "google", "none")


def data_dir() -> Path:
    """Where settings, recordings and models live. Override with VOICENOTES_HOME."""
    if env := os.environ.get("VOICENOTES_HOME"):
        return Path(env).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VoiceNotes"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "voicenotes"


@dataclass
class Settings:
    # Speech recognition
    language: str = "auto"  # auto | ur | en
    asr_backend: str = "auto"
    asr_model: str = "large-v3-turbo"  # tiny/base/small/medium/large-v3/large-v3-turbo
    # Urdu -> English translation
    translator: str = "llm"  # llm | whisper | google | none
    # Local LLM (Ollama) for translation, cleanup and insights
    ollama_url: str = "http://127.0.0.1:11434"
    llm_model: str = "gemma3:12b"
    llm_timeout: float = 600.0
    clean_text: bool = True
    extract_insights: bool = True
    # Output
    vault_dir: str = ""  # Obsidian vault; empty = <data_dir>/notes
    notes_subfolder: str = "Voice Notes"
    tags: str = "voice-note"
    keep_audio: bool = True

    def validate(self) -> None:
        if self.language not in LANGUAGES:
            raise ValueError(f"language must be one of {LANGUAGES}")
        if self.asr_backend not in ASR_BACKENDS:
            raise ValueError(f"asr_backend must be one of {ASR_BACKENDS}")
        if self.translator not in TRANSLATORS:
            raise ValueError(f"translator must be one of {TRANSLATORS}")

    def notes_dir(self) -> Path:
        base = Path(self.vault_dir).expanduser() if self.vault_dir else data_dir() / "notes"
        return base / self.notes_subfolder if self.notes_subfolder else base

    def updated(self, **changes) -> "Settings":
        known = {f.name for f in fields(self)}
        unknown = set(changes) - known
        if unknown:
            raise ValueError(f"unknown settings: {sorted(unknown)}")
        new = Settings(**{**asdict(self), **changes})
        new.validate()
        return new


def settings_path() -> Path:
    return data_dir() / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    if not path.exists():
        return Settings()
    raw = json.loads(path.read_text(encoding="utf-8"))
    known = {f.name for f in fields(Settings)}
    s = Settings(**{k: v for k, v in raw.items() if k in known})
    s.validate()
    return s


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    settings.validate()
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")
    return path
