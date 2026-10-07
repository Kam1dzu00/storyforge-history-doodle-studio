from __future__ import annotations

from pathlib import Path
from .schemas import WordStamp

def chunks(words: list[WordStamp], max_words: int = 5, max_chars: int = 34) -> list[list[WordStamp]]:
    result, current = [], []
    for word in words:
        projected = " ".join(x.word.strip() for x in current + [word])
        if current and (len(current) >= max_words or len(projected) > max_chars or word.start - current[-1].end > .35):
            result.append(current); current = []
        current.append(word)
        if len(current) >= 2 and word.word.rstrip().endswith((".", "!", "?", ",", ";", ":")):
            result.append(current); current = []
    if current: result.append(current)
    return result

def stamp(seconds: float, ass=False) -> str:
    ms = round(seconds * 1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h}:{m:02d}:{s:02d}.{ms//10:02d}" if ass else f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def build(words: list[WordStamp], out_dir: Path, width: int = 1920, height: int = 1080) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    vertical = height > width
    groups = chunks(words, max_words=4 if vertical else 5, max_chars=22 if vertical else 34)
    srt = out_dir / "subtitles.srt"; ass = out_dir / "subtitles.ass"
    srt_lines = []
    for i, group in enumerate(groups, 1):
        srt_lines += [str(i), f"{stamp(group[0].start)} --> {stamp(group[-1].end)}", " ".join(w.word.strip() for w in group), ""]
    srt.write_text("\n".join(srt_lines), encoding="utf-8")
    font_size = 82 if vertical else 68
    margin_v = 300 if vertical else 118
    margin_h = 72 if vertical else 130
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Doodle,Avenir Next,{font_size},&H00FFFFFF,&H0028B4D8,&H00181818,&H70000000,-1,0,0,0,100,100,0,0,1,7,2,2,{margin_h},{margin_h},{margin_v},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for group in groups:
        karaoke = "".join(f"{{\\kf{max(1,round((w.end-w.start)*100))}}}{w.word.strip()} " for w in group).strip()
        effect = "{\\fscx95\\fscy95\\t(0,80,\\fscx103\\fscy103)\\t(80,160,\\fscx100\\fscy100)}"
        lines.append(f"Dialogue: 0,{stamp(group[0].start,True)},{stamp(group[-1].end,True)},Doodle,,0,0,0,,{effect}{karaoke}\n")
    ass.write_text("".join(lines), encoding="utf-8"); return srt, ass
