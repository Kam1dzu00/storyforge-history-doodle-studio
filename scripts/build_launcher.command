#!/bin/zsh
set -e
ROOT="${0:A:h:h}"
APP="$ROOT/HistoryDoodle Studio.app"
TMP="$(mktemp -d)"
cat > "$TMP/launcher.applescript" <<APPLESCRIPT
on run
  do shell script "cd " & quoted form of "$ROOT" & " && nohup " & quoted form of "$ROOT/.venv/bin/python" & " -m history_doodle.app >" & quoted form of "$ROOT/logs/launcher.log" & " 2>&1 &"
end run
APPLESCRIPT
rm -rf "$APP"
osacompile -o "$APP" "$TMP/launcher.applescript"
rm -rf "$TMP"
echo "$APP"

