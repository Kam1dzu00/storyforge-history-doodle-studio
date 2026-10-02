from pathlib import Path
import os

_root = Path(__file__).resolve().parents[2]
_cache = _root / "models" / "cache"
os.environ.setdefault("HF_HOME", str(_cache / "huggingface"))
os.environ.setdefault("HF_HUB_CACHE", str(_cache / "huggingface" / "hub"))
os.environ.setdefault("TRANSFORMERS_CACHE", str(_cache / "transformers"))
os.environ.setdefault("MFLUX_MODEL_PATH", str(_root / "models" / "image"))

__version__ = "1.0.0"
