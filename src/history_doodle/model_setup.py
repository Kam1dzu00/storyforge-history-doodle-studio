from __future__ import annotations

from .config import configure_model_cache, ensure_dirs

MODELS = [
    "mlx-community/Qwen3-4B-Instruct-2507-4bit",
    "black-forest-labs/FLUX.2-klein-4B",
    "hexgrad/Kokoro-82M",
    "mlx-community/whisper-base-mlx",
]

def main():
    ensure_dirs(); configure_model_cache()
    from huggingface_hub import snapshot_download
    for repo in MODELS:
        print(f"Downloading {repo}…", flush=True)
        snapshot_download(repo_id=repo)
    print("All required models are ready.")

if __name__ == "__main__": main()
