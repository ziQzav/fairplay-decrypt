#!/bin/sh
# Build FairPlay Decrypt.app: a double-clickable macOS app bundle that
# launches mac_gui.py with the system Python. Run `make` first so the
# `transform` binary exists.
set -eu

APP="build/FairPlay Decrypt.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

mkdir -p "$MACOS" "$RESOURCES"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleName</key>
	<string>FairPlay Decrypt</string>
	<key>CFBundleDisplayName</key>
	<string>FairPlay Decrypt</string>
	<key>CFBundleIdentifier</key>
	<string>io.github.ziqzav.fairplay-decrypt</string>
	<key>CFBundleVersion</key>
	<string>1.0</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleExecutable</key>
	<string>FairPlayDecrypt</string>
	<key>NSHighResolutionCapable</key>
	<true/>
	<key>LSMinimumSystemVersion</key>
	<string>11.0</string>
</dict>
</plist>
PLIST

cat > "$MACOS/FairPlayDecrypt" <<'LAUNCHER'
#!/bin/sh
# Launch the tkinter GUI with the user's Python (needs tkinter, e.g. the
# python.org build). Falls back to python3 and prints a hint if it is
# missing.
set -eu

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$APP_DIR/../../../.."

for PYTHON in python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
    if command -v "$PYTHON" >/dev/null 2>&1 &&
        "$PYTHON" -c 'import tkinter' >/dev/null 2>&1; then
        exec "$PYTHON" "$ROOT/mac_gui.py"
    fi
done

osascript -e 'display dialog "Python 3 with tkinter was not found. Install Python from python.org, then reopen FairPlay Decrypt." buttons "OK" default button "OK" with icon stop'
exit 1
LAUNCHER

chmod +x "$MACOS/FairPlayDecrypt"

echo "Built $APP — double-click it, or run: open \"$APP\""
