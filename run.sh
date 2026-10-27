#!/usr/bin/env bash
# SpecAgent launcher — sets PYTHONPATH and delegates to main.py
# Usage: ./run.sh run "Build a todo API"
#        ./run.sh dashboard
#        ./run.sh config

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="${SCRIPT_DIR}/.lib:${SCRIPT_DIR}" \
  /opt/venv/bin/python3 "${SCRIPT_DIR}/main.py" "$@"
