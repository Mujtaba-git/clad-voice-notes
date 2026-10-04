import os

import pytest

from voicenotes.asr import available_backends, clean_segments, create_transcriber, normalize_language
from voicenotes.audio import load_audio
from voicenotes.models import Segment

from .conftest import AUDIO
from .fakes import FakeTranscriber, silence


@pytest.mark.parametrize("code,expected", [
    ("en", "en"), ("EN", "en"), ("ur", "ur"), ("hi", "ur"), ("pa", "ur"), ("", "ur"), (None, "ur"),
])
def test_normalize_language(code, expected):
    assert normalize_language(code) == expected


def test_clean_segments_drops_empty_and_collapses_loops():
    segs = [Segment(0, 1, " hello "), Segment(1, 2, ""), Segment(2, 3, "Thank you."),
            Segment(3, 4, "Thank you."), Segment(4, 5, "Thank you."), Segment(5, 6, "Thank you."),
            Segment(6, 7, "bye")]
    out = clean_segments(segs)
    assert [s.text for s in out] == ["hello", "Thank you.", "Thank you.", "bye"]
    assert out[2].end == 6  # the collapsed run keeps its time span


def test_fake_detects_hindi_as_urdu():
    assert FakeTranscriber("ur").detect_language(silence()) == "ur"
    assert FakeTranscriber("en").detect_language(silence()) == "en"


def test_transcribe_validates_arguments():
    t = FakeTranscriber()
    with pytest.raises(ValueError):
        t.transcribe(silence(), "auto")
    with pytest.raises(ValueError):
        t.transcribe(silence(), "ur", task="summarize")


def test_translate_task_reports_english():
    tr = FakeTranscriber().transcribe(silence(), "ur", task="translate")
    assert tr.language == "en"
    assert "bank" in tr.text


def test_progress_reaches_one():
    seen = []
    FakeTranscriber().transcribe(silence(), "ur", progress=seen.append)
    assert seen[-1] == 1.0


def test_factory_unknown_backend():
    with pytest.raises(ValueError):
        create_transcriber("nope")


def test_factory_auto_picks_something_installed():
    if not available_backends():
        pytest.skip("no backend installed")
    assert create_transcriber("auto", "tiny").name == available_backends()[0]


# ---------------------------------------------------------------- integration
# Real Whisper on the TTS fixtures. Uses the sherpa-onnx backend (models come
# from GitHub releases); set VOICENOTES_TEST_BACKEND=mlx on a Mac to test MLX.

BACKEND = os.environ.get("VOICENOTES_TEST_BACKEND", "sherpa-onnx")
MODEL = os.environ.get("VOICENOTES_TEST_MODEL", "small")


@pytest.fixture(scope="module")
def real():
    if BACKEND not in available_backends():
        pytest.skip(f"{BACKEND} not installed")
    return create_transcriber(BACKEND, MODEL)


@pytest.mark.integration
def test_real_detects_languages(real):
    assert real.detect_language(load_audio(AUDIO / "urdu_todo.wav")) == "ur"
    assert real.detect_language(load_audio(AUDIO / "english_todo.wav")) == "en"


@pytest.mark.integration
def test_real_english_transcription(real):
    text = real.transcribe(load_audio(AUDIO / "english_todo.wav"), "en").text.lower()
    for word in ["bank", "loan", "presentation", "monday", "groceries"]:
        assert word in text, (word, text)


@pytest.mark.integration
def test_real_urdu_transcription_is_urdu_script(real):
    text = real.transcribe(load_audio(AUDIO / "urdu_todo.wav"), "ur").text
    arabic_letters = sum("؀" <= c <= "ۿ" for c in text)
    assert arabic_letters > 0.6 * len(text.replace(" ", ""))
    for word in ["کاروبار", "بہن", "فون", "بازار", "خریدنی"]:  # last word must not be cut off
        assert word in text, (word, text)
