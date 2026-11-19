#!/bin/sh
cd "$(dirname "$0")"
echo "i4NS Radar MVP: open http://localhost:8000"
exec ./.venv/bin/python -m uvicorn api:app --port 8000
