from __future__ import annotations

import json, shutil, subprocess
from pathlib import Path
from .schemas import ProjectPlan
from .util import run

def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

def _motion_filter(motion: str, frames: int) -> str:
    if motion in ("slow_zoom_in", "subtle_push"):
        return f"zoompan=z='min(zoom+0.06/{frames},1.06)':d={frames}:s=1920x1080:fps=30"
    if motion == "slow_zoom_out":
        return f"zoompan=z='if(eq(on,0),1.06,max(1.0,zoom-0.06/{frames}))':d={frames}:s=1920x1080:fps=30"
    if motion == "pan_left":
        return f"scale=2016:1134,crop=1920:1080:x='96*(1-n/{frames})':y=27,fps=30"
    if motion == "pan_right":
        return f"scale=2016:1134,crop=1920:1080:x='96*n/{frames}':y=27,fps=30"
    return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30"

def render(project: Path, plan: ProjectPlan, narration: Path, ass: Path, music: Path | None = None, progress=lambda *_: None) -> tuple[Path, Path]:
    temp = project / "render/temp"; temp.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, shot in enumerate(sorted(plan.shots, key=lambda s:s.order), 1):
        if shot.status != "complete" or not shot.image_path: raise RuntimeError(f"Shot {shot.id} is not ready")
        duration = shot.end_time - shot.start_time; frames = max(1, round(duration*30)); clip = temp / f"clip_{i:04d}.mp4"
        if clip.exists():
            check = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(clip)],capture_output=True,text=True)
            if check.returncode == 0 and abs(float(check.stdout.strip()) - frames/30) < .12:
                clips.append(clip); progress(i,len(plan.shots)); continue
        run(["ffmpeg","-y","-loop","1","-i",str(project/shot.image_path),"-vf",_motion_filter(shot.camera_motion,frames),"-frames:v",str(frames),"-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",str(clip)])
        clips.append(clip); progress(i, len(plan.shots))
    concat = temp / "clips.txt"; concat.write_text("\n".join(f"file '{x.resolve().as_posix()}'" for x in clips), encoding="utf-8")
    silent = temp / "video.mp4"; no_sub = project / "render/final_video_no_subtitles.mp4"; final = project / "render/final_video.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
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
