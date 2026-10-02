#!/bin/zsh
set -e
ROOT="${0:A:h}"
cd "$ROOT"
if [[ "$(uname -m)" != "arm64" ]]; then echo "History Doodle Studio requires Apple Silicon."; read; exit 1; fi
if ! command -v uv >/dev/null 2>&1; then curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; fi
uv python install 3.12
uv sync
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then brew install ffmpeg; else echo "FFmpeg is missing. Install Homebrew from https://brew.sh and rerun setup."; read; exit 1; fi
fi
mkdir -p models/{llm,image,tts,whisper,cache} projects logs
uv run python -m history_doodle.model_setup
uv run pytest
./scripts/build_launcher.command
echo "Setup complete. Open HistoryDoodle Studio.app"
read

