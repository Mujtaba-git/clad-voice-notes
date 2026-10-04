"""Test doubles for the pipeline's external pieces."""
from __future__ import annotations

import numpy as np

from voicenotes.asr.base import Transcriber
from voicenotes.models import Segment


class FakeTranscriber(Transcriber):
    name = "fake"

    def __init__(self, language="ur", texts=None, translated=None):
        super().__init__("fake")
        self.lang = language
        self.texts = texts or ["آج میں بینک جاؤں گا۔"]
        self.translated = translated or ["Today I will go to the bank."]
        self.calls = []

    def _detect(self, samples):
        return "hi" if self.lang == "ur" else self.lang

    def _transcribe(self, samples, language, task, progress):
        self.calls.append((language, task))
        texts = self.translated if task == "translate" else self.texts
        if progress:
            progress(0.5)
        return [Segment(i * 5.0, i * 5.0 + 5.0, t) for i, t in enumerate(texts)]


class FakeLLM:
    """Mimics OllamaClient: answers via a function of (system, prompt)."""

    def __init__(self, responder=None, available=True):
        self.responder = responder or (lambda system, prompt, fmt: prompt)
        self.calls = []
        self.available = available
        self.model = "fake-llm"

    def chat(self, prompt, system="", format=None, temperature=0.2):
        self.calls.append({"system": system, "prompt": prompt, "format": format})
        return self.responder(system, prompt, format)

    def is_available(self):
        return self.available

    def has_model(self):
        return self.available


def silence(seconds=1.0):
    return np.zeros(int(16000 * seconds), np.float32)
