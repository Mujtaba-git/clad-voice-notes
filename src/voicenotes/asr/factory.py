"""Pick the best available Whisper backend for this machine."""
from __future__ import annotations

import importlib.util
import platform
import sys

from .base import Transcriber


def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def available_backends() -> list[str]:
    out = []
    if sys.platform == "darwin" and platform.machine() == "arm64" and _has("mlx_whisper"):
        out.append("mlx")
    if _has("faster_whisper"):
        out.append("faster-whisper")
    if _has("sherpa_onnx"):
        out.append("sherpa-onnx")
    return out


def create_transcriber(backend: str = "auto", model: str = "large-v3-turbo") -> Transcriber:
    if backend == "auto":
        avail = available_backends()
        if not avail:
            raise RuntimeError("No speech backend installed. Run: pip install 'voicenotes[mac]' (or [cpu])")
        backend = avail[0]
    if backend == "mlx":
        from .mlx_backend import MlxTranscriber
        return MlxTranscriber(model)
    if backend == "faster-whisper":
        from .faster_whisper_backend import FasterWhisperTranscriber
        return FasterWhisperTranscriber(model)
    if backend == "sherpa-onnx":
        from .sherpa_backend import SherpaOnnxTranscriber
        return SherpaOnnxTranscriber(model)
    raise ValueError(f"unknown backend {backend!r}")
