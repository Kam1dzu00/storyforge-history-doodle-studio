from __future__ import annotations

import json
import subprocess
from pathlib import Path

from history_doodle.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "projects/shorts-batch-01-rebuild-v2"

EXPRESSIONS = {
    "s01": "0.020*sin(2*PI*48*t)+0.010*sin(2*PI*96*t)+0.012*(0.5+0.5*sin(2*PI*2*t))*sin(2*PI*1800*t)",
    "s02": "0.014*sin(2*PI*110*t)+0.010*sin(2*PI*165*t)+0.008*sin(2*PI*(330+8*sin(2*PI*0.17*t))*t)",
    "s03": "0.020*sin(2*PI*55*t)+0.009*sin(2*PI*220*t)+0.007*(0.5+0.5*sin(2*PI*1.6*t))*sin(2*PI*660*t)",
    "s04": "0.021*sin(2*PI*49*t)+0.011*sin(2*PI*73.5*t)+0.009*(0.5+0.5*sin(2*PI*2.4*t))*sin(2*PI*147*t)",
    "s05": "0.018*sin(2*PI*82*t)+0.010*sin(2*PI*164*t)+0.009*(0.5+0.5*sin(2*PI*3.2*t))*sin(2*PI*980*t)",
}


def main() -> None:
    store = ProjectStore()
    projects = [Path(x) for x in json.loads((BATCH / "projects.json").read_text(encoding="utf-8"))]
    for project in projects:
        code = project.name.split("-")[3]
        output = project / "audio/generated" / f"{code}_premium_bed.wav"
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            f"aevalsrc={EXPRESSIONS[code]}:s=48000:d=70",
            "-af", "highpass=f=35,lowpass=f=6500,aformat=sample_rates=48000:channel_layouts=stereo,afade=type=in:start_time=0:duration=0.25,afade=type=out:start_time=69:duration=1",
            "-c:a", "pcm_s24le", str(output),
        ], check=True)
        state = store.load_state(project)
        state.background_music = str(output.resolve())
        state.background_music_mode = "user_file"
        state.background_music_enabled = True
        state.background_music_gain_db = -1.5
        state.background_music_duck_db = 6.0
        store.save_state(project, state)
        (project / "logs/music_identity.json").write_text(json.dumps({"source":str(output.resolve()),"profile":code,"mandatory":True,"vocal":False}, indent=2), encoding="utf-8")


if __name__ == "__main__": main()
