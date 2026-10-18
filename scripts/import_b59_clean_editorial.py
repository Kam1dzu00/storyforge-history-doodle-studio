from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from history_doodle.config import ROOT
from history_doodle.planner import parse_question_beats
from history_doodle.schemas import ProjectPlan, ProjectState, QuestionBeat, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore
from history_doodle.util import prompt_hash, shot_seed


PACK = ROOT / "projects/full-length-b59-clean-editorial-v1/sources/StoryForge_FULL_LENGTH_B59_CLEAN_EDITORIAL_V1"
FULL = ROOT / "projects/the-soviet-submarine-that-almost-started-world-war-iii-clean-editorial"
PREVIEW = ROOT / "projects/b59-clean-editorial-technical-preview"
QUESTION_RE = re.compile(r"\[QUESTION_BEAT\]\s*(.*?)\s*\[/QUESTION_BEAT\]", re.I | re.S)

QUESTION_BACKGROUNDS = {
    "How did a submarine nobody could see become one of the most dangerous places on Earth?": "tiny coherent Foxtrot-class B-59 silhouette deep in a dark ocean, two tiny surface ships far above, very low contrast",
    "Why would Moscow send submarines carrying nuclear weapons into a blockade the Americans were determined to enforce?": "minimal unlabeled North Atlantic map, one muted route from the Soviet north toward Cuba",
    "What did the men inside B-59 think was happening above them?": "dim control-room gauge silhouette with faint destroyer shadow and soft pressure rings far above",
    "If you believed the war had already started, what would a nuclear torpedo look like: escalation... or self-defense?": "single restrained nuclear torpedo outline with one faint circular pressure wave on near-black navy",
    "So who actually stopped the launch?": "three anonymous officer silhouettes and three tiny indicator lights, no faces, no controls with writing",
    "How close did the world really come to nuclear war?": "minimal globe silhouette with two muted signal-red zones, no mushroom cloud",
}


def pieces(text: str, target: int = 14) -> list[str]:
    """Split prose into coherent, exact contiguous voice/shot beats."""
    protected = QUESTION_RE.sub(lambda m: f"\n\n__QUESTION__{m.group(1).strip()}__ENDQUESTION__\n\n", text)
    paragraphs = [x.strip() for x in re.split(r"\n\s*\n", protected) if x.strip()]
    result: list[str] = []
    for paragraph in paragraphs:
        if paragraph.startswith("__QUESTION__"):
            result.append(paragraph.removeprefix("__QUESTION__").removesuffix("__ENDQUESTION__").strip())
            continue
        sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", paragraph) if x.strip()]
        for sentence in sentences:
            words = sentence.split()
            if len(words) <= target + 7:
                result.append(sentence); continue
            # Keep em/en dashes verbatim: they are spoken punctuation in the locked
            # source and must not disappear when prose is split into voice beats.
            clauses = [x.strip() for x in re.split(r"(?<=[,;:])\s+", sentence) if x.strip()]
            current = ""
            for clause in clauses:
                if current and len((current + " " + clause).split()) > target + 6:
                    result.append(current); current = clause
                else:
                    current = (current + " " + clause).strip()
            if current: result.append(current)
    return result


