from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from history_doodle.config import PROJECTS_DIR
from history_doodle.schemas import ProjectPlan, ProjectState, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
BATCH = PROJECTS_DIR / "shorts-batch-01-rebuild-v2"
PACK = BATCH / "sources/StoryForge_SHORTS_BATCH_01_REBUILD_V2"
VOICE = "am_michael"
SPEED = 1.03
CTA = "Like, subscribe, and watch more strange facts and stories on the channel."
CTA_TEXT = "LIKE • SUBSCRIBE\nMORE FACTS & STORIES"

FILES = [
    "S01_72_HOURS_WITHOUT_SLEEP.md",
    "S02_MEMORY_REWRITES_THE_PAST.md",
    "S03_CIA_SPY_CAT.md",
    "S04_MEDIEVAL_DEATH_TRAP.md",
    "S05_ANTIBIOTICS_VS_VIRUSES.md",
]

STYLE = {
    "S01": "premium adult dark-neon medical editorial illustration, midnight navy, electric cyan and warning red, realistic object design, cinematic rim light, rich ink texture, dramatic depth",
    "S02": "premium adult surreal editorial collage, warm cream, cobalt and crimson, sophisticated torn-photo layers, magazine illustration, cinematic shadows",
    "S03": "premium adult 1960s spy-pulp comic, dark teal black cream and signal red, restrained halftone texture, realistic normal cat, serious declassified atmosphere",
    "S04": "premium adult gritty historical comic, ochre dirty cream dark brown and plague green, detailed medieval street texture, smoke and deep perspective, never cute fantasy",
    "S05": "premium adult medical graphic novel, cream clinical field, navy vivid red and acid green, crisp macro biology, professional editorial diagrams, no baby-faced germs",
}

MUSIC_PROFILE = {"S01":"BRIGHT_FACTS","S02":"BRIGHT_FACTS","S03":"HISTORICAL_AMBIENCE","S04":"HISTORICAL_AMBIENCE","S05":"BRIGHT_FACTS"}


def block(text: str, heading: str, next_heading: str) -> str:
    m = re.search(rf"## {re.escape(heading)}\n(.*?)(?=\n## {re.escape(next_heading)}|\Z)", text, re.S)
    if not m: raise ValueError(f"missing {heading}")
    return m.group(1).strip()


def field(text: str, heading: str) -> str:
    value = block(text, heading, "__missing__") if False else None
    m = re.search(rf"## {re.escape(heading)}\n\*\*(.*?)\*\*", text)
    if not m: raise ValueError(f"missing field {heading}")
    return m.group(1).strip()


def clean_spoken(value: str) -> str:
    value = re.sub(r"\*\*\[(?:HOOK|CTA)\]\*\*\s*", "", value)
    value = value.replace("**", "")
    return re.sub(r"\s+", " ", value).strip()


def split_spoken(value: str, count: int) -> list[str]:
    # Balanced word groups preserve every punctuation token exactly, which is
    # required by the locked-narration guard in Pipeline.generate_voice.
    words = value.split(); base, extra = divmod(len(words), count); out=[]; cursor=0
    for index in range(count):
        size = base + (1 if index < extra else 0)
        out.append(" ".join(words[cursor:cursor+size])); cursor += size
    return out


def shot_lines(text: str) -> list[str]:
    body = block(text, "Shot plan — 14 beats", "Hook performance") if "Shot plan — 14 beats" in text and "Hook performance" in text else None
    if body is None:
        m = re.search(r"## Shot plan — (\d+) beats\n(.*?)(?=\n## |\Z)", text, re.S)
        if not m: raise ValueError("shot plan missing")
        body = m.group(2)
    lines = re.findall(r"^\d+\.\s+(?:\*\*[^*]+:\*\*\s*)?(.*)$", body, re.M)
    return [x.strip() for x in lines]


def prompt(code: str, visual: str) -> str:
    subject = re.sub(r"[“”\"'].*?[“”\"']", "", visual)
    return f"""FULL-SCREEN VERTICAL 9:16 CINEMATIC KEYFRAME.
{STYLE[code]}.
EXACT STORY BEAT: {subject}
One immediately readable focal action, strong foreground/midground/background separation, deliberate camera angle, rich controlled detail, adult editorial animation quality.
No childlike clip-art, no worksheet, no poster, no collage panels unless the beat explicitly requires editorial collage.
ZERO generated writing: no letters, words, numbers, labels, captions, logos, watermarks, interfaces, signs, pseudo-text, or gibberish.
Avoid people and hands unless explicitly essential. If a person appears: exactly one person, exactly two arms total, natural anatomy, hands fully out of frame. No extra limbs or duplicate body parts.
No unrelated cat, dog, mascot, Roman imagery, or generic filler."""


