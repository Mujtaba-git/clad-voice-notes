"""Command line: `voicenotes serve | process FILE | doctor`."""
from __future__ import annotations

import argparse
import shutil
import sys
import threading
import webbrowser

from . import __version__
from .config import data_dir, load_settings, settings_path

DEFAULT_PORT = 8765


def cmd_serve(args) -> int:
    import uvicorn

    from .server import create_app

    url = f"http://127.0.0.1:{args.port}"
    print(f"VoiceNotes {__version__} running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="warning")
    return 0


def cmd_process(args) -> int:
    from .pipeline import Pipeline

    settings = load_settings()
    changes = {}
    if args.translator:
        changes["translator"] = args.translator
    if args.model:
        changes["asr_model"] = args.model
    if args.backend:
        changes["asr_backend"] = args.backend
    if args.vault:
        changes["vault_dir"] = args.vault
    if args.llm_model:
        changes["llm_model"] = args.llm_model
    if changes:
        settings = settings.updated(**changes)

    def progress(stage, frac, msg):
        print(f"\r[{frac * 100:5.1f}%] {msg:<45}", end="", file=sys.stderr, flush=True)

    result = Pipeline(settings).run(args.file, progress=progress, save=not args.no_save,
                                    language=None if args.language == "auto" else args.language)
    print(file=sys.stderr)
    for w in result.warnings:
        print(f"warning: {w}", file=sys.stderr)
    print(result.clean or result.english or result.original)
    if result.note_path:
        print(f"\nSaved: {result.note_path}", file=sys.stderr)
    return 0


def cmd_doctor(args) -> int:
    from .asr import available_backends
    from .llm import LLMError, OllamaClient

    s = load_settings()
    ok = True

    def line(good, label, hint=""):
        nonlocal ok
        ok &= bool(good)
        print(f"{'✅' if good else '❌'} {label}" + (f"\n     → {hint}" if hint and not good else ""))

    print(f"VoiceNotes {__version__}\nData folder: {data_dir()}\nSettings:    {settings_path()}\n")
    line(shutil.which("ffmpeg"), "ffmpeg installed", "brew install ffmpeg")
    b = available_backends()
    line(b, f"speech engine(s): {', '.join(b) or 'none'}", "pip install 'voicenotes[mac]'")
    llm = OllamaClient(s.ollama_url, s.llm_model)
    up = llm.is_available()
    line(up, f"Ollama reachable at {s.ollama_url}", "install from https://ollama.com and open the app")
    if up:
        try:
            line(llm.has_model(), f"LLM model '{s.llm_model}' downloaded", f"ollama pull {s.llm_model}")
        except LLMError as e:
            line(False, str(e))
    print(f"\nNotes are saved to: {s.notes_dir()}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="voicenotes", description="Urdu/English voice notes to clean English text.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("serve", help="start the local web app (default)")
    s.add_argument("--port", type=int, default=DEFAULT_PORT)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--no-browser", action="store_true")
    s.set_defaults(func=cmd_serve)

    pr = sub.add_parser("process", help="process an audio file and print the result")
    pr.add_argument("file")
    pr.add_argument("--language", choices=["auto", "ur", "en"], default="auto")
    pr.add_argument("--translator", choices=["llm", "whisper", "google", "none"])
    pr.add_argument("--model", help="Whisper model, e.g. large-v3-turbo")
    pr.add_argument("--backend", choices=["auto", "mlx", "faster-whisper", "sherpa-onnx"])
    pr.add_argument("--vault", help="folder to save the note in")
    pr.add_argument("--llm-model", help="Ollama model, e.g. gemma3:12b")
    pr.add_argument("--no-save", action="store_true")
    pr.set_defaults(func=cmd_process)

    d = sub.add_parser("doctor", help="check that everything is installed")
    d.set_defaults(func=cmd_doctor)

    args = p.parse_args(argv)
    if not args.cmd:
        args = p.parse_args(["serve", *(argv or [])])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
