#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/Users/gianmarco/price-watcher"
LOG_DIR="$REPO_DIR/logs"
SLEEP_SECONDS=28800  # 8 horas

mkdir -p "$LOG_DIR"
cd "$REPO_DIR"

# Activar virtualenv si existe
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Cargar variables de entorno desde config/settings.example.env si existe
if [ -f "config/settings.example.env" ]; then
  # Ignorar líneas comentadas
  export $(grep -v '^#' config/settings.example.env | xargs) || true
fi

while true; do
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") Starting price-watcher run" >> "$LOG_DIR/bot_loop.log"
  # Ejecutar el bot (sin detener el script si falla)
  if python -u -m src.main >> "$LOG_DIR/bot_loop.log" 2>&1; then
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") Run finished successfully" >> "$LOG_DIR/bot_loop.log"
  else
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") Run failed (see log)" >> "$LOG_DIR/bot_loop.log"
  fi
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") Sleeping ${SLEEP_SECONDS}s (8h)" >> "$LOG_DIR/bot_loop.log"
  sleep "$SLEEP_SECONDS"
done
