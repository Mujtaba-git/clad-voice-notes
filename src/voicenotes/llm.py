"""Minimal client for a local Ollama server (https://ollama.com)."""
from __future__ import annotations

import re

import httpx


class LLMError(RuntimeError):
    pass


_THINK = re.compile(r"<think>.*?</think>", re.S)


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks that reasoning models may emit."""
    return _THINK.sub("", text).strip()


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "gemma3:12b",
                 timeout: float = 600.0, num_ctx: int = 8192, transport: httpx.BaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout, transport=transport)

    def is_available(self) -> bool:
        try:
            return self._http.get("/api/tags", timeout=3).status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self) -> list[str]:
        try:
            r = self._http.get("/api/tags", timeout=5)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama not reachable at {self.base_url}: {e}") from e
        return [m["name"] for m in r.json().get("models", [])]

    def has_model(self) -> bool:
        names = self.list_models()
        want = self.model if ":" in self.model else f"{self.model}:latest"
        return want in names or self.model in names

    def chat(self, prompt: str, system: str = "", format: dict | str | None = None,
             temperature: float = 0.2) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": self.num_ctx},
        }
        if format is not None:
            body["format"] = format
        try:
            r = self._http.post("/api/chat", json=body)
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama not reachable at {self.base_url}. Is it running? ({e})") from e
        if r.status_code == 404:
            raise LLMError(f"Model '{self.model}' not found. Run: ollama pull {self.model}")
        if r.status_code >= 400:
            raise LLMError(f"Ollama error {r.status_code}: {r.text[:300]}")
        return strip_thinking(r.json().get("message", {}).get("content", ""))
