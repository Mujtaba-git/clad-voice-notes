"""Browser end-to-end test: a headless Chromium "speaks" the Urdu fixture into
a fake microphone, the real UI records it, uploads it, and the real pipeline
(Whisper via sherpa-onnx + Google translation) produces a note.

Run: pytest tests/e2e -m integration   (needs: pip install playwright)
"""
import os
import socket
import threading
import time

import pytest

pw = pytest.importorskip("playwright.sync_api")

from voicenotes.config import Settings  # noqa: E402
from voicenotes.server import Engine, create_app  # noqa: E402

from ..conftest import AUDIO  # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.mark.integration
def test_record_in_browser_creates_note(tmp_path):
    import uvicorn

    settings = Settings(asr_backend=os.environ.get("VOICENOTES_TEST_BACKEND", "sherpa-onnx"),
                        asr_model=os.environ.get("VOICENOTES_TEST_MODEL", "small"),
                        translator=os.environ.get("VOICENOTES_TEST_TRANSLATOR", "google"),
                        vault_dir=str(tmp_path / "vault"), language="ur")
    app = create_app(Engine(settings, persist=False))
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)

    with pw.sync_playwright() as p:
        exe = os.environ.get("CHROMIUM_PATH") or ("/opt/pw-browsers/chromium" if os.path.isfile("/opt/pw-browsers/chromium") else None)
        browser = p.chromium.launch(executable_path=exe, args=[
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-audio-capture={AUDIO / 'urdu_todo.wav'}%noloop",
        ])
        page = browser.new_page()
        page.context.grant_permissions(["microphone"])
        page.goto(f"http://127.0.0.1:{port}/")
        page.select_option("#lang", "ur")
        page.click("#rec")
        page.wait_for_timeout(18000)  # the fixture is ~17 s long
        page.click("#rec")
        page.wait_for_selector("#result:not(.hidden)", timeout=240_000)
        tabs = page.inner_text("#tabs")
        assert "Original (Urdu)" in tabs
        page.click("[data-tab=english]")
        english = page.inner_text("#out").lower()
        page.screenshot(path=str(tmp_path / "result.png"), full_page=True)
        browser.close()
    server.should_exit = True

    assert "sister" in english and "market" in english, english
    notes = list((tmp_path / "vault" / "Voice Notes").glob("*.md"))
    assert len(notes) == 1
