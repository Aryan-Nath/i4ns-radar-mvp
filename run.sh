#!/bin/sh
set -eu
cd "$(dirname "$0")"

if [ ! -x ./.venv/bin/python ]; then
  echo "Python environment missing. Create .venv and install requirements.txt (see README.md)." >&2
  exit 1
fi
if ! command -v npm >/dev/null || [ ! -x web/node_modules/.bin/vite ]; then
  echo "Frontend dependencies missing. Install Node.js and run npm ci --prefix web." >&2
  exit 1
fi

npm run build --prefix web
echo "i4NS Radar MVP: open http://localhost:8000"
exec ./.venv/bin/python -m uvicorn api:app --port 8000
