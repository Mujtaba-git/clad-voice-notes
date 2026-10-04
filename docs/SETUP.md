# Setting up VoiceNotes on your Mac

This guide assumes no development experience. It takes about 15 minutes, mostly
spent downloading the AI models (one time only).

**You need:** a Mac with Apple Silicon (M1–M4; written for an M3 Pro), macOS 13 or later,
and about **15 GB free disk** for the tools and models.

---

## Option A: one command (recommended)

1. Open **Terminal** (⌘-Space, type *Terminal*, press Enter).
2. Paste these lines and press Enter:

   ```bash
   git clone https://github.com/Mujtaba-git/clad-voice-notes.git ~/clad-voice-notes
   cd ~/clad-voice-notes
   ./scripts/install_mac.sh
   ```

   If macOS asks to install the *Command Line Tools* (for `git`), click **Install**, wait, then run the lines again.

The installer:

| Step | What it installs | Size |
|---|---|---|
| Homebrew | Mac package manager (skipped if you have it) | — |
| ffmpeg | reads any audio format | ~100 MB |
| uv + Python 3.11 | private Python environment in `~/Library/Application Support/VoiceNotes/venv` | ~300 MB |
| Ollama | runs the local AI model | ~500 MB |
| `gemma3:12b` | the local AI for translation and grammar | ~8 GB |
| VoiceNotes.app | launcher in `~/Applications` | tiny |

The Whisper speech model (~1.6 GB) downloads automatically the first time you process a recording.

## Option B: DMG installer

Each CI run on GitHub produces `VoiceNotes-Installer.dmg`
(*Actions* tab → latest *CI* run → *Artifacts*). To build it yourself: `./scripts/make_dmg.sh`.
Open the DMG and double-click **Install VoiceNotes.command**. It runs the same installer as Option A.
If macOS says the file is from an unidentified developer, right-click it → **Open**.

---

## First run

1. Open **VoiceNotes** from `~/Applications` (or Spotlight). A 🎙️ appears in the menu bar and the app opens in your browser at <http://127.0.0.1:8765>.
2. Click **Settings**:
   - **Obsidian vault folder:** the full path of your vault, e.g. `/Users/you/Documents/Obsidian/MyVault`. (In Finder, right-click the vault folder while holding ⌥ Option → *Copy as Pathname*.)
   - **Sub-folder:** where notes go inside the vault (default `Voice Notes`).
   - **Default spoken language:** set **Urdu** if you mostly speak Urdu. It is faster and more reliable than auto-detect.
3. Click **Save**, then **Record**. Your browser asks for microphone access once; allow it.
4. Speak, press **Stop** (or Space), and wait. You'll see progress for each step. When it's done, the note is already in Obsidian.

**Tips**
- Long sessions are safe: the browser saves your audio every 5 seconds. If the tab or Mac crashes, reopen the app and click **Process it**.
- Every recording is also kept in `~/Library/Application Support/VoiceNotes/recordings`. You can reprocess one at any time by dropping it on the page.
- If something fails, the recording is not lost: click **Retry**.

## Choosing models (Settings)

| Setting | Default | Faster / lighter | More accurate |
|---|---|---|---|
| Whisper model | `large-v3-turbo` | `medium`, `small` | `large-v3` |
| Local AI model | `gemma3:12b` | `gemma3:4b` | `gemma3:27b` (needs 32 GB+ RAM) |

To try another AI model, run `ollama pull <name>` in Terminal, then type the name in Settings.
`qwen3:8b` and `qwen3:14b` are also good multilingual choices.

**Translation options**
- **Local AI (default):** best quality. It understands mixed Urdu and English and fixes recognition errors from context. Offline.
- **Whisper built-in:** offline and needs no Ollama, but rougher. Use the `large-v3` model for it (`turbo` was not trained to translate).
- **Google Translate:** online and free. It is close to what you used before, but it translates recognition mistakes literally.
- **Don't translate:** keeps only the Urdu transcript.

**Rough speed on an M3 Pro** (estimate; depends on RAM and model):
transcription with `large-v3-turbo` takes a few minutes per hour of audio. Translation and cleanup with `gemma3:12b` take a few more minutes per hour of speech.

## Command line (optional)

```bash
VN="$HOME/Library/Application Support/VoiceNotes/venv/bin/python"
"$VN" -m voicenotes process ~/Downloads/memo.m4a --language ur
"$VN" -m voicenotes doctor
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Yellow banner: *Ollama is not running* | Open the **Ollama** app (or run `ollama serve`). |
| *Model … is not downloaded* | `ollama pull gemma3:12b` |
| Nothing happens when opening the app | See the log: `~/Library/Logs/VoiceNotes.log` |
| Urdu comes out in Hindi (Devanagari) script | Set *Spoken language* to **Urdu** instead of Auto-detect. |
| Mac becomes slow / runs out of memory | Use `gemma3:4b` and/or Whisper `medium`. |
| Check everything | `"$VN" -m voicenotes doctor` |

## Updating

```bash
cd ~/clad-voice-notes && git pull && ./scripts/install_mac.sh
```

## Uninstalling

Delete `~/Applications/VoiceNotes.app` and `~/Library/Application Support/VoiceNotes`
(this also deletes your kept recordings; your Obsidian notes are not touched).
Optionally `brew uninstall ollama` and `rm -rf ~/.ollama ~/.cache/huggingface`.
