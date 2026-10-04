"""macOS menu-bar launcher: runs the local server and opens the UI.

Started by the VoiceNotes.app bundle (see scripts/build_mac_app.sh).
"""
from __future__ import annotations

import threading
import time
import webbrowser

import httpx

from .cli import DEFAULT_PORT

URL = f"http://127.0.0.1:{DEFAULT_PORT}"


def _server_running() -> bool:
    try:
        return httpx.get(f"{URL}/api/status", timeout=1).status_code == 200
    except httpx.HTTPError:
        return False


def _start_server():
    import uvicorn

    from .server import create_app

    uvicorn.run(create_app(), host="127.0.0.1", port=DEFAULT_PORT, log_level="warning")


def main():
    import rumps  # macOS only

    if not _server_running():
        threading.Thread(target=_start_server, daemon=True).start()
        for _ in range(100):
            if _server_running():
                break
            time.sleep(0.1)

    app = rumps.App("VoiceNotes", title="🎙️", quit_button="Quit VoiceNotes")
    app.menu = [rumps.MenuItem("Open VoiceNotes", callback=lambda _: webbrowser.open(URL))]
    webbrowser.open(URL)
    app.run()


if __name__ == "__main__":
    main()
