#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1 &
backend_pid=$!
(cd frontend && exec npm run dev) &
frontend_pid=$!
cleanup() { kill "$frontend_pid" "$backend_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
for attempt in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null || { echo 'Backend failed. Inspect output above.'; exit 1; }
printf '\nBackend: http://localhost:8000 — ready\nFrontend: http://localhost:5173 — starting\nCtrl+C stops both.\n'
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do sleep 2; done
echo 'A service stopped. Shutting down both; inspect logs above.'
exit 1