def visual_for(text: str, index: int, question: bool) -> tuple[str, str, str, str]:
    low = text.lower()
    if question:
        return "SILHOUETTE", "question_beat", QUESTION_BACKGROUNDS[text], "static"
    choices = [
        (("map", "cuba", "washington", "moscow", "atlantic", "turkey"), "MAP", "map_support"),
        (("torpedo", "weapon", "nuclear"), "OBJECT_HERO", "object_single"),
        (("radio", "battery", "gauge", "water", "air", "equipment", "signal"), "DETAIL", "object_single"),
        (("u-2", "aircraft", "pilot"), "OBJECT_HERO", "object_single"),
        (("destroyer", "ship", "navy", "fleet", "quarantine", "blockade"), "ENVIRONMENT", "environment_wide"),
        (("arkhipov", "savitsky", "kennedy", "khrushchev", "officer", "commander", "men", "crew"), "SILHOUETTE", "character_silhouette"),
        (("submarine", "b-59", "boat", "underwater", "ocean", "surface"), "ENVIRONMENT", "environment_wide"),
    ]
    for words, visual_type, category in choices:
        if any(word in low for word in words):
            break
    else:
        visual_type, category = ("DETAIL", "symbol_metaphor") if index % 3 else ("ENVIRONMENT", "environment_wide")
    focus = re.sub(r"[\"“”]", "", text).strip()
    focus = re.sub(r"\b(?:said|called|word|question|think|imagine)\b.*", "", focus, flags=re.I).strip(" ,.;:")
    focus = focus[:180] or "one restrained historically grounded Cold War visual metaphor"
    motion = "static" if visual_type in {"MAP", "DETAIL"} else ("slow_zoom_in" if index % 2 else "subtle_push")
    return visual_type, category, focus, motion


def mode_for(text: str, index: int, total: int, question: bool) -> tuple[str, float, int]:
    low = text.lower()
    if question: return "QUESTION", .86, 750
    if index <= 10: return "HOOK", 1.02, 220
    if index >= total - 8: return "REVEAL", .91, 520
    if any(x in low for x in ("nuclear", "explosion", "danger", "war", "shot down", "attack", "launch")):
        return "TENSION", .92, 380
    if any(x in low for x in ("reality", "answer", "what actually", "important", "matters", "in other words")):
        return "REVEAL", .91, 480
    return "STORY", .97, 280


