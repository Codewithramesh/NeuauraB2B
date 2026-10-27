#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
if [[ ! -d .venv ]]; then
  if [[ -x /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 ]]; then
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m venv .venv
  else
    python3 -m venv .venv
  fi
fi
.venv/bin/python -m pip install -r backend/requirements.txt
if [[ ! -f .env ]]; then cp .env.example .env; chmod 600 .env; fi
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
(cd frontend && npm ci && npm run build)
printf '\nNEUAURA installed. Start: ./scripts/start.sh\n'
printf 'Speech model (about 75 MB, explicit download): .venv/bin/python scripts/download_model.py\n'
printf 'AI engine setup: docs/LOCAL_SETUP.md\n'
