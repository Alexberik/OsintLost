#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Ensure model
if [[ ! -f models/version-RFB-320.onnx ]]; then
  echo "Model not found — downloading..."
  bash scripts/download_model.sh
fi

# Optional: create venv if missing
if [[ ! -d .venv ]]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

export PORT="${PORT:-8090}"
echo "Starting OsintLost on http://0.0.0.0:${PORT}"
cd backend
exec ../.venv/bin/python server.py
