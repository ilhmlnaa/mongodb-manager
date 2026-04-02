#!/usr/bin/env sh
set -eu

TOOLS_VERSION="100.16.0"
DISTRO="ubuntu2404"
BASE_URL="https://fastdl.mongodb.org/tools/db"

ARCH="$(uname -m)"

case "$ARCH" in
  x86_64|amd64)
    ARCH_SUFFIX="x86_64"
    ;;
  aarch64|arm64)
    ARCH_SUFFIX="arm64"
    ;;
  *)
    echo "Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

ARCHIVE_NAME="mongodb-database-tools-${DISTRO}-${ARCH_SUFFIX}-${TOOLS_VERSION}.tgz"
DOWNLOAD_URL="${BASE_URL}/${ARCHIVE_NAME}"
EXTRACTED_DIR="mongodb-database-tools-${DISTRO}-${ARCH_SUFFIX}-${TOOLS_VERSION}"

TARGET_DIR="/app/mongo-tools/linux/bin"
TMP_DIR="/tmp/mongodb-tools"
REQUIRED_TOOLS="mongodump mongorestore"

mkdir -p "$TMP_DIR" "$TARGET_DIR"

curl -fsSL "$DOWNLOAD_URL" -o "$TMP_DIR/$ARCHIVE_NAME"
tar -xzf "$TMP_DIR/$ARCHIVE_NAME" -C "$TMP_DIR"

for tool in $REQUIRED_TOOLS; do
  cp "$TMP_DIR/$EXTRACTED_DIR/bin/$tool" "$TARGET_DIR/$tool"
done
chmod +x "$TARGET_DIR/"*

rm -rf "$TMP_DIR"

echo "MongoDB Database Tools installed to $TARGET_DIR (tools: $REQUIRED_TOOLS)"