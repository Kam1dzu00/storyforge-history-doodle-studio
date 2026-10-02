from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = ROOT / "models"
PROJECTS_DIR = ROOT / "projects"
ASSETS_DIR = ROOT / "assets"
LOGS_DIR = ROOT / "logs"

LLM_REPO = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
IMAGE_MODEL = "flux2-klein-4b"
TTS_REPO = "hexgrad/Kokoro-82M"
WHISPER_REPO = "mlx-community/whisper-base-mlx"
DEFAULT_VOICE = "am_michael"
VOICES = ["am_michael", "am_eric", "am_liam", "am_onyx", "am_adam", "am_echo", "am_fenrir", "am_puck"]

STYLE_DIR = ASSETS_DIR / "style"
STYLE_BIBLE = STYLE_DIR / "style_bible.json"
STYLE_PROMPT = STYLE_DIR / "style_prompt.txt"
NEGATIVE_PROMPT = STYLE_DIR / "negative_prompt.txt"
STYLE_REFERENCE = STYLE_DIR / "style_reference.png"

def configure_model_cache() -> None:
    cache = MODELS_DIR / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache / "huggingface"))
    os.environ.setdefault("HF_HUB_CACHE", str(cache / "huggingface" / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache / "transformers"))
    os.environ.setdefault("MFLUX_MODEL_PATH", str(MODELS_DIR / "image"))

def ensure_dirs() -> None:
    for path in (MODELS_DIR / "llm", MODELS_DIR / "image", MODELS_DIR / "tts", MODELS_DIR / "whisper", MODELS_DIR / "cache", PROJECTS_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)
    configure_model_cache()

