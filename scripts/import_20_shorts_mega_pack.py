from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from history_doodle.config import PROJECTS_DIR
from history_doodle.schemas import ProjectPlan, ProjectState, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore
from history_doodle.style_system import PromptComposer


ROOT = Path(__file__).resolve().parents[1]
BATCH = PROJECTS_DIR / "shorts-mega-pack-v1-batch"
PACK = BATCH / "sources/StoryForge_20_SHORTS_MEGA_PACK_V1"
VOICE = "am_eric"
CTA = "Like, subscribe, and watch more strange facts and stories on the channel."
CTA_TEXT = "LIKE • SUBSCRIBE • MORE FACTS & STORIES"

FAMILIES = {
    "S01": "shorts_dark_neon", "S02": "shorts_dark_neon", "S08": "shorts_dark_neon",
    "S09": "shorts_spy", "S10": "shorts_spy",
    "S11": "shorts_historical", "S12": "shorts_historical",
    "S13": "shorts_technical", "S16": "shorts_technical", "S18": "shorts_technical",
    "S19": "shorts_technical", "S20": "shorts_technical",
}

STYLE_DIRECTIONS = {
    "NEON_SLEEP_GLITCH": "dark sleepless-neuroscience comic, midnight navy, electric cyan and magenta, selective dream distortion",
    "PSYCHEDELIC_MEMORY_COLLAGE": "surreal adult memory collage, layered fragments, violet teal coral, warped transitions but one clear focus",
    "ARCADE_MEDICAL": "adult arcade-medical metaphor, cyan navy red, bold game-like impact shapes without UI or writing",
    "COMIC_COURTROOM": "bright comic courtroom metaphor using virus, winter evidence, gavel and scales as objects, no people",
    "GROSS_POP_ART": "clean gross-out pop art, vivid green cyan coral, funny but medically readable",
    "THERMAL_BODY_MAP": "thermal medical map, blue-to-red heat gradients, clean immune diagrams",
    "COSMIC_COLOR_EXPLAINER": "cosmic color explainer, deep blue atmosphere, radiant spectral light and elegant particles",
    "ELECTRIC_GRAPHIC_NOVEL": "electric science graphic novel, black storm sky, white-blue lightning and orange heat",
    "SPY_PULP_1960S": "1960s spy pulp, deep navy, olive, cream and red, analog surveillance props",
    "DEEP_SEA_COLD_WAR": "deep-sea Cold War engineering, abyssal navy, steel, red accents, gigantic industrial scale",
    "GROSS_HISTORY_BRIGHT": "warm bright Roman historical cartoon, terracotta stone aqua channels, object-first sanitation comedy",
    "MEDIEVAL_CHAOS_COMIC": "medieval urban chaos comic, timber brown, fire orange, smoky blue, dense period environment",
    "RETRO_AVIATION_POSTER": "1950s retro aviation engineering poster, cream teal red, elegant aircraft cutaways",
    "KINETIC_POP_SCIENCE": "kinetic pop science, fizzy cyan red yellow, explosive bubbles and diagonal motion",
    "MINIMAL_WINTER_MACRO": "minimal winter macro, black-blue air, white vapor particles, icy cyan rim light",
    "BIO_MECHANICAL_CROSS_SECTION": "biomechanical stomach cross-section, coral tissue, acid yellow, cyan protective barrier",
    "KITCHEN_CHEMISTRY_COMIC": "kitchen chemistry comic, onion purple, sulfur yellow, clean microscopic transitions",
    "KINETIC_ANIMAL_PHYSICS": "kinetic animal physics, anatomically correct cat silhouette, clean rotation arcs, blue orange palette",
    "MATERIAL_SCIENCE_SPLIT": "material science split, brushed steel blue versus warm wood amber, visible heat-flow particles",
    "MICRO_FOOD_SCIENCE": "microscopic food science, golden kernel cutaway, steam blue, dramatic structural rupture",
}


def slugify(value: str) -> str:
    value = value.lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def section(text: str, name: str, next_name: str) -> str:
    match = re.search(rf"## {re.escape(name)}\n(.*?)(?=\n## {re.escape(next_name)}|\Z)", text, re.S)
    if not match: raise ValueError(f"Missing section {name}")
    return match.group(1).strip()


