#!/usr/bin/env bash
set -euo pipefail
ROOT="/Users/hoangminhlong/Downloads/xuly_dangky_doanhnghiep"
APP="$ROOT/BusinessDossier.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$ROOT/macos_app/Info.plist" "$APP/Contents/Info.plist"
clang -fobjc-arc "$ROOT/macos_app/BusinessDossierApp.m" -framework Cocoa -framework WebKit -o "$APP/Contents/MacOS/BusinessDossier"
chmod +x "$APP/Contents/MacOS/BusinessDossier"
echo "$APP"
