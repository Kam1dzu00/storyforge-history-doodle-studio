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
if [[ -f "$ROOT/assets/app_icon.icns" ]]; then
  cp "$ROOT/assets/app_icon.icns" "$APP/Contents/Resources/HistoryDoodle.icns"
  /usr/libexec/PlistBuddy -c "Set :CFBundleIconFile HistoryDoodle.icns" "$APP/Contents/Info.plist"
fi
/usr/libexec/PlistBuddy -c "Set :CFBundleName History Doodle Studio" "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string History Doodle Studio" "$APP/Contents/Info.plist" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName History Doodle Studio" "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.historydoodle.studio" "$APP/Contents/Info.plist" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.historydoodle.studio" "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string 1.0" "$APP/Contents/Info.plist" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString 1.0" "$APP/Contents/Info.plist"
xattr -cr "$APP"
codesign --force --deep --sign - "$APP" >/dev/null
rm -rf "$TMP"
echo "$APP"
