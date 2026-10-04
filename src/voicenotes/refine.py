"""LLM post-processing: grammar/structure cleanup and insight extraction."""
from __future__ import annotations

import json
import re
from typing import Callable

from . import prompts
from .models import Insights
from .textutils import chunk_text, word_count

Progress = Callable[[float], None]

# A cleaned chunk shorter than this fraction of the input is treated as an
# over-eager summary and the original text is kept instead.
MIN_LENGTH_RATIO = 0.5


def parse_json_object(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def _as_list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(v).strip().lstrip("-•* ").strip() for v in value if str(v).strip()]


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for it in items:
        key = re.sub(r"\W+", " ", it.lower()).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def insights_from_dict(d: dict) -> Insights:
    return Insights(
        title=str(d.get("title", "")).strip().strip('"'),
        key_points=_dedupe(_as_list(d.get("key_points"))),
        action_items=_dedupe(_as_list(d.get("action_items"))),
    )


class Refiner:
    def __init__(self, llm, chunk_chars: int = 3000):
        self.llm = llm
        self.chunk_chars = chunk_chars
        self.warnings: list[str] = []

    def clean(self, text: str, progress: Progress | None = None) -> str:
        chunks = chunk_text(text, self.chunk_chars)
        out = []
        for i, chunk in enumerate(chunks):
            edited = self.llm.chat(prompts.CLEAN_PROMPT.format(text=chunk), system=prompts.CLEAN_SYSTEM).strip()
            if word_count(edited) < MIN_LENGTH_RATIO * word_count(chunk):
                self.warnings.append(f"Cleanup of part {i + 1} dropped too much text; kept the original wording.")
                edited = chunk
            out.append(edited)
            if progress:
                progress((i + 1) / len(chunks))
        return "\n\n".join(out)

    def _extract(self, system: str, prompt: str) -> Insights:
        raw = self.llm.chat(prompt, system=system, format=prompts.INSIGHTS_SCHEMA, temperature=0.1)
        return insights_from_dict(parse_json_object(raw))

    def insights(self, text: str, progress: Progress | None = None) -> Insights:
        chunks = chunk_text(text, self.chunk_chars * 2)
        parts: list[Insights] = []
        for i, chunk in enumerate(chunks):
            try:
                parts.append(self._extract(prompts.INSIGHTS_SYSTEM, prompts.INSIGHTS_PROMPT.format(text=chunk)))
            except (json.JSONDecodeError, ValueError):
                self.warnings.append(f"Could not extract key points from part {i + 1}.")
            if progress:
                progress((i + 1) / (len(chunks) + (1 if len(chunks) > 1 else 0)))
        if not parts:
            return Insights()
        if len(parts) == 1:
            return parts[0]
        combined = Insights(
            title=parts[0].title,
            key_points=_dedupe([p for x in parts for p in x.key_points]),
            action_items=_dedupe([a for x in parts for a in x.action_items]),
        )
        payload = json.dumps({"key_points": combined.key_points, "action_items": combined.action_items},
                             ensure_ascii=False, indent=1)
        try:
            merged = self._extract(prompts.MERGE_SYSTEM, payload)
        except (json.JSONDecodeError, ValueError):
            return combined
        # Never let the merge silently lose most of the tasks.
        if len(merged.action_items) < 0.5 * len(combined.action_items):
            merged.action_items = combined.action_items
        return merged
