from __future__ import annotations

import json, logging, re, shutil, subprocess, wave
from pathlib import Path
import numpy as np
import soundfile as sf
from .config import WHISPER_REPO
from .schemas import WordStamp
from .util import cleanup_models, run
from .timing import validate_word_timestamps

log = logging.getLogger(__name__)

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
    def generate(self, script: str, out_dir: Path, voice: str, progress=lambda *_: None, speed: float = 1.03) -> Path:
        from kokoro import KPipeline
        chunks = split_sentences(script); chunk_dir = out_dir / "chunks"; chunk_dir.mkdir(parents=True, exist_ok=True)
        pipeline = KPipeline(lang_code="a")
        cleaned = []
        try:
            for i, text in enumerate(chunks, 1):
                progress(i, len(chunks))
                audio_parts = [np.asarray(audio, dtype=np.float32) for _, _, audio in pipeline(text, voice=voice, speed=speed)]
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

    def preview(self, text: str, output: Path, voice: str, speed: float = 1.03) -> Path:
        from kokoro import KPipeline
        output.parent.mkdir(parents=True,exist_ok=True); pipeline=KPipeline(lang_code="a")
        try:
            parts=[np.asarray(audio,dtype=np.float32) for _,_,audio in pipeline(text,voice=voice,speed=speed)]
            if not parts: raise RuntimeError("Kokoro produced no preview audio")
            sf.write(output,np.concatenate(parts),24000)
        finally:
            del pipeline; cleanup_models()
        return output

    def generate_segments(self, segments: list[dict], out_dir: Path, voice: str, progress=lambda *_: None) -> Path:
        """Generate narration with per-segment Kokoro speed and explicit pauses.

        This is opt-in so existing projects keep their established audio path.
        Each production segment may be split for TTS stability, but its speed is
        preserved and PAUSE_AFTER is inserted only after the complete segment.
        """
        from kokoro import KPipeline
        chunk_dir = out_dir / "chunks"; chunk_dir.mkdir(parents=True, exist_ok=True)
        pipeline = KPipeline(lang_code="a")
        cleaned: list[tuple[Path, int, int]] = []
        total = sum(len(split_sentences(str(x["text"]))) for x in segments)
        current = 0
        try:
            for segment_index, segment in enumerate(segments, 1):
                parts = split_sentences(str(segment["text"]))
                speed = float(segment["speed"])
                pause_ms = int(segment["pause_after_ms"])
                silence_ms = int(segment.get("silence_ms", 0))
                if not 0.5 <= speed <= 1.5 or not 0 <= pause_ms <= 5000:
                    raise ValueError(f"Invalid voice metadata in segment {segment_index}")
                if not parts:
                    if not 1 <= silence_ms <= 10000:
                        raise ValueError(f"Silent segment {segment_index} requires silence_ms")
                    dest = chunk_dir / f"segment_{segment_index:04d}_silence.wav"
                    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{silence_ms / 1000:.3f}", str(dest)])
                    # The silent clip already is the requested pause. Applying
                    # pause_after_ms as well would double explicit black/outro
                    # holds (for example, 1000 ms becomes 2000 ms).
                    cleaned.append((dest, 0, segment_index))
                    continue
                for part_index, text in enumerate(parts, 1):
                    current += 1; progress(current, total)
                    audio_parts = [np.asarray(audio, dtype=np.float32) for _, _, audio in pipeline(text, voice=voice, speed=speed)]
                    if not audio_parts: raise RuntimeError(f"Kokoro produced no audio for segment {segment_index}")
                    stem = f"segment_{segment_index:04d}_{part_index:02d}"
                    raw = chunk_dir / f"raw_{stem}.wav"; dest = chunk_dir / f"{stem}.wav"
                    sf.write(raw, np.concatenate(audio_parts), 24000)
                    trim = "silenceremove=start_periods=1:start_duration=0:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-48dB,areverse,loudnorm=I=-16:TP=-1:LRA=9"
                    run(["ffmpeg", "-y", "-i", str(raw), "-af", trim, "-ar", "24000", str(dest)])
                    raw.unlink(missing_ok=True)
                    cleaned.append((dest, pause_ms if part_index == len(parts) else 120, segment_index))
        finally:
            del pipeline
            cleanup_models()

        gap_paths: dict[int, Path] = {}
        for pause_ms in sorted({pause for _, pause, _ in cleaned[:-1] if pause > 0}):
            gap = out_dir / f"gap_{pause_ms:04d}ms.wav"
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{pause_ms / 1000:.3f}", str(gap)])
            gap_paths[pause_ms] = gap
        concat = out_dir / "concat.txt"; lines = []
        timeline, cursor = [], 0.0
        for index, (path, pause_ms, segment_index) in enumerate(cleaned):
            lines.append(f"file '{path.resolve().as_posix()}'")
            duration = sf.info(path).duration
            if not timeline or timeline[-1]["segment"] != segment_index:
                timeline.append({"segment": segment_index, "start": cursor, "end": cursor + duration})
            else:
                timeline[-1]["end"] = cursor + duration
            cursor += duration
            if index + 1 < len(cleaned) and pause_ms > 0:
                lines.append(f"file '{gap_paths[pause_ms].resolve().as_posix()}'")
                cursor += pause_ms / 1000
                timeline[-1]["end"] = cursor
        concat.write_text("\n".join(lines), encoding="utf-8")
        (out_dir / "voice_timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
        wav = out_dir / "narration.wav"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-af", "loudnorm=I=-16:TP=-1:LRA=9", "-ar", "48000", "-ac", "1", str(wav)])
        run(["ffmpeg", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "192k", str(out_dir / "narration.m4a")])
        return wav

class TimestampEngine:
    def transcribe(self, audio_path: Path, output_path: Path) -> list[WordStamp]:
        import mlx_whisper
        try:
            result = mlx_whisper.transcribe(str(audio_path), path_or_hf_repo=WHISPER_REPO, word_timestamps=True, language="en", verbose=None)
            words = [WordStamp.model_validate(w) for s in result["segments"] for w in s.get("words", [])]
            for warning in validate_word_timestamps(words, audio_duration(audio_path)): log.warning(warning)
            output_path.write_text(json.dumps([w.model_dump() for w in words], indent=2), encoding="utf-8")
            return words
        finally: cleanup_models()

def audio_duration(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

def quality_report(path: Path) -> dict:
    duration = audio_duration(path)
    loud = subprocess.run(["ffmpeg","-hide_banner","-i",str(path),"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True)
    silence = subprocess.run(["ffmpeg","-hide_banner","-i",str(path),"-af","silencedetect=noise=-45dB:d=0.7","-f","null","-"],capture_output=True,text=True)
    gaps = [float(x) for x in re.findall(r"silence_duration: ([0-9.]+)", silence.stderr)]
    integrated = re.findall(r"I:\s*(-?[0-9.]+) LUFS", loud.stderr)
    peak = re.findall(r"Peak:\s*(-?[0-9.]+) dBFS", loud.stderr)
    return {"duration":duration,"integrated_lufs":float(integrated[-1]) if integrated else None,"peak_dbfs":float(peak[-1]) if peak else None,"silences_over_700ms":gaps,"potential_errors_over_1200ms":[x for x in gaps if x>1.2]}