def metadata(text: str, name: str) -> str:
    match = re.search(rf"- \*\*{re.escape(name)}:\*\*\s*(.*)", text)
    if not match: raise ValueError(f"Missing metadata {name}")
    return match.group(1).strip().strip("`")


def split_narration(main: str, count: int = 7) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(main.split()))
    if len(sentences) >= count:
        base,extra=divmod(len(sentences),count); groups=[]; cursor=0
        for i in range(count):
            size=base+(1 if i<extra else 0); groups.append(" ".join(sentences[cursor:cursor+size])); cursor+=size
        return groups
    words=main.split(); base,extra=divmod(len(words),count); groups=[]; cursor=0
    for i in range(count):
        size=base+(1 if i<extra else 0); groups.append(" ".join(words[cursor:cursor+size])); cursor+=size
    return groups


def safe_visual(value: str) -> str:
    value=re.sub(r"\bhand\b", "flat mitten-shaped hand icon with no fingers", value, flags=re.I)
    value=re.sub(r"\bpeople\b", "simple separated faceless silhouette icons", value, flags=re.I)
    value=re.sub(r"\bperson\b", "single shoulders-up faceless silhouette with hands off-frame", value, flags=re.I)
    return value


def visual_category(visual: str) -> str:
    text=visual.lower()
    if any(x in text for x in ("cross-section","diagram","cutaway","flow","gauge","map","particles","arrows")): return "process_sequence"
    if any(x in text for x in (" vs ","split","comparison","beside")): return "comparison_split"
    if any(x in text for x in ("city","street","room","ocean","sky","latrine","building")): return "environment_wide"
    return "object_single"