def import_one(source: Path, order: int) -> Path:
    text = source.read_text(encoding="utf-8"); code = source.name[:3]
    title = field(text, "Upload title"); cover = field(text, "Cover text")
    narration_raw = block(text, "Narration", "Shot plan —") if False else re.search(r"## Narration\n(.*?)(?=\n## Shot plan)", text, re.S).group(1)
    narration = clean_spoken(narration_raw)
    if not narration.endswith(CTA): raise ValueError(f"CTA mismatch {code}")
    main = narration[:-len(CTA)].strip(); visuals = shot_lines(text)
    if len(visuals) not in (14, 15): raise ValueError(f"{code}: {len(visuals)} shots")
    spoken = split_spoken(main, len(visuals)-1) + [CTA]
    slug = f"shorts-rebuild-v2-{code.lower()}-{re.sub(r'[^a-z0-9]+','-',title.lower()).strip('-')}"
    project = PROJECTS_DIR / slug
    if project.exists(): raise FileExistsError(project)
    for rel in ("planning","audio/chunks","audio/generated","images","subtitles","render/temp","logs","sources"):
        (project/rel).mkdir(parents=True,exist_ok=True)
    for src in PACK.glob("*.md"): shutil.copy2(src, project/"sources"/src.name)
    shutil.copy2(source, project/"sources"/source.name)
    (project/"script.txt").write_text(narration+"\n",encoding="utf-8")
    state = ProjectState(project_id=slug,title=title,input_mode="script",target_duration_seconds=55,voice=VOICE,base_seed=3_100_000+order*100_000,output_width=1080,output_height=1920,style_mode=f"premium_rebuild_v2_{code.lower()}",host_enabled=False,semantic_visual_routing=True,full_bleed_frames=True,voice_preset="calm_history",speech_speed=SPEED,music_profile=MUSIC_PROFILE[code],background_music_enabled=True,background_music_mode="procedural",background_music_gain_db=-1.0,background_music_duck_db=6.0,background_music_fade_in=.25,background_music_fade_out=.8,script_status="complete",planning_status="complete")
    shots=[]; scenes=[]; segments=[]
    motions=["subtle_push","static","slow_zoom_in","static","slow_zoom_out"]
    for i,(visual,narr) in enumerate(zip(visuals,spoken),1):
        sid=f"shot_{i:03d}"; scene_id=f"scene_{i:03d}"; is_cta=i==len(visuals)
        p=prompt(code,visual)
        shot=Shot(id=sid,scene_id=scene_id,order=i,narration_context=narr,visual_subject=visual,location="full-screen story world",action=visual,composition="full-screen vertical 9:16 cinematic frame",prompt=p,negative_prompt="text, letters, numbers, labels, captions, logos, watermark, pseudo-text, gibberish, childlike clip-art, flat worksheet, empty background, extra limbs, extra arms, extra hands, malformed fingers, fused body parts, unrelated animals, generic filler",seed=state.base_seed+i*4051,estimated_duration=3.5,camera_motion=motions[(i-1)%len(motions)],visual_type="OBJECT_HERO",people_count=0,labels=[CTA_TEXT] if is_cta else ([cover] if i==1 else []),visual_purpose="literal premium mobile-first story beat",subject_placement="OFF_CENTER",camera_angle="SLIGHT_LOW" if i==1 else "EYE_LEVEL",framing="CLOSEUP" if i in (1,len(visuals)-1,len(visuals)) else "MEDIUM_WIDE",foreground_elements=["strong foreground anchor"],midground_elements=[visual],background_elements=["substyle-specific environment with depth and no writing"],environment_context=STYLE[code],action_description=visual,negative_space_direction="lower-third subtitle safe area",continuity_key=code.lower(),visual_category="environment_wide" if any(w in visual.lower() for w in ("street","office","highway","city","room")) else "object_single",visual_focus=visual,host_present=False,routing_source="manual",director_override=True,validation_checks={"premium_v2":True,"anatomy_hard_reject":True,"text_hard_reject":True})
        shots.append(shot); scenes.append(Scene(id=scene_id,section_id="section_001",order=i,narration_text=narr,shot_ids=[sid]))
        segments.append({"text":narr,"speed":SPEED,"pause_after_ms":0 if is_cta else (260 if i in (1,len(visuals)-1) else 100)})
    plan=ProjectPlan(sections=[StorySection(id="section_001",title=title,purpose=f"premium vertical short {code}",scene_ids=[s.id for s in scenes])],scenes=scenes,shots=shots)
    store=ProjectStore(); store.save_state(project,state); store.save_plan(project,plan)
    (project/"voice_segments.json").write_text(json.dumps(segments,indent=2),encoding="utf-8")
    identity={"id":code,"title":title,"selected_voice":VOICE,"voice_backend":"kokoro.KPipeline","lang_code":"a","baseline_speed":SPEED,"normalization":"per-segment loudnorm I=-16 TP=-1 LRA=9; final 48k mono loudnorm","frame_count":len(shots),"source":str(source)}
    (project/"logs/production_identity.json").write_text(json.dumps(identity,indent=2),encoding="utf-8")
    return project


def main() -> None:
    created=[import_one(PACK/"shorts"/name,i) for i,name in enumerate(FILES,1)]
    (BATCH/"projects.json").write_text(json.dumps([str(p) for p in created],indent=2),encoding="utf-8")
    recovered={"source_project":str(PROJECTS_DIR/"could-you-survive-ancient-rome"),"voice_backend":"Kokoro KPipeline","lang_code":"a","voice_id":VOICE,"baseline_speed":SPEED,"chunk_trim":"-48 dB leading/trailing","per_chunk_normalization":"I=-16 LUFS, TP=-1 dB, LRA=9","final_output":"48 kHz mono WAV; AAC 192 kbps derivative"}
    (BATCH/"logs/recovered_original_voice.json").write_text(json.dumps(recovered,indent=2),encoding="utf-8")
    print("\n".join(str(p) for p in created))


if __name__ == "__main__": main()
