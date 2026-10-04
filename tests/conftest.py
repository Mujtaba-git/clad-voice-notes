import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
AUDIO = FIXTURES / "audio"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never touch the real user data dir during tests."""
    monkeypatch.setenv("VOICENOTES_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@pytest.fixture
def audio_manifest():
    return json.loads((AUDIO / "manifest.json").read_text(encoding="utf-8"))
