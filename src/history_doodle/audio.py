from __future__ import annotations

import json, re, shutil, subprocess, wave
from pathlib import Path
import numpy as np
import soundfile as sf
from .config import WHISPER_REPO
from .schemas import WordStamp
from .util import cleanup_models, run

def split_sentences(text: str, max_chars: int = 350) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text.strip())
    out, current = [], ""
    for p in pieces:
        if current and len(current) + len(p) + 1 > max_chars:
            out.append(current); current = p
        else: current = (current + " " + p).strip()
    if current: out.append(current)
    return out

class VoiceEngine:
    def generate(self, script: str, out_dir: Path, voice: str, progress=lambda *_: None) -> Path:
        from kokoro import KPipeline
        chunks = split_sentences(script); chunk_dir = out_dir / "chunks"; chunk_dir.mkdir(parents=True, exist_ok=True)
        pipeline = KPipeline(lang_code="a")
        cleaned = []
        try:
            for i, text in enumerate(chunks, 1):
                progress(i, len(chunks))
                audio_parts = [np.asarray(audio, dtype=np.float32) for _, _, audio in pipeline(text, voice=voice, speed=1.03)]
                if not audio_parts: raise RuntimeError(f"Kokoro produced no audio for chunk {i}")
                raw = chunk_dir / f"raw_{i:04d}.wav"; dest = chunk_dir / f"chunk_{i:04d}.wav"
                sf.write(raw, np.concatenate(audio_parts), 24000)
                trim = "silenceremove=start_periods=1:start_duration=0:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-48dB,areverse,loudnorm=I=-16:TP=-1:LRA=9"
                run(["ffmpeg", "-y", "-i", str(raw), "-af", trim, "-ar", "24000", str(dest)])
                raw.unlink(missing_ok=True); cleaned.append(dest)
        finally:
            del pipeline
            cleanup_models()
        concat = out_dir / "concat.txt"
        gap = out_dir / "gap.wav"
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.16", str(gap)])
        lines = []
        for i, p in enumerate(cleaned):
            lines.append(f"file '{p.resolve().as_posix()}'")
            if i + 1 < len(cleaned): lines.append(f"file '{gap.resolve().as_posix()}'")
        concat.write_text("\n".join(lines), encoding="utf-8")
        wav = out_dir / "narration.wav"
        master = "silenceremove=stop_periods=-1:stop_duration=0.48:stop_threshold=-45dB:stop_silence=0.30,loudnorm=I=-16:TP=-1:LRA=9"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-af", master, "-ar", "48000", "-ac", "1", str(wav)])
        run(["ffmpeg", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "192k", str(out_dir / "narration.m4a")])
        return wav

class TimestampEngine:
    def transcribe(self, audio_path: Path, output_path: Path) -> list[WordStamp]:
        import mlx_whisper
        try:
            result = mlx_whisper.transcribe(str(audio_path), path_or_hf_repo=WHISPER_REPO, word_timestamps=True, language="en", verbose=None)
            words = [WordStamp.model_validate(w) for s in result["segments"] for w in s.get("words", [])]
            output_path.write_text(json.dumps([w.model_dump() for w in words], indent=2), encoding="utf-8")
            return words
        finally: cleanup_models()

def audio_duration(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())
