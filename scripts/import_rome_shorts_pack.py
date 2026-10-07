from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from history_doodle.schemas import ProjectPlan, ProjectState, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / "Downloads"
PACK = [
    ("rome-short-01-night", "Why Ancient Rome Was Terrifying at Night", "S01_NIGHT", 51001),
    ("rome-short-02-apartments", "Ancient Rome's Apartments Were a Death Trap", "S02_APARTMENTS", 52001),
    ("rome-short-03-toilets", "Ancient Roman Toilets Were Worse Than You Think", "S03_TOILETS", 53001),
]

STYLE = (
    "VERTICAL 9:16 mobile-first adult editorial history cartoon, established StoryForge illustrated look, "
    "bold confident ink outlines, strong readable silhouettes, simplified grounded Roman forms, punchy warm "
    "terracotta and teal palette, crisp foreground-midground-background separation, premium magazine illustration, "
    "historically plausible first-century ancient Rome, dynamic vertical composition, subject fills the frame, "
    "clear at phone size, expressive but not childish, slightly meme-like visual timing, no baked text"
)
NEGATIVE = (
    "modern objects, electric lights, modern clothes, anime, children's book, glossy 3D, photorealism, neon, "
    "fake writing, labels, captions, logos, watermarks, clutter, tiny subject, empty dead space, extra limbs, "
    "missing limbs, fused bodies, malformed hands, duplicate people, graphic gore, explicit waste"
)


def field(block: str, name: str, default: str = "") -> str:
    match = re.search(rf"\[{name}:\s*(.*?)\]", block)
    return match.group(1).strip() if match else default


def paragraph(block: str, heading: str) -> str:
    match = re.search(rf"\[{heading}\]\s*\n(.*?)(?=\n\n\[|\Z)", block, re.S)
    return " ".join(match.group(1).strip().split()) if match else ""


def people_count(brief: str) -> int:
    text = brief.lower()
    if any(x in text for x in ("empty seats", "single object", "object demonstration", "water channel", "oil lamp", "spark near", "stone surface", "aqueduct, bathhouse", "split composition: seat row")):
        return 0
    if any(x in text for x in ("crowd", "pedestrians", "people", "multiple", "several")):
        return 4
    if any(x in text for x in ("resident", "traveler", "pedestrian", "citizen", "sleeper", "user", "someone")):
        return 1
    return 0


def visual_type(brief: str, purpose: str) -> str:
    text = (brief + " " + purpose).lower()
    if any(x in text for x in ("object", "lamp", "sponge", "spark", "channel")):
        return "OBJECT_HERO"
    if any(x in text for x in ("split", "triptych", "montage", "cutaway", "four-panel")):
        return "COMPARISON"
    if any(x in text for x in ("city", "street", "alley", "building", "skyline", "latrine", "apartment")):
        return "ENVIRONMENT"
    return "CHARACTER_MEDIUM" if people_count(brief) else "DETAIL"


