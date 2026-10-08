from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from PIL import Image

from history_doodle.config import PROJECTS_DIR, ROOT
from history_doodle.schemas import ProjectPlan, ProjectState, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore
from history_doodle.style_system import PromptComposer
from history_doodle.util import prompt_hash


SOURCE = Path.home() / "Downloads"
PROJECT = PROJECTS_DIR / "youve-been-lied-to-about-getting-sick"
MASTER = SOURCE / "02_MASTER_PRODUCTION.md"
NARRATION = SOURCE / "03_NARRATION_ONLY.txt"
EXECUTION = SOURCE / "01_CODEX_EXECUTION_PROMPT-2.md"
SOURCE_GUIDE = SOURCE / "04_SOURCE_GUIDE.md"


def field(block: str, name: str) -> str:
    match = re.search(rf"- \*\*{re.escape(name)}:\*\*[ \t]*(.*)", block)
    return match.group(1).strip() if match else ""


def category(visual: str) -> str:
    text = visual.lower()
    if any(x in text for x in ("split", "side-by-side", "three-panel", "scale balancing", "contrast")): return "comparison_split"
    if any(x in text for x in ("diagram", "decision tree", "checklist", "recap board", "escalation scale", "timeline", "icon set", "infographic")): return "process_sequence"
    if any(x in text for x in ("person", "character", "mom", "uncle", "body silhouette", "sick person")): return "character_reaction"
    if any(x in text for x in ("bacteria", "virus", "germ", "mucus", "face diagram", "immune")): return "medical_diagram"
    if any(x in text for x in ("pill", "bottle", "orange", "tissue", "thermometer")): return "object_single"
    if any(x in text for x in ("card", "montage", "sequence")): return "object_collection"
    return "symbol_metaphor"


def people(visual: str) -> int:
    text=visual.lower()
    if any(x in text for x in ("person", "character", "mom", "uncle", "baby icon", "adult icon", "body silhouette")): return 1
    return 0


def visual_type(cat: str) -> str:
    return {"comparison_split":"COMPARISON","process_sequence":"INFO_CARD","character_reaction":"CHARACTER_MEDIUM","medical_diagram":"DETAIL","object_single":"OBJECT_HERO","object_collection":"OBJECT_COLLECTION"}.get(cat,"DETAIL")


def main() -> None:
    if PROJECT.exists(): raise FileExistsError(PROJECT)
    master=MASTER.read_text(encoding="utf-8"); narration=NARRATION.read_text(encoding="utf-8").strip()
    blocks=re.findall(r"### SHOT\s+(\d+)\s*\n(.*?)(?=\n### SHOT|\n## POST-PRODUCTION)",master,re.S)
    if len(blocks)!=39: raise ValueError(f"Expected 39 shots, got {len(blocks)}")
    spoken=[field(block,"Narration") for _,block in blocks if field(block,"Narration")]
    if " ".join("\n\n".join(spoken).split()) != " ".join(narration.split()): raise ValueError("Locked narration mismatch")
    for rel in ("planning","audio/chunks","images","subtitles","render/temp","logs","sources"):(PROJECT/rel).mkdir(parents=True,exist_ok=True)
    for source,target in ((MASTER,"master_production.md"),(NARRATION,"source_narration.txt"),(EXECUTION,"execution_prompt.md"),(SOURCE_GUIDE,"source_guide.md")):
        shutil.copy2(source,PROJECT/"sources"/target)
    (PROJECT/"script.txt").write_text(narration+"\n",encoding="utf-8")
    state=ProjectState(project_id=PROJECT.name,title="You've Been Lied To About Getting Sick",input_mode="script",target_duration_seconds=600,voice="am_eric",base_seed=730000,style_mode="bright_explainer",host_enabled=False,semantic_visual_routing=True,full_bleed_frames=True,voice_preset="energetic_explainer",speech_speed=1.02,music_profile="BRIGHT_FACTS",background_music_enabled=True,background_music_mode="procedural",background_music_gain_db=-1.0,background_music_duck_db=6.0,background_music_fade_in=1.2,background_music_fade_out=3.0,outro_enabled=True,outro_image_path="images/shot_039.png",pause_before_outro_ms=2000,outro_speed=.95,script_status="complete",planning_status="complete")
    composer=PromptComposer(); shots=[]; scenes=[]; segments=[]
    overlays={1:["BIG MYTHS ABOUT SICKNESS"],4:["WHAT REALLY MAKES YOU SICK?"],9:["MYTH #2"],39:["SUBSCRIBE FOR MORE FACTS & HIDDEN STORIES"]}
    motions=["subtle_push","static","slow_zoom_in","static","slow_zoom_out","static"]
    for index,(number,block) in enumerate(blocks,1):
        text=field(block,"Narration"); visual=field(block,"Visual"); speed=float(field(block,"Speed") or 1.0); pause=float((field(block,"Pause after") or "0s").rstrip("s")); cat=category(visual); count=people(visual)
        sid=f"shot_{index:03d}"; scene_id=f"scene_{index:03d}"
        shot=Shot(id=sid,scene_id=scene_id,order=index,narration_context=text,visual_subject=visual,location="modern bright medical explainer world",action=visual,composition="one bold cinematic full-screen visual beat with strong depth and clear silhouette",prompt="",negative_prompt="",seed=state.base_seed+index*1543,estimated_duration=min(10,max(3,float((field(block,"Duration") or "8s").rstrip("s")))),camera_motion=motions[(index-1)%len(motions)],visual_type=visual_type(cat),people_count=count,labels=overlays.get(index,[]),visual_purpose="literal medical myth explanation",subject_placement="OFF_CENTER",camera_angle=("SLIGHT_LOW" if index%3==0 else "SLIGHT_HIGH" if index%3==1 else "EYE_LEVEL"),framing="CLOSEUP" if cat=="object_single" else "MEDIUM_WIDE",foreground_elements=["large relevant prop or controlled motion accent"],midground_elements=[visual],background_elements=["supporting medical or domestic context with depth"],environment_context="complete bright modern environment, never ancient Rome",action_description=visual,negative_space_direction="safe upper area for deterministic overlay",continuity_key="bright_medical_episode_01",visual_category=cat,visual_focus=visual,host_present=False,routing_source="manual")
        shot.prompt,shot.negative_prompt,_=composer.compose(state,shot)
        shots.append(shot); scenes.append(Scene(id=scene_id,section_id="section_001",order=index,narration_text=text,shot_ids=[sid]))
        segments.append({"text":text,"speed":speed,"pause_after_ms":round(pause*1000),**({"silence_ms":2000} if index==38 else {})})
    black=PROJECT/"images/shot_038.png"; Image.new("RGB",(1920,1080),(2,4,8)).save(black)
    outro_src=ROOT/"assets/channel/channel_outro_static.png"; outro=PROJECT/"images/shot_039.png"; shutil.copy2(outro_src,outro)
    for index,path in ((38,black),(39,outro)):
        shot=shots[index-1]; shot.image_path=str(path.relative_to(PROJECT)); shot.status="complete"; shot.approved=True; shot.prompt_hash=prompt_hash(shot.prompt,shot.negative_prompt)
    plan=ProjectPlan(sections=[StorySection(id="section_001",title=state.title,purpose="medical myth-busting long-form episode",scene_ids=[x.id for x in scenes])],scenes=scenes,shots=shots)
    store=ProjectStore(); store.save_state(PROJECT,state); store.save_plan(PROJECT,plan)
    (PROJECT/"voice_segments.json").write_text(json.dumps(segments,ensure_ascii=False,indent=2),encoding="utf-8")
    print(PROJECT)


if __name__ == "__main__": main()
