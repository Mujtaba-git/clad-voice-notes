"""Whisper via mlx-whisper: runs on the Apple-Silicon GPU (fastest on a Mac)."""
from __future__ import annotations

import numpy as np

from ..models import Segment
from .base import Progress, Transcriber

REPOS = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    "turbo": "mlx-community/whisper-large-v3-turbo",
}


class MlxTranscriber(Transcriber):
    name = "mlx"

    def __init__(self, model: str = "large-v3-turbo"):
        super().__init__(model)
        self.repo = REPOS.get(model, model)  # allow a raw HF repo id too

    def _run(self, samples: np.ndarray, **kw) -> dict:
        import mlx_whisper

        return mlx_whisper.transcribe(samples, path_or_hf_repo=self.repo, verbose=None, **kw)

    def _detect(self, samples: np.ndarray) -> str:
        return self._run(samples, language=None).get("language", "")

    def _transcribe(self, samples, language, task, progress: Progress | None) -> list[Segment]:
        out = self._run(samples, language=language, task=task, condition_on_previous_text=False)
        return [Segment(s["start"], s["end"], s["text"]) for s in out.get("segments", [])]
