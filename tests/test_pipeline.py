import json
from datetime import datetime
from pathlib import Path

import pytest

from voicenotes.audio import AudioError
from voicenotes.config import Settings
from voicenotes.pipeline import Pipeline

from .conftest import AUDIO
from .fakes import FakeLLM, FakeTranscriber

INSIGHTS = {"title": "Bank and sister", "key_points": ["Errands"], "action_items": ["Go to the bank", "Call sister"]}


def smart_llm():
    def respond(system, prompt, fmt):
        if fmt is not None:
            return json.dumps(INSIGHTS)
        if "translator" in system:
            return "Tomorrow I have to go to the bank. I have to call my sister."
        return "Tomorrow, I have to go to the bank. I also have to call my sister."
    return FakeLLM(respond)


def make(tmp_path, transcriber=None, llm=None, **settings):
    s = Settings(vault_dir=str(tmp_path / "vault"), **settings)
    return Pipeline(s, transcriber=transcriber or FakeTranscriber("ur"), llm=llm or smart_llm(),
                    now=lambda: datetime(2026, 10, 4, 9, 0))


def test_urdu_end_to_end_creates_note(tmp_path):
    events = []
    r = make(tmp_path).run(AUDIO / "urdu_todo.wav", progress=lambda *e: events.append(e))
    assert r.language == "ur"
    assert r.original.startswith("آج")
    assert "bank" in r.english and "sister" in r.clean
    assert r.insights.action_items == ["Go to the bank", "Call sister"]
    note = Path(r.note_path)
    assert note.parent == tmp_path / "vault" / "Voice Notes"
    assert note.name == "2026-10-04 0900 Bank and sister.md"
    assert Path(r.audio_path).exists()
    fractions = [e[1] for e in events]
    assert fractions == sorted(fractions) and events[-1] == ("done", 1.0, "Done")
    assert r.warnings == []


def test_english_skips_translation(tmp_path):
    t = FakeTranscriber("en", texts=["i need call the bank tomorrow"])
    llm = smart_llm()
    r = make(tmp_path, transcriber=t, llm=llm).run(AUDIO / "english_todo.wav")
    assert r.language == "en" and r.english == "i need call the bank tomorrow"
    assert not any("translator" in c["system"] for c in llm.calls)
    assert t.calls == [("en", "transcribe")]


def test_forced_language_skips_detection(tmp_path):
    t = FakeTranscriber("en")  # would detect English...
    r = make(tmp_path, transcriber=t, language="ur").run(AUDIO / "urdu_todo.wav", save=False)
    assert r.language == "ur" and r.note_path is None


def test_whisper_translation_mode(tmp_path):
    t = FakeTranscriber("ur")
    r = make(tmp_path, transcriber=t, translator="whisper").run(AUDIO / "urdu_todo.wav", save=False)
    assert ("ur", "translate") in t.calls
    assert r.english == "Today I will go to the bank."
    assert any("turbo" in w for w in r.warnings)  # default model is turbo


def test_falls_back_to_whisper_when_ollama_down(tmp_path):
    t = FakeTranscriber("ur")
    llm = FakeLLM(available=False)
    r = make(tmp_path, transcriber=t, llm=llm).run(AUDIO / "urdu_todo.wav")
    assert r.english == "Today I will go to the bank."
    assert r.clean == "" and r.insights.action_items == []
    assert any("Ollama" in w for w in r.warnings)
    assert llm.calls == []
    assert "Ollama" in Path(r.note_path).read_text(encoding="utf-8")


def test_no_llm_steps_when_disabled(tmp_path):
    llm = smart_llm()
    r = make(tmp_path, llm=llm, clean_text=False, extract_insights=False, translator="none").run(
        AUDIO / "urdu_todo.wav", save=False)
    assert llm.calls == [] and r.english == "" and r.warnings == []


def test_silent_audio_rejected(tmp_path):
    import subprocess
    wav = tmp_path / "silence.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                    "-t", "2", str(wav)], check=True)
    with pytest.raises(AudioError, match="silent"):
        make(tmp_path).run(wav)


def test_keep_audio_off(tmp_path):
    r = make(tmp_path, keep_audio=False).run(AUDIO / "urdu_todo.wav")
    assert r.audio_path is None


def test_missing_model_gives_single_clear_warning(tmp_path):
    llm = smart_llm()
    llm.has_model = lambda: False
    r = make(tmp_path, llm=llm).run(AUDIO / "urdu_todo.wav", save=False)
    assert llm.calls == []
    assert all("ollama pull gemma3:12b" in w for w in r.warnings if "AI model" in w)
    assert sum("not downloaded" in w for w in r.warnings) == 2  # translation fallback + skipped cleanup
