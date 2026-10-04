"""Common interface and helpers for Whisper backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import numpy as np

from ..audio import SAMPLE_RATE
from ..models import Segment, Transcript

Progress = Callable[[float], None]  # fraction 0..1

DETECT_SECONDS = 30


def normalize_language(code: str | None) -> str:
    """The app only supports Urdu and English. Whisper often labels Urdu speech
    as Hindi (same spoken language, different script), so anything that is not
    English is treated as Urdu."""
    return "en" if (code or "").lower().startswith("en") else "ur"


def clean_segments(segments: list[Segment], max_repeats: int = 2) -> list[Segment]:
    """Drop empty segments and collapse Whisper's repetition loops
    (the same line emitted over and over on silence/noise)."""
    out: list[Segment] = []
    run = 0
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        if out and text == out[-1].text:
            run += 1
            if run >= max_repeats:
                out[-1].end = seg.end
                continue
        else:
            run = 0
        out.append(Segment(seg.start, seg.end, text))
    return out


class Transcriber(ABC):
    name: str = "base"

    def __init__(self, model: str = "large-v3-turbo"):
        self.model = model

    def detect_language(self, samples: np.ndarray) -> str:
        """Return 'ur' or 'en' using the first 30 s of audio."""
        return normalize_language(self._detect(samples[: DETECT_SECONDS * SAMPLE_RATE]))

    @abstractmethod
    def _detect(self, samples: np.ndarray) -> str:
        """Raw Whisper language code for a short clip."""

    @abstractmethod
    def _transcribe(self, samples: np.ndarray, language: str, task: str, progress: Progress | None) -> list[Segment]:
        ...

    def transcribe(
        self,
        samples: np.ndarray,
        language: str,
        task: str = "transcribe",
        progress: Progress | None = None,
    ) -> Transcript:
        if language not in ("ur", "en"):
            raise ValueError("language must be 'ur' or 'en' (detect it first)")
        if task not in ("transcribe", "translate"):
            raise ValueError("task must be 'transcribe' or 'translate'")
        segs = clean_segments(self._transcribe(samples, language, task, progress))
        if progress:
            progress(1.0)
        return Transcript(language="en" if task == "translate" else language, segments=segs)
