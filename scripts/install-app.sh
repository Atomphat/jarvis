#!/bin/bash
# Installs Jarvis.app into ~/Applications, signs it ad hoc and adds it to Login Items.
set -euo pipefail
cd "$(dirname "$0")/.."
pkill -f "Jarvis.app/Contents/MacOS/Jarvis" 2>/dev/null || true
pkill -f -- "-m jarvis.app" 2>/dev/null || true
sleep 1
mkdir -p ~/Applications logs
rm -rf ~/Applications/Jarvis.app
cp -R macapp/Jarvis.app ~/Applications/
chmod +x ~/Applications/Jarvis.app/Contents/MacOS/Jarvis
codesign --force --deep -s - ~/Applications/Jarvis.app
osascript -e 'tell application "System Events"
  if not (exists login item "Jarvis") then make login item at end with properties {path:"'"$HOME"'/Applications/Jarvis.app", hidden:true}
end tell'
open ~/Applications/Jarvis.app
echo "Jarvis installed and started"
