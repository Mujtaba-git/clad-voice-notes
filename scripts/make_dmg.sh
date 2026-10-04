#!/usr/bin/env bash
# Package the project as VoiceNotes-Installer.dmg. Opening the DMG and
# double-clicking "Install VoiceNotes.command" runs install_mac.sh.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$REPO/dist/VoiceNotes-Installer.dmg}"
STAGE="$(mktemp -d)/VoiceNotes"
mkdir -p "$STAGE/voicenotes" "$(dirname "$OUT")"
git -C "$REPO" archive HEAD | tar -x -C "$STAGE/voicenotes"
cat > "$STAGE/Install VoiceNotes.command" <<'CMD'
#!/bin/bash
cd "$(dirname "$0")"
SRC="$HOME/Library/Application Support/VoiceNotes/source"
mkdir -p "$SRC" && rsync -a --delete voicenotes/ "$SRC/"
"$SRC/scripts/install_mac.sh"
echo; read -n 1 -s -r -p "Press any key to close this window"
CMD
chmod +x "$STAGE/Install VoiceNotes.command"
cp "$REPO/docs/SETUP.md" "$STAGE/README - Setup.md"
hdiutil create -volname "VoiceNotes" -srcfolder "$STAGE" -ov -format UDZO "$OUT"
echo "Created $OUT"