def build_project(path: Path, title: str, source_text: str, selected: list[str], preview: bool) -> None:
    if path.exists():
        raise FileExistsError(path)
    for rel in ("planning", "audio/chunks", "audio/generated", "images", "subtitles", "render/temp", "logs", "sources"):
        (path / rel).mkdir(parents=True, exist_ok=True)
    shutil.copytree(PACK, path / "sources" / PACK.name, dirs_exist_ok=True)
    state = ProjectState(
        project_id=path.name, title=title, input_mode="script", target_duration_seconds=55 if preview else 1200,
        style_mode="clean_editorial", voice="am_michael", speech_speed=1.03,
        output_width=1920, output_height=1080, host_enabled=False, full_bleed_frames=True,
        music_profile="COLD_WAR_UNDERWATER_EDITORIAL", background_music_enabled=True,
        background_music_mode="procedural", background_music_duck_db=6.0,
        background_music_question_duck_db=8.0, background_music_fade_in=.8 if preview else 1.5,
        background_music_fade_out=2.0 if preview else 5.0,
        script_status="complete", planning_status="complete", voice_status="pending",
        images_status="pending", subtitles_status="pending", render_status="pending",
    )
    ProjectStore().save_state(path, state)
    (path / "script.txt").write_text(source_text.strip() + "\n", encoding="utf-8")
    question_texts = set(QUESTION_RE.findall(source_text))
    shots=[]; scenes=[]; voice=[]
    for index, text in enumerate(selected, 1):
        question=text in question_texts
        visual_type, category, focus, motion=visual_for(text,index,question)
        sid=f"scene_{index:03d}"; shot_id=f"shot_{index:03d}"
        beat=QuestionBeat(question_text=text,background_visual=QUESTION_BACKGROUNDS[text]) if question else None
        prompt=("FULL-SCREEN 16:9 CLEAN EDITORIAL DOCUMENTARY KEYFRAME. Mature hand-drawn editorial illustration, clean dark-ink linework with varied weight, soft cel shading, subtle paper-gouache texture, restrained warm cream muted navy dusty blue charcoal palette with one signal-red or pale-cyan accent. One dominant focal point, adult proportions, historically readable October 1962 Cold War setting, generous negative space, calm long-form visual comfort. "
                f"EXACT VISUAL IDEA: {beat.background_visual if beat else focus}. "
                "No typography inside the image, no labels, no letters, no numbers, no logos, no pseudo-text, no watermark, no split screen, no collage, no childish clip-art, no glossy 3D, no photorealism. "
                "Keep people as cropped adult silhouettes or profiles with hands out of frame; one coherent Foxtrot-class B-59 hull language throughout.")
        negative="text, letters, numbers, labels, logo, watermark, pseudo-text, gibberish, childlike clip-art, glossy 3D, photorealism, anime, comic overload, extra limbs, extra hands, malformed fingers, duplicated faces, crowded scene, unclear focal point, random modern submarine"
        shot=Shot(id=shot_id,scene_id=sid,order=index,narration_context=text,visual_subject=focus,location="October 1962 Atlantic / B-59 story world",action=focus,historical_props=["Foxtrot-class Soviet submarine continuity", "1962 Soviet and U.S. Cold War material culture"],character_ids=[],composition="single dominant off-center focal point with restrained depth and negative space",camera_motion=motion,prompt=prompt,negative_prompt=negative,seed=shot_seed(590000 if preview else 591000,index),estimated_duration=6 if question else 5,visual_type=visual_type,people_count=0,labels=[text] if question else [],director_override=True,visual_purpose="QUESTION_BEAT retention reset" if question else "support the exact narration beat",visual_category=category,visual_focus=beat.background_visual if beat else focus,routing_source="manual",question_beat=beat)
        shot.prompt_hash=prompt_hash(prompt,negative)
        shots.append(shot)
        scenes.append(Scene(id=sid,section_id="section_001",order=index,narration_text=text,shot_ids=[shot_id]))
        mode,speed,pause=mode_for(text,index,len(selected),question)
        voice.append({"text":text,"mode":mode,"speed":speed,"pause_before_ms":beat.pause_before_ms if beat else 0,"pause_after_ms":beat.pause_after_ms if beat else pause,"question_beat":question})
    plan=ProjectPlan(sections=[StorySection(id="section_001",title="Technical preview" if preview else "Complete episode",purpose="Locked B-59 clean editorial production",scene_ids=[x.id for x in scenes])],scenes=scenes,shots=shots)
    ProjectStore().save_plan(path,plan)
    (path/"voice_segments.json").write_text(json.dumps(voice,ensure_ascii=False,indent=2),encoding="utf-8")
    (path/"logs/production_identity.json").write_text(json.dumps({
        "selected_voice":"am_michael","voice_backend":"kokoro.KPipeline","lang_code":"a","earliest_approved_project":"projects/long-form-ten-minute-production-dry-run","earliest_approved_created_at":"2026-10-03T06:08:14.854865+00:00","baseline_speed":1.03,"style_id":"clean_editorial","question_beats":sum(bool(x.question_beat) for x in shots),"asset_count":len(shots),"preview":preview
    },indent=2),encoding="utf-8")


def main() -> None:
    narration=(PACK/"10_NARRATION_ONLY.txt").read_text(encoding="utf-8").strip()
    full_pieces=pieces(narration)
    first_question=QUESTION_RE.findall(narration)[0].strip()
    qpos=next(i for i,x in enumerate(full_pieces) if x==first_question)
    # A technical preview is a curated sample, not the complete cold open.
    # Keep exact supplied lines while staying inside the required 45–60 seconds.
    preview_pieces=full_pieces[:14]+[first_question]
    preview_script="\n\n".join(preview_pieces[:-1])+f"\n\n[QUESTION_BEAT]\n{first_question}\n[/QUESTION_BEAT]"
    if not PREVIEW.exists(): build_project(PREVIEW,"B-59 Clean Editorial Technical Preview",preview_script,preview_pieces,True)
    if not FULL.exists(): build_project(FULL,"The Soviet Submarine That Almost Started World War III",narration,full_pieces,False)
    print(json.dumps({"preview":str(PREVIEW),"preview_shots":len(preview_pieces),"full":str(FULL),"full_shots":len(full_pieces)},indent=2))


if __name__ == "__main__":
    main()
