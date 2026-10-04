import json

import pytest
from fastapi.testclient import TestClient

from voicenotes.config import Settings, load_settings
from voicenotes.server import Engine, create_app

from .conftest import AUDIO
from .fakes import FakeLLM, FakeTranscriber


def llm_factory(settings):
    def respond(system, prompt, fmt):
        if fmt is not None:
            return json.dumps({"title": "Errands", "key_points": ["k"], "action_items": ["Go to the bank"]})
        return "Tomorrow I will go to the bank."
    return FakeLLM(respond)


@pytest.fixture
def client(tmp_path):
    engine = Engine(Settings(vault_dir=str(tmp_path / "vault")),
                    transcriber_factory=lambda b, m: FakeTranscriber("ur"), llm_factory=llm_factory)
    app = create_app(engine)
    with TestClient(app) as c:
        c.app = app
        yield c


def test_index_serves_ui(client):
    r = client.get("/")
    assert r.status_code == 200 and "VoiceNotes" in r.text and "MediaRecorder" in r.text


def test_status(client):
    s = client.get("/api/status").json()
    assert s["ollama"] is True and "backends" in s


def test_settings_roundtrip_and_persist(client):
    r = client.put("/api/settings", json={"language": "ur", "llm_model": "qwen3:8b"})
    assert r.status_code == 200 and r.json()["language"] == "ur"
    assert client.get("/api/settings").json()["llm_model"] == "qwen3:8b"
    assert load_settings().llm_model == "qwen3:8b"


def test_settings_rejects_bad_values(client):
    assert client.put("/api/settings", json={"language": "fr"}).status_code == 400
    assert client.put("/api/settings", json={"bogus": 1}).status_code == 400


def test_upload_processes_and_saves_note(client, tmp_path, isolated_home):
    with open(AUDIO / "urdu_todo.wav", "rb") as f:
        r = client.post("/api/jobs", files={"file": ("my note.wav", f, "audio/wav")}, data={"language": "ur"})
    assert r.status_code == 200
    job = client.app.state.jobs.wait(r.json()["id"])
    assert job.status == "done", job.error
    res = client.get(f"/api/jobs/{job.id}").json()["result"]
    assert res["insights"]["action_items"] == ["Go to the bank"]
    assert res["note_path"].startswith(str(tmp_path / "vault"))
    # upload stored in recordings and reused as the kept audio (no duplicate copy)
    recs = list((isolated_home / "recordings").iterdir())
    assert len(recs) == 1 and res["audio_path"] == str(recs[0])
    assert client.get("/api/jobs").json()[0]["id"] == job.id


def test_failed_job_reports_error_and_can_retry(client, tmp_path):
    bad = tmp_path / "bad.m4a"
    bad.write_bytes(b"garbage")
    with open(bad, "rb") as f:
        r = client.post("/api/jobs", files={"file": ("bad.m4a", f)})
    job = client.app.state.jobs.wait(r.json()["id"])
    assert job.status == "error" and "ffmpeg" in job.error
    r2 = client.post(f"/api/jobs/{job.id}/retry")
    assert r2.status_code == 200 and r2.json()["id"] != job.id


def test_upload_validation(client):
    assert client.post("/api/jobs", files={"file": ("x.wav", b"")}).status_code == 400
    assert client.post("/api/jobs", files={"file": ("x.wav", b"abc")}, data={"language": "fr"}).status_code == 400
    assert client.get("/api/jobs/nope").status_code == 404
