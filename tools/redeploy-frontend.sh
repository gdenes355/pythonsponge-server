#!/bin/bash
set -euo pipefail

REPO="gdenes355/python-frontend"
DEST_BASE="/home/pythonsponge/deployed"
NEW_DIR="$DEST_BASE/app-new"
OLD_DIR="$DEST_BASE/app-old"
CURRENT_DIR="$DEST_BASE/app"

# Fetch latest release info
echo "Fetching latest release info..."
RELEASE_INFO=$(curl -sSfL "https://api.github.com/repos/$REPO/releases/latest")

# Get .zip asset URL
ZIP_URL=$(echo "$RELEASE_INFO" | grep -Eo '"browser_download_url":\s*"[^"]+\.zip"' | cut -d '"' -f 4 | head -n 1)

if [[ -z "$ZIP_URL" ]]; then
  echo "❌ No .zip asset found in latest release"
  exit 1
fi

echo "Downloading asset: $ZIP_URL"
TMP_ZIP="/tmp/build.zip"
curl -sSfL "$ZIP_URL" -o "$TMP_ZIP"

# Clean existing app-new
rm -rf "$NEW_DIR"
mkdir -p "$NEW_DIR"

# Extract zip
echo "Extracting to $NEW_DIR..."
unzip -q "$TMP_ZIP" -d "$NEW_DIR"

# Verify build integrity
if [[ ! -f "$NEW_DIR/index.html" ]]; then
  echo "❌ index.html not found in extracted build. Aborting."
  exit 1
fi

# Swap folders
echo "Swapping deployments..."
rm -rf "$OLD_DIR"
if [[ -d "$CURRENT_DIR" ]]; then
  mv "$CURRENT_DIR" "$OLD_DIR"
fi
mv "$NEW_DIR" "$CURRENT_DIR"

# Cleanup
rm -rf "$OLD_DIR"
rm -f "$TMP_ZIP"

echo "✅ Deployment successful!"
