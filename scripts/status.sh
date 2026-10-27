#!/usr/bin/env bash
cd "$(dirname "$0")/.."
if curl -fsS http://127.0.0.1:8000/api/v1/health; then printf '\nBackend + built dashboard reachable.\n'; else echo 'Backend is not reachable.'; exit 1; fi
if curl -fsS http://127.0.0.1:5173 >/dev/null 2>&1; then echo 'Vite development frontend reachable.'; else echo 'Vite not running (not needed for built dashboard).'; fi
