from datetime import datetime

from voicenotes.models import Insights, NoteResult
from voicenotes.notes import fallback_title, format_duration, render_markdown, safe_filename, save_note

WHEN = datetime(2026, 10, 4, 18, 30, 5)


def urdu_note(**kw):
    base = dict(language="ur", duration=75.4, original="آج میں بینک جاؤں گا۔",
                english="Today I will go to the bank.", clean="Today, I will go to the bank.",
                insights=Insights("Bank visit", ["Going to the bank"], ["Go to the bank"]))
    base.update(kw)
    return NoteResult(**base)


def test_format_duration():
    assert format_duration(75.4) == "1:15"
    assert format_duration(3725) == "1:02:05"


def test_safe_filename():
    assert safe_filename('a/b:c*?"<>|#[x]') == "a b c x"
    assert safe_filename("...") == "Voice note"
    assert len(safe_filename("x" * 300)) == 80


def test_fallback_title():
    assert fallback_title("Hello, world! This is a long sentence indeed yes") == "Hello world This is a long sentence indeed"
    assert fallback_title("") == "Voice note"


def test_render_urdu_note_has_all_sections_in_order():
    md = render_markdown(urdu_note(), WHEN, ["voice-note", "#ideas"])
    assert md.startswith("---\ntitle: \"Bank visit\"\ncreated: 2026-10-04T18:30:05\nlanguage: ur\n")
    assert "tags:\n  - voice-note\n  - ideas" in md
    order = ["# Bank visit", "## Action items", "- [ ] Go to the bank", "## Key points",
             "## Clean notes", "## English translation", "## Original (Urdu)", '<div dir="rtl">']
    positions = [md.index(x) for x in order]
    assert positions == sorted(positions)


def test_render_english_note_uses_transcript_section():
    n = NoteResult(language="en", duration=10, original="hello there", english="hello there")
    md = render_markdown(n, WHEN)
    assert "## Transcript" in md and "## English translation" not in md
    assert "# hello there" in md  # fallback title


def test_render_warnings_callout():
    md = render_markdown(urdu_note(warnings=["Ollama is not running"]), WHEN)
    assert "> [!warning]" in md and "Ollama is not running" in md


def test_render_escapes_yaml():
    md = render_markdown(urdu_note(insights=Insights(title='Say "hi"')), WHEN)
    assert 'title: "Say \\"hi\\""' in md


def test_save_note_avoids_collisions(tmp_path):
    a = save_note(urdu_note(), tmp_path, WHEN)
    b = save_note(urdu_note(), tmp_path, WHEN)
    assert a.name == "2026-10-04 1830 Bank visit.md"
    assert b.name == "2026-10-04 1830 Bank visit (2).md"
    assert "Go to the bank" in a.read_text(encoding="utf-8")
