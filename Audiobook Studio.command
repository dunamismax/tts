#!/bin/zsh
# Double-click this file to open Audiobook Studio in your web browser.
# Keep the Terminal window it opens running while you use the studio (you can minimize it).
cd "$(dirname "$0")"
if lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  open "http://127.0.0.1:8765/"
  exit 0
fi
exec ./audiobook.py web
