from __future__ import annotations

import platform, shutil
from pathlib import Path
import psutil
from .config import MODELS_DIR, PROJECTS_DIR, STYLE_REFERENCE

def check() -> dict:
    hf = MODELS_DIR/"cache/huggingface/hub"
    names = "\n".join(str(x) for x in hf.glob("models--*")) if hf.exists() else ""
    return {
        "Apple Silicon": platform.machine() == "arm64",
        "RAM": f"{round(psutil.virtual_memory().total/1024**3)} GB",
        "Qwen": "models--mlx-community--Qwen3-4B-Instruct-2507-4bit" in names,
        "FLUX": "models--black-forest-labs--FLUX.2-klein-4B" in names,
        "Kokoro": "models--hexgrad--Kokoro-82M" in names,
        "Whisper": "models--mlx-community--whisper-base-mlx" in names,
        "FFmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
        "Models location": str(MODELS_DIR),
        "Projects location": str(PROJECTS_DIR),
        "Style reference": str(STYLE_REFERENCE) if STYLE_REFERENCE.exists() else "Not set (prompt-only mode)",
    }

