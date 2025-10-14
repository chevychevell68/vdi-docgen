#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip >/dev/null 2>&1 || true
python -m pip install -r requirements.txt
python -m gunicorn app:app --bind 0.0.0.0:${PORT:-5000}
