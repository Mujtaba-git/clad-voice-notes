# Architecture

## Goals that drove the design

1. **Local and free.** No subscriptions or per-use credits; works offline.
2. **Urdu first.** Accurate Urdu→English, including Urdu mixed with English words.
3. **Never lose details.** Cleanup must not quietly summarise. Recordings are never lost.
4. **Long recordings.** 30–60 minute sessions are the normal case.
5. **Small, testable pieces.** Every stage can be swapped and tested in isolation.
6. **Ready to deploy later.** The same engine can run as a server.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | The whole speech/ML ecosystem is in Python |
| Speech-to-text | **Whisper**, three interchangeable backends:<br>• `mlx-whisper` (Apple GPU; default on Mac)<br>• `faster-whisper` (CPU, cross-platform)<br>• `sherpa-onnx` (CPU; models from GitHub, used in cloud CI) | Whisper is the best open model for Urdu, with punctuation and code-switching support. MLX is the fastest way to run it on Apple Silicon. |
| Translation + cleanup | Local LLM via **Ollama** (default `gemma3:12b`) | Free, offline. Gemma 3 covers 140+ languages including Urdu. Ollama makes swapping models a one-liner. |
| Optional online translation | Google Translate web endpoint | Free and familiar. Opt-in only. |
| Audio decoding | ffmpeg | Reads every format (m4a, webm, mp3, …) |
| Backend | FastAPI + uvicorn, in-process job queue | Small, typed, easy to deploy later |
| UI | One static HTML page (no build step) | Browser `MediaRecorder` for recording, IndexedDB for crash recovery |
| Mac shell | `rumps` menu-bar app + a `.app` bundle + DMG installer | A real Mac app feel without bundling 2 GB of ML libraries |
| Tests | pytest, httpx MockTransport, Playwright | See [TESTING.md](TESTING.md) |
| CI | GitHub Actions: Linux + **macOS Apple Silicon** | Tests the real Mac path (MLX + Ollama) and builds the DMG |

## Data flow

```
 Browser UI ──(upload)──▶ POST /api/jobs ──▶ saved to recordings/ ──▶ JobManager (1 worker thread)
                                                                         │
                                                                         ▼
 ┌──────────────────────────────── Pipeline.run() ───────────────────────────────────────┐
 │ load_audio (ffmpeg → 16 kHz mono)                                                     │
 │   └▶ detect_language (first 30 s; anything not English ⇒ Urdu)                        │
 │       └▶ Transcriber.transcribe(lang)  → original transcript (Urdu script / English)  │
 │           └▶ if Urdu: Translator (LLM | Google | Whisper-translate) → English         │
 │               └▶ Refiner.clean (chunked, length-guarded) → clean English              │
 │                   └▶ Refiner.insights (JSON schema, map-reduce) → title/points/to-dos │
 │                       └▶ save_note → <vault>/Voice Notes/2026-10-04 1830 <title>.md   │
 └───────────────────────────────────────────────────────────────────────────────────────┘
                                                                         │
 Browser polls GET /api/jobs  ◀────────── progress (stage, %, message) ──┘
```

## Modules (`src/voicenotes/`)

| Module | Responsibility |
|---|---|
| `config.py` | `Settings` dataclass, JSON persistence, data folder (`~/Library/Application Support/VoiceNotes`) |
| `audio.py` | ffmpeg decoding; silence-aware chunking (≤28 s) for backends without long-form support |
| `asr/base.py` | `Transcriber` interface; language normalisation (Hindi→Urdu); removal of Whisper repetition loops |
| `asr/mlx_backend.py`, `faster_whisper_backend.py`, `sherpa_backend.py` | The three Whisper backends |
| `asr/factory.py` | Picks the best installed backend (`mlx` → `faster-whisper` → `sherpa-onnx`) |
| `llm.py` | Minimal Ollama client (`/api/chat`, JSON-schema output, strips `<think>` blocks) |
| `prompts.py` | All LLM prompts in one place |
| `translate.py` | `LLMTranslator` (chunked, with previous-chunk context) and `GoogleTranslator` (retries/backoff) |
| `refine.py` | Grammar/structure cleanup and insight extraction |
| `textutils.py` | Sentence splitting aware of Urdu `۔ ؟`; sentence-preserving chunking |
| `notes.py` | Obsidian Markdown rendering (front matter, checkboxes, RTL Urdu block), safe file names |
| `pipeline.py` | Orchestration, weighted progress, fallbacks, warnings |
| `jobs.py` | Background queue: one job at a time so two big models never compete for RAM |
| `server.py` | FastAPI app; `Engine` caches the loaded Whisper model between jobs |
| `cli.py` | `serve`, `process`, `doctor` |
| `menubar.py` | macOS menu-bar launcher |
| `static/index.html` | The whole UI |

## Key design decisions

**Transcribe in Urdu, then translate with an LLM, instead of using Whisper's translation.**
Measured on our test clip: Whisper's built-in translation turned "submit the loan
application" into "get the duty of Friday". Google Translate on the transcript produced
"get the wallet". A transcript plus an LLM that is told *"this is a speech-recognition
transcript, infer the intended words"* can recover those. Keeping the Urdu transcript also
lets you check the translation against what you said.

**Treat any non-English detection as Urdu.** Whisper's auto-detect labelled our Urdu
clip as Hindi and wrote Devanagari. You speak only Urdu or English, so the app forces
the language to `ur` in that case. Setting the language explicitly is fastest.

**Guard against summarising.** If a cleaned chunk has fewer than 50% of the original
words, the original wording is kept and a warning is added to the note. When to-do
lists from different parts of the recording are merged, the merge cannot drop more
than half of the tasks.

**Chunk everything for long recordings.** A 60-minute talk is about 8–9k words.
Translation uses ~1,200-character chunks (each with the previous chunk's English as
context). Cleanup uses ~3,000-character chunks. Insights are extracted per chunk and
then merged. Each LLM call stays well inside the context window of a small model.

**Never lose a recording.** The browser stores audio in IndexedDB every 5 s while
recording. The server writes the upload to `recordings/` *before* processing. Failed
jobs can be retried.

**Graceful degradation.** If Ollama is down, translation falls back to Whisper and
cleanup is skipped. The note is still saved, with a visible warning.

## Future deployment

The engine is already a plain HTTP service, so deploying it later is mostly packaging:

- **Self-hosted server / home lab:** `voicenotes serve --host 0.0.0.0` behind a reverse
  proxy with authentication. Use `faster-whisper` on an NVIDIA GPU (`device="cuda"`) and
  Ollama or vLLM for the LLM.
- **Container:** a Dockerfile with `.[cpu]` extras plus ffmpeg; mount a volume for
  `VOICENOTES_HOME`.
- **Multi-user:** replace the in-memory `JobManager` with a persistent queue
  (Redis/RQ, Celery), store jobs in SQLite/Postgres, and add accounts.
- **Phone capture:** the UI already works in mobile browsers on the same network, and
  recordings from the iPhone Voice Memos app can be dropped in today.

The interfaces (`Transcriber`, `Translator`, the LLM `chat()` method) are the seams for
adding cloud providers, other languages, or speaker diarisation later.
