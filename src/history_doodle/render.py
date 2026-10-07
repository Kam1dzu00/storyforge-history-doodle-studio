from __future__ import annotations

import json, shutil, subprocess
from pathlib import Path
from .schemas import ProjectPlan
from .util import run

FPS = 30
TRANSITION_SECONDS = 0.16

def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

def _motion_filter(motion: str, frames: int, width: int = 1920, height: int = 1080) -> str:
    # Keep motion deliberately restrained. Large zooms and lateral pans make
    # illustrated stills feel shaky, especially after upscaling to 1080p.
    if motion in ("slow_zoom_in", "subtle_push"):
        return f"zoompan=z='min(zoom+0.015/{frames},1.015)':d={frames}:s={width}x{height}:fps={FPS}"
    if motion == "slow_zoom_out":
        return f"zoompan=z='if(eq(on,0),1.015,max(1.0,zoom-0.015/{frames}))':d={frames}:s={width}x{height}:fps={FPS}"
    # Requested pans are intentionally converted to a locked frame. This is
    # safer for generated illustrations and prevents edge-to-edge judder.
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={FPS}"

def _xfade_graph(durations: list[float]) -> tuple[str, str]:
    """Build mostly hard cuts with an occasional short dissolve."""
    if len(durations) < 2:
        return "", "0:v"
    filters: list[str] = []
    previous = "0:v"
    elapsed = durations[0]
    for index in range(1, len(durations)):
        output = f"v{index}"
        if index % 8 == 0:
            filters.append(f"[{previous}][{index}:v]xfade=transition=fade:duration={TRANSITION_SECONDS}:offset={elapsed:.6f}[{output}]")
        else:
            filters.append(f"[{previous}][{index}:v]concat=n=2:v=1:a=0[{output}]")
        previous = output
        elapsed += durations[index]
    return ";".join(filters), previous

def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())

def _concat_copy(files: list[Path], output: Path, list_file: Path) -> None:
    # All still-image clips share the same codec settings, so packet-level concat
    # is both fast and far more reliable than one 80+ input filter graph.
    list_file.write_text("".join(f"file '{x.resolve().as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for x in files), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)])

def _assemble_long_form(clips: list[Path], temp: Path, output: Path) -> None:
    """Assemble small hard-cut reels, then dissolve only between reels.

    This keeps roughly 87% hard cuts while avoiding FFmpeg's fragile filter graph
    with dozens of simultaneous 1080p decoders.
    """
    groups = [clips[i:i + 8] for i in range(0, len(clips), 8)]
    reels: list[Path] = []
    for index, group in enumerate(groups, 1):
        reel = temp / f"reel_{index:03d}.mp4"
        _concat_copy(group, reel, temp / f"reel_{index:03d}.txt")
        reels.append(reel)
    if len(reels) == 1:
        shutil.copy2(reels[0], output); return
    durations = [_probe_duration(x) for x in reels]
    command = ["ffmpeg", "-y"]
    for reel in reels: command += ["-i", str(reel)]
    filters=[]; previous="0:v"; elapsed=durations[0]-TRANSITION_SECONDS
    for index in range(1,len(reels)):
        label=f"r{index}"
        filters.append(f"[{previous}][{index}:v]xfade=transition=fade:duration={TRANSITION_SECONDS}:offset={elapsed:.6f}[{label}]")
        previous=label
        elapsed += durations[index]-TRANSITION_SECONDS
    command += ["-filter_complex", ";".join(filters), "-map", f"[{previous}]", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(output)]
    run(command)

def render(project: Path, plan: ProjectPlan, narration: Path, ass: Path, music: Path | None = None, progress=lambda *_: None, width: int = 1920, height: int = 1080) -> tuple[Path, Path]:
    temp = project / "render/temp"; temp.mkdir(parents=True, exist_ok=True)
    ordered_shots = sorted(plan.shots, key=lambda s:s.order)
    missing = [f"Shot {s.order}" for s in ordered_shots if s.status != "complete" or not s.image_path or not (project / (s.image_path or "")).exists()]
    if missing:
        raise RuntimeError(f"{len(missing)} shots missing: " + ", ".join(missing))
    clips = []
    durations = []
    for i, shot in enumerate(ordered_shots, 1):
        duration = shot.end_time - shot.start_time
        durations.append(duration)
        # Every clip except the last carries the dissolve tail. The overlap is
        # removed by xfade, so the final video still matches the narration.
        has_dissolve_after = i < len(ordered_shots) and i % 8 == 0
        clip_duration = duration + (TRANSITION_SECONDS if has_dissolve_after else 0)
        frames = max(1, round(clip_duration*FPS)); clip = temp / f"clip_production_v3_{i:04d}.mp4"
        source_image=project/shot.image_path
        if clip.exists() and clip.stat().st_mtime >= source_image.stat().st_mtime:
            check = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(clip)],capture_output=True,text=True)
            if check.returncode == 0 and abs(float(check.stdout.strip()) - frames/30) < .12:
                clips.append(clip); progress(i,len(plan.shots)); continue
        run(["ffmpeg","-y","-loop","1","-i",str(project/shot.image_path),"-vf",_motion_filter(shot.camera_motion,frames,width,height),"-frames:v",str(frames),"-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",str(clip)])
        clips.append(clip); progress(i, len(plan.shots))
    silent = temp / "video.mp4"; no_sub = project / "render/final_video_no_subtitles.mp4"; final = project / "render/final_video.mp4"
    if len(clips) == 1:
        shutil.copy2(clips[0], silent)
    else:
        _assemble_long_form(clips, temp, silent)
    if music and music.exists():
        audio_filter = "[1:a]loudnorm=I=-16:TP=-1:LRA=9[voice];[2:a]volume=0.10,aloop=loop=-1:size=2e+09[music];[music][voice]sidechaincompress=threshold=0.02:ratio=8[duck];[voice][duck]amix=inputs=2:duration=first:weights='1 0.35'[a]"
        run(["ffmpeg","-y","-i",str(silent),"-i",str(narration),"-stream_loop","-1","-i",str(music),"-filter_complex",audio_filter,"-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest",str(no_sub)])
    else:
        run(["ffmpeg","-y","-i",str(silent),"-i",str(narration),"-c:v","copy","-c:a","aac","-b:a","192k","-shortest",str(no_sub)])
    escaped = str(ass).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    run(["ffmpeg","-y","-i",str(no_sub),"-vf",f"ass='{escaped}'","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-c:a","copy",str(final)])
    return no_sub, final

def probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
