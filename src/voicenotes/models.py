"""Plain data types shared across the pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Transcript:
    language: str
    segments: list[Segment] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments if s.text.strip())

    @property
    def duration(self) -> float:
        return self.segments[-1].end if self.segments else 0.0


@dataclass
class Insights:
    title: str = ""
    key_points: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)


@dataclass
class NoteResult:
    """Everything produced for one recording."""

    language: str
    duration: float
    original: str  # transcript in the spoken language (Urdu script or English)
    english: str  # faithful English (translation, or the transcript itself)
    clean: str = ""  # grammar/structure-corrected English, details preserved
    insights: Insights = field(default_factory=Insights)
    audio_path: str | None = None
    note_path: str | None = None
    warnings: list[str] = field(default_factory=list)
