#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo '请先运行 scripts/setup.sh'; exit 1
fi
exec .venv/bin/python -m uvicorn studio.server:app --host 127.0.0.1 --port "${PORT:-8000}"
