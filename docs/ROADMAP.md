# Roadmap

## ✅ Done (v0.1)

- [x] Milestone 1: research and architecture ([RESEARCH.md](RESEARCH.md), [ARCHITECTURE.md](ARCHITECTURE.md))
- [x] Milestone 2: Whisper speech-to-text with three backends, Urdu/English detection, tested on real audio
- [x] Milestone 3: Urdu→English translation (local LLM / Google / Whisper) with fallbacks
- [x] Milestone 4: grammar and structure cleanup that preserves details; key points and to-do extraction
- [x] Milestone 5: Obsidian Markdown notes (front matter, checkboxes, RTL Urdu)
- [x] Milestone 6: web UI with recording, crash recovery, file drop, progress, copy, settings
- [x] Milestone 7: macOS menu-bar app, one-command installer, DMG, CI on Apple Silicon, docs

## Next (suggested order)

1. **Try it on your own voice.** Record a few real 5–10 minute notes, then compare
   `gemma3:12b` with `qwen3:14b` and Whisper `large-v3-turbo` with `large-v3`. Pick the defaults that sound most like you.
2. **Editable prompt presets:** "Fix grammar only", "Summarise", "Blog draft", "Meeting minutes".
3. **Global hotkey** (e.g. ⌥-Space) to start/stop recording from anywhere, recording natively in the menu-bar app.
4. **Live preview** while speaking (streaming Whisper on 5-second windows).
5. **Urdu-tuned Whisper:** convert a Hugging Face Urdu fine-tune to MLX and offer it as a model option.
6. **History page:** browse, search and re-process past recordings.
7. **Custom vocabulary:** names and terms you use often, passed to Whisper as `initial_prompt`.
8. **Self-contained signed .app** (PyInstaller/Briefcase plus notarisation), so the installer no longer needs Homebrew or Python.
9. **Server deployment** (see "Future deployment" in [ARCHITECTURE.md](ARCHITECTURE.md)).
