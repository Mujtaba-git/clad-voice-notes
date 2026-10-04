"""Urdu -> English translators.

* LLMTranslator     - local LLM via Ollama (default, offline, best quality)
* GoogleTranslator  - Google Translate's free web endpoint (online, opt-in)
Whisper's built-in translation is handled by the pipeline (it works on audio).
"""
from __future__ import annotations

import time
from typing import Callable, Protocol

import httpx

from . import prompts
from .textutils import chunk_text

Progress = Callable[[float], None]


class TranslationError(RuntimeError):
    pass


class Translator(Protocol):
    name: str

    def translate(self, text: str, progress: Progress | None = None) -> str: ...


class LLMTranslator:
    name = "llm"

    def __init__(self, llm, chunk_chars: int = 1200):
        self.llm = llm
        self.chunk_chars = chunk_chars

    def translate(self, text: str, progress: Progress | None = None) -> str:
        chunks = chunk_text(text, self.chunk_chars)
        out: list[str] = []
        for i, chunk in enumerate(chunks):
            context = prompts.TRANSLATE_CONTEXT.format(previous=out[-1][-600:]) if out else ""
            english = self.llm.chat(prompts.TRANSLATE_PROMPT.format(context=context, text=chunk),
                                    system=prompts.TRANSLATE_SYSTEM, temperature=0.1)
            if not english.strip():
                raise TranslationError(f"LLM returned an empty translation for part {i + 1}")
            out.append(english.strip())
            if progress:
                progress((i + 1) / len(chunks))
        return "\n\n".join(out)


class GoogleTranslator:
    """Uses the same free endpoint as the Google Translate website. Not an
    official API: no key needed, but it may rate-limit or change."""

    name = "google"
    URL = "https://translate.googleapis.com/translate_a/single"

    def __init__(self, source: str = "ur", target: str = "en", chunk_chars: int = 1500,
                 retries: int = 4, transport: httpx.BaseTransport | None = None, sleep=time.sleep):
        self.source, self.target = source, target
        self.chunk_chars, self.retries = chunk_chars, retries
        self._http = httpx.Client(timeout=30, transport=transport, headers={"User-Agent": "Mozilla/5.0"})
        self._sleep = sleep

    def _one(self, text: str) -> str:
        params = {"client": "gtx", "sl": self.source, "tl": self.target, "dt": "t"}
        delay = 2.0
        for attempt in range(self.retries + 1):
            try:
                r = self._http.post(self.URL, params=params, data={"q": text})
            except httpx.HTTPError as e:
                err = str(e)
            else:
                if r.status_code == 200:
                    return "".join(part[0] for part in r.json()[0] if part and part[0])
                err = f"HTTP {r.status_code}"
            if attempt < self.retries:
                self._sleep(delay)
                delay *= 2
        raise TranslationError(f"Google Translate failed: {err}")

    def translate(self, text: str, progress: Progress | None = None) -> str:
        chunks = chunk_text(text, self.chunk_chars)
        out = []
        for i, c in enumerate(chunks):
            out.append(self._one(c))
            if progress:
                progress((i + 1) / len(chunks))
        return " ".join(out)
