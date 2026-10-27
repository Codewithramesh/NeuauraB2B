#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -x .venv/bin/python ]] || { echo 'Run ./scripts/setup.sh first.'; exit 1; }
[[ -f frontend/dist/index.html ]] || { echo 'Build the frontend: cd frontend && npm run build'; exit 1; }
if [[ -f local-data/server.pid ]]; then
  prior_pid=$(cat local-data/server.pid)
  if [[ "$prior_pid" =~ ^[0-9]+$ ]] && kill -0 "$prior_pid" 2>/dev/null; then
    prior_command=$(ps -p "$prior_pid" -o command= || true)
    if [[ "$prior_command" == *"backend.app.main:app"* && "$prior_command" == *"$PWD"* ]]; then
      echo 'NEUAURA is already running. Open http://localhost:8000 or stop with ./scripts/stop.sh.'
      exit 0
    fi
  fi
fi
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
mkdir -p local-data
printf '%s\n' "$$" > local-data/server.pid
chmod 600 local-data/server.pid
printf '\nStarting NEUAURA on http://localhost:8000\nBackend + dashboard: one local service. Ctrl+C shuts down.\n'
printf 'First-run setup token: cat local-data/setup-token (after startup).\n'
exec .venv/bin/python -m uvicorn backend.app.main:app --app-dir "$PWD" --host 127.0.0.1 --port 8000 --workers 1
