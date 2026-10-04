import pytest

from voicenotes import cli


def test_version(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert "0.1.0" in capsys.readouterr().out


def test_doctor_runs(capsys, monkeypatch):
    monkeypatch.setattr("voicenotes.llm.OllamaClient.is_available", lambda self: False)
    code = cli.main(["doctor"])
    out = capsys.readouterr().out
    assert "ffmpeg installed" in out and "Ollama" in out
    assert code == 1  # Ollama is not running


def test_process_with_fakes(capsys, monkeypatch, tmp_path):
    from .fakes import FakeLLM, FakeTranscriber
    from .conftest import AUDIO

    monkeypatch.setattr("voicenotes.pipeline.create_transcriber", lambda b, m: FakeTranscriber("en", texts=["hello world"]))
    monkeypatch.setattr("voicenotes.pipeline.OllamaClient", lambda *a, **k: FakeLLM(available=False))
    code = cli.main(["process", str(AUDIO / "english_todo.wav"), "--vault", str(tmp_path)])
    cap = capsys.readouterr()
    assert code == 0 and "hello world" in cap.out and "Saved:" in cap.err
