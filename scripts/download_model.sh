#!/usr/bin/env bash
# Download UltraFace RFB-320 ONNX model for local face detection
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="$ROOT/models"
URL="https://github.com/onnx/models/raw/main/validated/vision/body_analysis/ultraface/models/version-RFB-320.onnx"
OUT="$MODEL_DIR/version-RFB-320.onnx"

mkdir -p "$MODEL_DIR"
if [[ -f "$OUT" ]]; then
  echo "Model already exists: $OUT"
  exit 0
fi

echo "Downloading UltraFace model..."
if command -v curl >/dev/null; then
  curl -L --fail -o "$OUT" "$URL"
elif command -v wget >/dev/null; then
  wget -O "$OUT" "$URL"
else
  echo "Need curl or wget" >&2
  exit 1
fi
echo "Saved to $OUT ($(du -h "$OUT" | cut -f1))"
