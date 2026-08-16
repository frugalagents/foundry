#!/usr/bin/env bash
# Build the Lambda deployment package into .lambda-src/
set -euo pipefail

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$INFRA_DIR/../backend"
OUT="$INFRA_DIR/.lambda-src"

echo "→ Cleaning $OUT"
rm -rf "$OUT"
mkdir -p "$OUT"

echo "→ Installing Python dependencies (Linux x86_64 wheels)"
pip install \
  --quiet \
  --requirement "$BACKEND_DIR/requirements.txt" \
  --target "$OUT" \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade

echo "→ Copying backend source"
cp -r "$BACKEND_DIR/api" "$OUT/api"

echo "✓ Lambda package ready at $OUT"
echo "  Size: $(du -sh "$OUT" | cut -f1)"
