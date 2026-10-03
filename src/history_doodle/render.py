from __future__ import annotations

import json, shutil, subprocess
from pathlib import Path
from .schemas import ProjectPlan
from .util import run

FPS = 30
TRANSITION_SECONDS = 0.32

def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

def _motion_filter(motion: str, frames: int) -> str:
    # Keep motion deliberately restrained. Large zooms and lateral pans make
    # illustrated stills feel shaky, especially after upscaling to 1080p.
    if motion in ("slow_zoom_in", "subtle_push"):
        return f"zoompan=z='min(zoom+0.015/{frames},1.015)':d={frames}:s=1920x1080:fps={FPS}"
    if motion == "slow_zoom_out":
        return f"zoompan=z='if(eq(on,0),1.015,max(1.0,zoom-0.015/{frames}))':d={frames}:s=1920x1080:fps={FPS}"
    # Requested pans are intentionally converted to a locked frame. This is
    # safer for generated illustrations and prevents edge-to-edge judder.
    return f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps={FPS}"

def _xfade_graph(durations: list[float]) -> tuple[str, str]:
    """Build gentle dissolves while preserving the exact narration duration."""
    if len(durations) < 2:
        return "", "0:v"
    filters: list[str] = []
    previous = "0:v"
    elapsed = durations[0]
    for index in range(1, len(durations)):
        output = f"v{index}"
        filters.append(
            f"[{previous}][{index}:v]xfade=transition=fade:duration={TRANSITION_SECONDS}:offset={elapsed:.6f}[{output}]"
        )
        previous = output
        elapsed += durations[index]
    return ";".join(filters), previous

def render(project: Path, plan: ProjectPlan, narration: Path, ass: Path, music: Path | None = None, progress=lambda *_: None) -> tuple[Path, Path]:
    temp = project / "render/temp"; temp.mkdir(parents=True, exist_ok=True)
    ordered_shots = sorted(plan.shots, key=lambda s:s.order)
    clips = []
    durations = []
    for i, shot in enumerate(ordered_shots, 1):
        if shot.status != "complete" or not shot.image_path: raise RuntimeError(f"Shot {shot.id} is not ready")
        duration = shot.end_time - shot.start_time
        durations.append(duration)
        # Every clip except the last carries the dissolve tail. The overlap is
        # removed by xfade, so the final video still matches the narration.
        clip_duration = duration + (TRANSITION_SECONDS if i < len(ordered_shots) else 0)
        frames = max(1, round(clip_duration*FPS)); clip = temp / f"clip_smooth_v2_{i:04d}.mp4"
        if clip.exists():
            check = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(clip)],capture_output=True,text=True)
            if check.returncode == 0 and abs(float(check.stdout.strip()) - frames/30) < .12:
                clips.append(clip); progress(i,len(plan.shots)); continue
        run(["ffmpeg","-y","-loop","1","-i",str(project/shot.image_path),"-vf",_motion_filter(shot.camera_motion,frames),"-frames:v",str(frames),"-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",str(clip)])
        clips.append(clip); progress(i, len(plan.shots))
    silent = temp / "video.mp4"; no_sub = project / "render/final_video_no_subtitles.mp4"; final = project / "render/final_video.mp4"
    if len(clips) == 1:
        shutil.copy2(clips[0], silent)
    else:
        graph, output = _xfade_graph(durations)
        command = ["ffmpeg", "-y"]
        for clip in clips: command += ["-i", str(clip)]
        command += ["-filter_complex", graph, "-map", f"[{output}]", "-t", f"{sum(durations):.6f}", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(silent)]
        run(command)
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
