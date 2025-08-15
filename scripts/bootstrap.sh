#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/moot/Library/Mobile Documents/com~apple~CloudDocs/Documents/Programs/ITRStats"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
