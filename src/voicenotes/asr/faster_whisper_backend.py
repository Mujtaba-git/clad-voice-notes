"""Whisper via faster-whisper (CTranslate2, CPU int8). Cross-platform."""
from __future__ import annotations

import numpy as np

from ..audio import SAMPLE_RATE
from ..models import Segment
from .base import Progress, Transcriber


class FasterWhisperTranscriber(Transcriber):
    name = "faster-whisper"

    def __init__(self, model: str = "large-v3-turbo", device: str = "auto", compute_type: str = "int8"):
        super().__init__(model)
        self.device, self.compute_type = device, compute_type
        self._model = None

    def _get(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model, device=self.device, compute_type=self.compute_type)
        return self._model

    def _detect(self, samples: np.ndarray) -> str:
        _, info = self._get().transcribe(samples, language=None, beam_size=1, without_timestamps=True)
        return info.language

    def _transcribe(self, samples, language, task, progress: Progress | None) -> list[Segment]:
        total = max(len(samples) / SAMPLE_RATE, 1e-6)
        it, _ = self._get().transcribe(
            samples, language=language, task=task, beam_size=5,
            vad_filter=True, condition_on_previous_text=False,
        )
        segs = []
        for s in it:
            segs.append(Segment(s.start, s.end, s.text))
            if progress:
                progress(min(s.end / total, 0.99))
        return segs
