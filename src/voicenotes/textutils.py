"""Sentence splitting and chunking that understands Urdu punctuation."""
from __future__ import annotations

import re

# English . ! ? and Urdu full stop (۔) / question mark (؟)
_SENT_END = re.compile(r"(?<=[.!?۔؟])\s+")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [s for s in _SENT_END.split(text) if s]


def chunk_text(text: str, max_chars: int = 2500) -> list[str]:
    """Group whole sentences into chunks of at most `max_chars` (a single
    over-long sentence is hard-split on word boundaries)."""
    chunks: list[str] = []
    cur = ""
    for sent in split_sentences(text):
        pieces = [sent]
        if len(sent) > max_chars:
            pieces, buf = [], ""
            for word in sent.split(" "):
                if buf and len(buf) + 1 + len(word) > max_chars:
                    pieces.append(buf)
                    buf = word
                else:
                    buf = f"{buf} {word}".strip()
            if buf:
                pieces.append(buf)
        for p in pieces:
            if cur and len(cur) + 1 + len(p) > max_chars:
                chunks.append(cur)
                cur = p
            else:
                cur = f"{cur} {p}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def word_count(text: str) -> int:
    return len(text.split())
