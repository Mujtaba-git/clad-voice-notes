#!/usr/bin/env bash
# Build a small VoiceNotes.app that launches the menu-bar app from a Python venv.
#   build_mac_app.sh <venv> <destination-folder>
set -euo pipefail
VENV="${1:?venv path}"
DEST="${2:-$HOME/Applications}"
APP="$DEST/VoiceNotes.app"

mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>VoiceNotes</string>
  <key>CFBundleDisplayName</key><string>VoiceNotes</string>
  <key>CFBundleIdentifier</key><string>local.voicenotes.app</string>
  <key>CFBundleVersion</key><string>0.1.0</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>CFBundleExecutable</key><string>VoiceNotes</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
</dict></plist>
PLIST
cat > "$APP/Contents/MacOS/VoiceNotes" <<LAUNCH
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:\$PATH"
LOG="\$HOME/Library/Logs/VoiceNotes.log"
exec "$VENV/bin/python" -m voicenotes.menubar >>"\$LOG" 2>&1
LAUNCH
chmod +x "$APP/Contents/MacOS/VoiceNotes"
echo "Built $APP"
