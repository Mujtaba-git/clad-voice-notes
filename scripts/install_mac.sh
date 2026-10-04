#!/usr/bin/env bash
# One-step installer for macOS (Apple Silicon).
#   ./scripts/install_mac.sh            # install everything + default AI model
#   LLM_MODEL=gemma3:4b ./scripts/install_mac.sh   # pick a lighter model
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP_HOME="$HOME/Library/Application Support/VoiceNotes"
VENV="$APP_HOME/venv"
LLM_MODEL="${LLM_MODEL:-gemma3:12b}"

say() { printf "\n\033[1;32m==> %s\033[0m\n" "$*"; }

if [[ "$(uname -s)" != "Darwin" ]]; then echo "This installer is for macOS."; exit 1; fi

if ! command -v brew >/dev/null; then
  say "Installing Homebrew (you may be asked for your password)"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

say "Installing ffmpeg, uv and Ollama"
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
command -v uv >/dev/null || brew install uv
if ! command -v ollama >/dev/null && [[ ! -d /Applications/Ollama.app ]]; then
  brew install --cask ollama || brew install ollama
fi

say "Creating Python environment in $VENV"
mkdir -p "$APP_HOME"
uv venv --allow-existing -p 3.11 "$VENV"
(cd "$REPO" && uv pip install --python "$VENV/bin/python" ".[mac]")

say "Starting Ollama and downloading the AI model ($LLM_MODEL, one-time download)"
if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
  if [[ -d /Applications/Ollama.app ]]; then open -a Ollama; else (ollama serve >/dev/null 2>&1 &); fi
  for _ in $(seq 1 30); do curl -sf http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done
fi
ollama pull "$LLM_MODEL"
"$VENV/bin/python" - <<PY
from voicenotes.config import load_settings, save_settings
s = load_settings(); save_settings(s.updated(llm_model="$LLM_MODEL"))
PY

say "Building VoiceNotes.app"
"$REPO/scripts/build_mac_app.sh" "$VENV" "$HOME/Applications"

say "Checking the installation"
"$VENV/bin/python" -m voicenotes doctor || true

say "Done! Open 'VoiceNotes' from ~/Applications (or Spotlight). The first recording downloads the Whisper model (~1.5 GB)."
