import numpy as np
import pytest

from voicenotes.audio import SAMPLE_RATE, AudioError, is_silent, load_audio, split_on_silence

from .conftest import AUDIO


def test_load_audio_decodes_wav_to_16k_mono():
    x = load_audio(AUDIO / "english_todo.wav")
    assert x.dtype == np.float32
    assert 14 < len(x) / SAMPLE_RATE < 17
    assert np.abs(x).max() <= 1.0


def test_load_audio_missing_file(tmp_path):
    with pytest.raises(AudioError):
        load_audio(tmp_path / "nope.wav")


def test_load_audio_garbage(tmp_path):
    p = tmp_path / "bad.m4a"
    p.write_bytes(b"not audio at all")
    with pytest.raises(AudioError):
        load_audio(p)


def _tone(seconds, amp=0.5):
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def test_split_short_audio_is_one_chunk():
    x = _tone(10)
    assert split_on_silence(x) == [(0, len(x))]


def test_split_cuts_at_silence_and_covers_everything():
    # 20 s speech, 1 s silence, 20 s speech -> cut should land inside the gap
    x = np.concatenate([_tone(20), np.zeros(SAMPLE_RATE, np.float32), _tone(20)])
    chunks = split_on_silence(x, max_chunk_s=28)
    assert chunks[0][0] == 0 and chunks[-1][1] == len(x)
    for (a, b), (c, _) in zip(chunks, chunks[1:]):
        assert b == c
    cut = chunks[0][1] / SAMPLE_RATE
    assert 20 <= cut <= 21
    assert all((b - a) / SAMPLE_RATE <= 28 for a, b in chunks)


def test_split_long_continuous_audio_respects_max():
    x = _tone(100)
    chunks = split_on_silence(x, max_chunk_s=28)
    assert all((b - a) / SAMPLE_RATE <= 28 for a, b in chunks)
    assert chunks[-1][1] == len(x)


def test_split_empty():
    assert split_on_silence(np.zeros(0, np.float32)) == []


def test_is_silent():
    assert is_silent(np.zeros(1000, np.float32))
    assert not is_silent(_tone(1))
