"""Whisper via sherpa-onnx (ONNX Runtime, CPU). Models are downloaded from
sherpa-onnx's GitHub releases, so this backend works where Hugging Face is
unreachable. Long audio is split at silences into <30 s windows."""
from __future__ import annotations

import os
import tarfile
import urllib.request
from pathlib import Path

import numpy as np

from ..audio import SAMPLE_RATE, is_silent, split_on_silence
from ..config import data_dir
from ..models import Segment
from .base import Progress, Transcriber

RELEASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
_NAMES = {"large-v3-turbo": "turbo", "turbo": "turbo"}


def model_dirs() -> list[Path]:
    return [data_dir() / "models", Path.home() / ".cache" / "voicenotes" / "models"]


def ensure_model(model: str) -> tuple[Path, str]:
    """Return (directory, prefix) for the ONNX Whisper model, downloading if needed."""
    name = _NAMES.get(model, model)
    folder = f"sherpa-onnx-whisper-{name}"
    for base in model_dirs():
        d = base / folder
        if (d / f"{name}-tokens.txt").exists():
            return d, name
    target = model_dirs()[0]
    target.mkdir(parents=True, exist_ok=True)
    url = f"{RELEASE}/{folder}.tar.bz2"
    tmp = target / f"{folder}.tar.bz2.part"
    urllib.request.urlretrieve(url, tmp)
    with tarfile.open(tmp, "r:bz2") as tar:
        tar.extractall(target, filter="data")
    tmp.unlink()
    return target / folder, name


class SherpaOnnxTranscriber(Transcriber):
    name = "sherpa-onnx"

    def __init__(self, model: str = "small", num_threads: int | None = None):
        super().__init__(model)
        self.num_threads = num_threads or max(1, (os.cpu_count() or 2) - 1)
        self._recognizers: dict[tuple[str, str], object] = {}

    def _recognizer(self, language: str, task: str):
        key = (language, task)
        if key not in self._recognizers:
            import sherpa_onnx

            d, name = ensure_model(self.model)
            enc = d / f"{name}-encoder.int8.onnx"
            dec = d / f"{name}-decoder.int8.onnx"
            if not enc.exists():
                enc, dec = d / f"{name}-encoder.onnx", d / f"{name}-decoder.onnx"
            self._recognizers[key] = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=str(enc), decoder=str(dec), tokens=str(d / f"{name}-tokens.txt"),
                language=language, task=task, num_threads=self.num_threads,
            )
        return self._recognizers[key]

    def _decode(self, rec, samples: np.ndarray):
        stream = rec.create_stream()
        stream.accept_waveform(SAMPLE_RATE, samples)
        rec.decode_stream(stream)
        return stream.result

    def _detect(self, samples: np.ndarray) -> str:
        return self._decode(self._recognizer("", "transcribe"), samples).lang or ""

    def _transcribe(self, samples, language, task, progress: Progress | None) -> list[Segment]:
        rec = self._recognizer(language, task)
        chunks = split_on_silence(samples)
        segs: list[Segment] = []
        for i, (a, b) in enumerate(chunks):
            piece = samples[a:b]
            if not is_silent(piece):
                text = self._decode(rec, piece).text.strip()
                segs.append(Segment(a / SAMPLE_RATE, b / SAMPLE_RATE, text))
            if progress:
                progress((i + 1) / len(chunks))
        return segs