def import_one(slug: str, title: str, code: str, base_seed: int) -> Path:
    master_src = SOURCE / f"StoryForge_Shorts_Rome_{code}_MASTER.md"
    narration_src = SOURCE / f"StoryForge_Shorts_Rome_{code}_NARRATION.txt"
    master = master_src.read_text(encoding="utf-8")
    narration = narration_src.read_text(encoding="utf-8").strip()
    blocks = re.findall(r"### SHOT\s+(\d+)\s*\n(.*?)(?=\n### SHOT|\n## Final assembly rules)", master, re.S)
    shot_lines = [paragraph(block, "NARRATION") for _, block in blocks]
    if " ".join("\n\n".join(shot_lines).split()) != " ".join(narration.split()):
        raise ValueError(f"Locked narration mismatch in {code}")

    project = ROOT / "projects" / slug
    if project.exists():
        raise FileExistsError(f"Project already exists: {project}")
    for rel in ("planning", "audio/chunks", "images", "subtitles", "render/temp", "logs"):
        (project / rel).mkdir(parents=True, exist_ok=True)
    state = ProjectState(
        project_id=slug,
        title=title,
        input_mode="script",
        target_duration_seconds=55,
        voice="am_michael",
        base_seed=base_seed,
        output_width=1080,
        output_height=1920,
        background_music_enabled=True,
        background_music_mode="procedural",
        background_music_gain_db=-2.0,
        background_music_duck_db=7.0,
        background_music_fade_in=0.4,
        background_music_fade_out=1.2,
        script_status="complete",
        planning_status="complete",
    )
    store = ProjectStore()
    store.save_state(project, state)
    (project / "script.txt").write_text(narration + "\n", encoding="utf-8")
    shutil.copy2(narration_src, project / "source_narration.txt")
    shutil.copy2(master_src, project / "master_production.md")
    shutil.copy2(SOURCE / "StoryForge_Shorts_Rome_CODEX_EXECUTION_PROMPT.md", project / "execution_prompt.md")
    shutil.copy2(SOURCE / "StoryForge_Shorts_Rome_PACK_README.md", project / "pack_readme.md")

    shots, scenes, segments = [], [], []
    motions = ["subtle_push", "slow_zoom_in", "static", "slow_zoom_out", "pan_left", "pan_right"]
    for index, (number, block) in enumerate(blocks, 1):
        narration_line = paragraph(block, "NARRATION")
        brief = paragraph(block, "VISUAL BRIEF")
        style_notes = paragraph(block, "STYLE NOTES")
        purpose = field(block, "VISUAL_PURPOSE", "literal narration beat")
        placement = field(block, "SUBJECT_PLACEMENT", "subject dominant")
        camera = field(block, "CAMERA", "dynamic vertical framing")
        composition = field(block, "COMPOSITION", "clear vertical composition")
        action = field(block, "ACTION", brief)
        speed = float(field(block, "VOICE_SPEED", "1.03"))
        duration = max(3.0, float(field(block, "DURATION_TARGET", "3.2s").rstrip("s")))
        count = people_count(brief)
        prompt = (
            f"{STYLE}. LITERAL VISUAL: {brief}. PURPOSE: {purpose}. ACTION: {action}. "
            f"COMPOSITION: {composition}; {placement}; camera {camera}. {style_notes}. "
            f"Show the specific narrated thing immediately and unmistakably. "
            f"{'NO PEOPLE; focus only on the named environment or object.' if count == 0 else f'Exactly {count} clearly separated adult Roman figure(s), natural anatomy, each with exactly two arms and two legs.'}"
        )
        sid = f"shot_{index:03d}"
        scene_id = f"scene_{index:03d}"
        shot = Shot(
            id=sid,
            scene_id=scene_id,
            order=index,
            narration_context=narration_line,
            visual_subject=brief,
            location="Ancient Rome, first century CE",
            action=action,
            composition=composition,
            prompt=prompt,
            negative_prompt=NEGATIVE + ", " + paragraph(block, "NEGATIVE"),
            seed=base_seed + index * 137,
            estimated_duration=duration,
            camera_motion=motions[(index - 1) % len(motions)],
            visual_type=visual_type(brief, purpose),
            people_count=count,
            visual_purpose=purpose,
            background_style="vertical StoryForge Roman editorial cartoon",
            time_of_day="night" if code == "S01_NIGHT" else "day",
            environment_context="historically grounded ancient Roman urban environment",
            action_description=action,
            continuity_key=code.lower(),
        )
        shots.append(shot)
        scenes.append(Scene(id=scene_id, section_id="section_001", order=index, narration_text=narration_line, shot_ids=[sid]))
        segments.append({"text": narration_line, "speed": speed, "pause_after_ms": 70 if index < len(blocks) else 0})
    plan = ProjectPlan(
        sections=[StorySection(id="section_001", title=title, purpose="fast vertical micro-story", scene_ids=[x.id for x in scenes])],
        scenes=scenes,
        shots=shots,
        characters=[],
    )
    store.save_plan(project, plan)
    (project / "voice_segments.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    return project


def main() -> None:
    for item in PACK:
        print(import_one(*item))


if __name__ == "__main__":
    main()
