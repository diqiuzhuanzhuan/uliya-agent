#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend"

python -m uvicorn app.main:app --reload --host "${BACKEND_HOST:-0.0.0.0}" --port "${BACKEND_PORT:-8000}"
