from __future__ import annotations

import gc, hashlib, json, logging, subprocess
from pathlib import Path

def prompt_hash(prompt: str, negative: str = "") -> str:
    return hashlib.sha256((prompt + "\0" + negative).encode()).hexdigest()

def shot_seed(base_seed: int, index: int) -> int:
    return (base_seed + index * 1009) % 2_147_483_647

def run(args: list[str], *, check=True, capture=False) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=check, text=True, capture_output=capture)

def cleanup_models() -> None:
    gc.collect()
    try:
        import mlx.core as mx
        mx.clear_cache()
    except Exception:
        pass

def setup_logging(logfile: Path) -> None:
    logfile.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

def json_from_model_text(text: str) -> dict:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = clean.find("{"), clean.rfind("}")
    if start < 0 or end < start: raise ValueError("Model response did not contain JSON")
    return json.loads(clean[start:end + 1])

