#!/bin/zsh
set -e
ROOT="${0:A:h}"
cd "$ROOT"
exec "$ROOT/.venv/bin/python" -m history_doodle.app