def import_short(path: Path, manifest_row: dict, order: int) -> Path:
    code=manifest_row["id"]; text=path.read_text(encoding="utf-8")
    title=metadata(text,"Title"); cover=metadata(text,"Cover text"); direction=metadata(text,"Visual direction")
    narration=section(text,"Narration","Shot plan"); paragraphs=[x.strip() for x in narration.split("\n\n") if x.strip()]
    if paragraphs[-1] != CTA: raise ValueError(f"CTA mismatch in {code}")
    main=" ".join(paragraphs[:-1]); chunks=split_narration(main); complete_narration=main+"\n\n"+CTA
    shot_plan=section(text,"Shot plan","Mandatory final CTA")
    lines=re.findall(r"^\d+\.\s+(?:[^:]+:\s*)?(.*)$",shot_plan,re.M)
    if len(lines)!=8: raise ValueError(f"Expected 8 shots in {code}, got {len(lines)}")
    slug=f"shorts-v1-{code.lower()}-{slugify(title)}"; project=PROJECTS_DIR/slug
    if project.exists(): raise FileExistsError(project)
    for rel in ("planning","audio/chunks","images","subtitles","render/temp","logs","sources"):(project/rel).mkdir(parents=True,exist_ok=True)
    for src in (PACK/"00_README_FIRST.md",PACK/"01_CODEX_BATCH_EXECUTION_PROMPT.md",PACK/"02_GLOBAL_STYLE_BIBLE.md",PACK/"03_QA_ANATOMY_TEXT.md",PACK/"05_FACT_GUARDRAILS.md",PACK/"06_BATCH_MANIFEST.json",path):
        shutil.copy2(src,project/"sources"/src.name)
    (project/"script.txt").write_text(complete_narration+"\n",encoding="utf-8")
    family=FAMILIES.get(code,"shorts_bright_pop"); historical=family in {"shorts_historical","shorts_spy"}
    state=ProjectState(project_id=slug,title=title,input_mode="script",target_duration_seconds=55,voice=VOICE,base_seed=2_000_000+order*100_000,output_width=1080,output_height=1920,style_mode=family,host_enabled=False,semantic_visual_routing=True,full_bleed_frames=True,voice_preset="energetic_explainer",speech_speed=1.03,music_profile="HISTORICAL_AMBIENCE" if historical else "BRIGHT_FACTS",background_music_enabled=True,background_music_mode="procedural",background_music_gain_db=-1.5 if historical else 0.5,background_music_duck_db=7.0,background_music_fade_in=.35,background_music_fade_out=1.0,script_status="complete",planning_status="complete")
    composer=PromptComposer(); shots=[]; scenes=[]; segments=[]
    narration_chunks=chunks+[CTA]; motions=["subtle_push","static","slow_zoom_in","static","slow_zoom_out","subtle_push","static","slow_zoom_in"]
    for i,(visual,narr) in enumerate(zip(lines,narration_chunks),1):
        focus=(f"calm style-matched closing background with a play-button symbol, bell symbol, and starburst, no text, no people" if i==8 else safe_visual(visual))
        if "cat" in focus.lower(): focus += "; exactly one anatomically correct cat with four legs, one head, one tail, no duplicated limbs"
        category=visual_category(focus); sid=f"shot_{i:03d}"; scene_id=f"scene_{i:03d}"
        shot=Shot(id=sid,scene_id=scene_id,order=i,narration_context=narr,visual_subject=focus,location="style-specific illustrated world",action=focus,composition="full-screen vertical 9:16, one dominant subject, clear in under one second",prompt="",negative_prompt="",seed=state.base_seed+i*3253,estimated_duration=6.0,camera_motion=motions[i-1],visual_type="OBJECT_HERO" if category=="object_single" else "DETAIL",people_count=0,labels=[CTA_TEXT] if i==8 else ([cover] if i==1 else []),visual_purpose="literal mobile-first narrated beat",subject_placement="OFF_CENTER",camera_angle="EYE_LEVEL",framing="CLOSEUP" if i in (1,7,8) else "MEDIUM_WIDE",foreground_elements=["one large literal subject"],midground_elements=[focus],background_elements=["simple style-matched environment with no writing"],environment_context=STYLE_DIRECTIONS[direction]+", full-screen vertical world",action_description=focus,negative_space_direction="center-safe subtitle area",continuity_key=code.lower(),visual_category=category,visual_focus=f"{STYLE_DIRECTIONS[direction]}; {focus}",host_present=False,routing_source="manual")
        shot.prompt,shot.negative_prompt,_=composer.compose(state,shot)
        shots.append(shot); scenes.append(Scene(id=scene_id,section_id="section_001",order=i,narration_text=narr,shot_ids=[sid]))
        segments.append({"text":narr,"speed":1.06 if i==8 else 1.03,"pause_after_ms":0 if i==8 else (350 if i==7 else 170)})
    plan=ProjectPlan(sections=[StorySection(id="section_001",title=title,purpose=f"vertical short {direction}",scene_ids=[x.id for x in scenes])],scenes=scenes,shots=shots)
    store=ProjectStore(); store.save_state(project,state); store.save_plan(project,plan)
    (project/"voice_segments.json").write_text(json.dumps(segments,ensure_ascii=False,indent=2),encoding="utf-8")
    (project/"logs/production_identity.json").write_text(json.dumps({"id":code,"title":title,"visual_direction":direction,"style_family":family,"selected_voice":VOICE,"posting_order":order},indent=2),encoding="utf-8")
    return project


def main() -> None:
    manifest=json.loads((PACK/"06_BATCH_MANIFEST.json").read_text(encoding="utf-8")); by_id={x["id"]:x for x in manifest["shorts"]}
    order=["S01","S09","S13","S11","S02","S08","S03","S20","S10","S14","S12","S07","S05","S18","S19","S04","S17","S06","S15","S16"]
    files={x.name[:3]:x for x in (PACK/"shorts").glob("S*.md")}
    created=[import_short(files[code],by_id[code],i) for i,code in enumerate(order,1)]
    (BATCH/"logs/selected_voice.json").write_text(json.dumps({"candidates":["am_eric","am_liam","am_puck"],"sample_files":[f"voice_samples/{x}.wav" for x in ("am_eric","am_liam","am_puck")],"selected_voice":VOICE,"reason":"most consistent intelligent lively conversational tone in local Kokoro production tests"},indent=2),encoding="utf-8")
    (BATCH/"projects.json").write_text(json.dumps([str(x) for x in created],indent=2),encoding="utf-8")
    print("\n".join(str(x) for x in created))


if __name__=="__main__": main()
