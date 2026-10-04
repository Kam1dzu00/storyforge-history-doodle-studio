from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .schemas import ProjectState
from .util import run


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def generate_procedural_ambience(output: Path, duration: float, fade_in: float = 2.0, fade_out: float = 5.0) -> Path:
    """Create a restrained, seamless-feeling Cold War/ocean ambience in PCM."""
    output.parent.mkdir(parents=True, exist_ok=True)
    fade_start = max(0.0, duration - fade_out)
    expression = (
        "0.030*sin(2*PI*43*t)+0.018*sin(2*PI*67*t)+"
        "0.006*sin(2*PI*113*t)+0.004*random(0)"
    )
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc={expression}:s=48000:d={duration:.6f}",
        "-af", f"highpass=f=25,lowpass=f=1800,aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:st=0:d={fade_in:.3f},afade=t=out:st={fade_start:.6f}:d={fade_out:.3f}",
        "-c:a", "pcm_s24le", str(output),
    ])
    return output


def _stream_hash(path: Path) -> str:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "hash", "-hash", "sha256", "-"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip().split("=", 1)[-1]


def master_background_music(project: Path, state: ProjectState) -> tuple[Path, Path, Path]:
    """Preserve the completed render, master audio, then remux with video stream copy."""
    render_dir = project / "render"
    final = render_dir / "final_video.mp4"
    no_music = render_dir / "final_video_no_music.mp4"
    if not final.exists() and not no_music.exists():
        raise FileNotFoundError("Completed final_video.mp4 is required before audio mastering")
    if not no_music.exists():
        shutil.copy2(final, no_music)

    duration = probe_duration(no_music)
    generated = project / "audio/generated/azorian_cold_war_ambient.wav"
    if state.background_music_mode == "user_file" and state.background_music:
        music = Path(state.background_music).expanduser()
        if not music.exists():
            raise FileNotFoundError(f"Background music file not found: {music}")
    else:
        music = generate_procedural_ambience(generated, duration, state.background_music_fade_in, state.background_music_fade_out)

    narration = project / "audio/narration.wav"
    if not narration.exists():
        raise FileNotFoundError("Original narration WAV is required for lossless final mastering")
    mix = project / "audio/final_mix.wav"
    fade_start = max(0.0, duration - state.background_music_fade_out)
    gain = state.background_music_gain_db
    graph = (
        f"[0:a]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={duration:.6f},asplit=2[voice_mix][voice_sc];"
        f"[1:a]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,"
        f"aloop=loop=-1:size=2147483647,atrim=duration={duration:.6f},"
        f"loudnorm=I=-26:TP=-6:LRA=5,volume={gain}dB,"
        f"afade=t=in:st=0:d={state.background_music_fade_in:.3f},"
        f"afade=t=out:st={fade_start:.6f}:d={state.background_music_fade_out:.3f}[bed];"
        "[bed][voice_sc]sidechaincompress=threshold=0.018:ratio=6:attack=150:release=900[ducked];"
        "[voice_mix][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.891[a]"
    )
    run([
        "ffmpeg", "-y", "-i", str(narration), "-stream_loop", "-1", "-i", str(music),
        "-filter_complex", graph, "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(mix),
    ])

    temporary = render_dir / "final_video.music.tmp.mp4"
    try:
        run([
            "ffmpeg", "-y", "-i", str(no_music), "-i", str(mix), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
            "-t", f"{duration:.6f}", "-movflags", "+faststart", str(temporary),
        ])
        if _stream_hash(no_music) != _stream_hash(temporary):
            raise RuntimeError("Video stream hash changed during audio mastering")
        temporary.replace(final)
    finally:
        temporary.unlink(missing_ok=True)

    report = {
        "mode": state.background_music_mode,
        "music_source": str(music),
        "duration": duration,
        "music_target_lufs": -26,
        "duck_db": state.background_music_duck_db,
        "duck_attack_ms": 150,
        "duck_release_ms": 900,
        "fade_in_seconds": state.background_music_fade_in,
        "fade_out_seconds": state.background_music_fade_out,
        "video_stream_copy_verified": True,
    }
    (project / "logs/audio_mastering.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return no_music, final, music
