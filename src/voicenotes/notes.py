"""Render a NoteResult as an Obsidian-friendly Markdown note and save it."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import NoteResult

LANG_NAMES = {"ur": "Urdu", "en": "English"}


def format_duration(seconds: float) -> str:
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fallback_title(text: str, words: int = 8) -> str:
    w = re.sub(r"[^\w\s'-]", " ", text).split()
    return " ".join(w[:words]) if w else "Voice note"


def safe_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r'[\\/:*?"<>|#^\[\]\n\r\t]+', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:max_len].rstrip(" .") or "Voice note"


def _yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_markdown(note: NoteResult, created: datetime, tags: list[str] | None = None) -> str:
    title = note.insights.title or fallback_title(note.clean or note.english or note.original)
    tags = [t.strip().lstrip("#") for t in (tags or []) if t.strip()]
    fm = [
        "---",
        f"title: {_yaml_str(title)}",
        f"created: {created.strftime('%Y-%m-%dT%H:%M:%S')}",
        f"language: {note.language}",
        f"duration: {_yaml_str(format_duration(note.duration))}",
    ]
    if tags:
        fm.append("tags:")
        fm += [f"  - {t}" for t in tags]
    if note.audio_path:
        fm.append(f"audio: {_yaml_str(note.audio_path)}")
    fm.append("---")

    body = [f"# {title}", ""]
    if note.insights.action_items:
        body += ["## Action items", ""] + [f"- [ ] {a}" for a in note.insights.action_items] + [""]
    if note.insights.key_points:
        body += ["## Key points", ""] + [f"- {k}" for k in note.insights.key_points] + [""]
    if note.clean:
        body += ["## Clean notes", "", note.clean.strip(), ""]
    if note.language == "ur":
        if note.english:
            body += ["## English translation", "", note.english.strip(), ""]
        body += ["## Original (Urdu)", "", '<div dir="rtl">', "", note.original.strip(), "", "</div>", ""]
    else:
        body += ["## Transcript", "", note.original.strip(), ""]
    if note.warnings:
        body += ["> [!warning] Processing notes"] + [f"> - {w}" for w in note.warnings] + [""]
    return "\n".join(fm + [""] + body).rstrip() + "\n"


def save_note(note: NoteResult, folder: Path, created: datetime, tags: list[str] | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    title = note.insights.title or fallback_title(note.clean or note.english or note.original)
    stem = f"{created.strftime('%Y-%m-%d %H%M')} {safe_filename(title)}"
    path = folder / f"{stem}.md"
    n = 2
    while path.exists():
        path = folder / f"{stem} ({n}).md"
        n += 1
    path.write_text(render_markdown(note, created, tags), encoding="utf-8")
    return path
