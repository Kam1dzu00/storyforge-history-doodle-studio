# StoryForge: models, settings, and restoration

This repository intentionally does not store downloaded model weights. The `models/`
directory is ignored by Git because the current local cache is about 25 GB and contains
individual files larger than GitHub's limits. The application recreates the cache from
the model repositories below.

## Runtime

- macOS on Apple Silicon
- Python `>=3.12,<3.13`
- FFmpeg available on `PATH`
- Python environment: `uv sync`
- Run UI: `uv run history-doodle`
- Run CLI: `uv run history-doodle-cli`

The package versions are locked in `uv.lock`; primary dependency constraints are in
`pyproject.toml`.

## Required models

| Purpose | Hugging Face repository | Runtime |
| --- | --- | --- |
| Script and shot planning | `mlx-community/Qwen3-4B-Instruct-2507-4bit` | MLX-LM |
| Image generation | `black-forest-labs/FLUX.2-klein-4B` | MFLUX |
| English narration | `hexgrad/Kokoro-82M` | Kokoro `KPipeline(lang_code="a")` |
| Word timestamps | `mlx-community/whisper-base-mlx` | MLX Whisper |

Model identifiers are also defined in `src/history_doodle/config.py` and
`src/history_doodle/model_setup.py`.

## Local paths

At startup StoryForge sets:

- `HF_HOME=<repository>/models/cache/huggingface`
- `MFLUX_MODEL_PATH=<repository>/models/image`

Generated projects are stored under `<repository>/projects`; application logs are under
`<repository>/logs`. These directories are intentionally excluded from Git.

## Production defaults

- Default voice: `am_michael`
- Available voices: `am_michael`, `am_eric`, `am_liam`, `am_onyx`, `am_adam`,
  `am_echo`, `am_fenrir`, `am_puck`
- Standard video: H.264 MP4
- Standard audio master: AAC, 48 kHz stereo
- Word-level subtitle timing: Whisper MLX
- Narration/music mastering: loudness normalization plus side-chain ducking

Project-specific style, voice speed, music profile, seeds, resolution, and timing are
stored in each project's `project.json`, `voice_segments.json`, scene/shot manifests,
and logs. Generated project media is not part of the source-code backup unless archived
separately.

## Restore procedure

1. Clone the repository.
2. Install Python 3.12, `uv`, and FFmpeg.
3. Run `uv sync` in the repository root.
4. Run `uv run python -m history_doodle.model_setup` to download the four required
   model repositories into the project-local cache.
5. Run `uv run pytest`.
6. Start the application with `uv run history-doodle`.

The model licenses and access conditions remain those published with each upstream
Hugging Face repository. They must be reviewed separately before redistribution or
commercial distribution.
