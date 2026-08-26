#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  trap - INT TERM EXIT
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

cd "$ROOT/services/api"
uv run uvicorn fitness_api.main:app --reload --port 8000 &
API_PID=$!

cd "$ROOT/apps/web"
npm run dev &
WEB_PID=$!

# Plain wait keeps this compatible with the macOS Bash 3.2 default.
wait
