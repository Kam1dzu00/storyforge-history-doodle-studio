from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared"
VOICE_DIR = SHARED / "voice_segments"
VOICE_DIR.mkdir(parents=True, exist_ok=True)

MODEL = Path("/Users/mihailfedrunov/.cache/hyperframes/tts/models/kokoro-v1.0.onnx")
VOICES = Path("/Users/mihailfedrunov/.cache/hyperframes/tts/voices/voices-v1.0.bin")
SYNTH = Path("/Users/mihailfedrunov/.cache/hyperframes/tts/synth-v2.py")

BEATS = [
    (0.0, 5.0, "A day in a World War One trench was hell."),
    (5.0, 10.0, "Men stood for hours in freezing water and thick mud."),
    (10.0, 15.0, "Rats scurried between your boots. Even sleep was a gamble."),
    (15.0, 22.0, "Meals arrived cold, stale, or covered in mud. Bon appétit."),
    (22.0, 30.0, "Then without warning, shells could turn everything upside down."),
    (30.0, 38.0, "A letter from home might be the best moment of the week."),
    (38.0, 48.0, "And sometimes the order came: climb out into no man's land."),
    (48.0, 60.0, "And some men lived like this for years. If they survived."),
]


def probe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "/Users/mihailfedrunov/.npm-global/bin/ffprobe", "-v", "error",
        "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path),
    ], text=True)
    return float(out.strip())


SPEEDS = [0.82, 0.82, 0.82, 0.76, 0.76, 0.76, 0.76, 0.76]
records = []
for idx, (start, end, text) in enumerate(BEATS, 1):
    speed = SPEEDS[idx - 1]
    output = VOICE_DIR / f"beat_{idx:02d}.wav"
    subprocess.run([
        "uv", "run", "--with", "kokoro-onnx", "--with", "soundfile",
        str(SYNTH), str(MODEL), str(VOICES), text, "am_michael", str(speed), str(output), "en-us",
    ], check=True)
    duration = probe_duration(output)
    slot = end - start
    if duration > slot - 0.2:
        raise RuntimeError(f"Beat {idx} is too long: {duration:.3f}s for {slot:.3f}s slot")
    records.append({
        "beat": idx, "start": start, "end": end, "slot_duration": slot,
        "speech_duration": round(duration, 6), "text": text, "file": str(output),
        "voice": "am_michael", "speed": speed, "lang": "en-us",
    })

(SHARED / "voice_manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
print(json.dumps(records, indent=2))
