#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
echo "Creating virtual environment..."
python3 -m venv .venv
fi

echo "Installing dependencies in .venv..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "Starting ghosf..."
exec .venv/bin/python app.py