#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
# Homebrew's alternate Node 20 is used when installed, without changing host links.
if [[ -x /opt/homebrew/opt/node@20/bin/node ]]; then
  export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
fi
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python scripts/check_environment.py
