#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f local-data/server.pid ]]; then echo 'No tracked NEUAURA server. For dev.sh, press Ctrl+C in its terminal.'; exit 0; fi
server_pid=$(cat local-data/server.pid)
if [[ ! "$server_pid" =~ ^[0-9]+$ ]]; then echo 'Invalid PID file; no process was stopped.'; exit 1; fi
server_command=$(ps -p "$server_pid" -o command= || true)
if [[ "$server_command" == *"backend.app.main:app"* && "$server_command" == *"$PWD"* ]]; then
  kill -TERM "$server_pid"
  echo 'NEUAURA shutdown requested. Queued work and saved records persist.'
else
  echo 'The tracked NEUAURA process is no longer running.'
fi
rm -f local-data/server.pid
