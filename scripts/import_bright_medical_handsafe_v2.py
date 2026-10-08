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
PROJECT = PROJECTS_DIR / "youve-been-lied-to-about-getting-sick-handsafe-v2"
MASTER = SOURCE / "02_MASTER_PRODUCTION-2.md"
NARRATION = SOURCE / "03_NARRATION_ONLY.txt"
EXECUTION = SOURCE / "01_CODEX_EXECUTION_PROMPT-3.md"
DELETE_INSTRUCTION = SOURCE / "05_DELETE_AND_REBUILD_INSTRUCTION.md"
PACK = SOURCE / "StoryForge_BRIGHT_MEDICAL_EPISODE_PACK_V2_HANDSAFE.zip"


def field(block: str, name: str) -> str:
    match = re.search(rf"- (?:\*\*)?{re.escape(name)}:(?:\*\*)?[ \t]*(.*)", block)
    return match.group(1).strip() if match else ""


def category(visual: str) -> str:
    text = visual.lower()
    if any(x in text for x in ("split", "side-by-side", "3-panel", "scale")):
        return "comparison_split"
    if any(x in text for x in ("diagram", "flow", "tree", "ladder", "chart", "infographic", "strip", "sequence", "icons")):
        return "process_sequence"
    if any(x in text for x in ("silhouette", "face", "reaction", "person")):
        return "character_reaction"
    if any(x in text for x in ("bacteria", "virus", "germ", "mucus", "sinus", "immune")):
        return "medical_diagram"
    if any(x in text for x in ("pill", "bottle", "orange", "tissue", "thermometer", "coat", "toolbox")):
        return "object_single"
    return "symbol_metaphor"


def visual_type(cat: str) -> str:
    return {
        "comparison_split": "COMPARISON",
        "process_sequence": "INFO_CARD",
        "character_reaction": "CHARACTER_CLOSEUP",
        "medical_diagram": "DETAIL",
        "object_single": "OBJECT_HERO",
    }.get(cat, "DETAIL")


def safe_visual(visual: str) -> str:
    """Translate layout words that commonly trigger fake writing into visual-only staging."""
    replacements = {
        "card": "full-frame composition",
        "board": "clean arrangement",
        "checklist": "three large unlabeled symbols",
        "decision tree": "branching path of unlabeled symbols",
        "signpost": "two contrasting unlabeled symbols",
        "label": "symbol",
        "licensed physician": "medical authority",
        "badge": "red rejection symbol",
        "timeline": "left-to-right visual progression",
    }
    result = visual
    for old, new in replacements.items():
        result = re.sub(old, new, result, flags=re.I)
    return result


def main() -> None:
    if PROJECT.exists():
        raise FileExistsError(PROJECT)
    for required in (MASTER, NARRATION, EXECUTION, DELETE_INSTRUCTION, PACK):
        if not required.exists():
            raise FileNotFoundError(required)

    master = MASTER.read_text(encoding="utf-8")
    narration = NARRATION.read_text(encoding="utf-8").strip()
    blocks = re.findall(r"### SHOT\s+(\d+)\s*\n(.*?)(?=\n### SHOT|\n## FINAL QA)", master, re.S)
    if len(blocks) != 39:
        raise ValueError(f"Expected 39 shots, got {len(blocks)}")
    spoken = [field(block, "Narration") for _, block in blocks if field(block, "Narration")]
    if " ".join("\n\n".join(spoken).split()) != " ".join(narration.split()):
        raise ValueError("Locked narration mismatch")

    for rel in ("planning", "audio/chunks", "images", "subtitles", "render/temp", "logs", "sources"):
        (PROJECT / rel).mkdir(parents=True, exist_ok=True)
    for source, target in (
        (MASTER, "master_production.md"),
        (NARRATION, "source_narration.txt"),
        (EXECUTION, "execution_prompt.md"),
        (DELETE_INSTRUCTION, "delete_and_rebuild_instruction.md"),
    ):
        shutil.copy2(source, PROJECT / "sources" / target)
    shutil.copy2(PACK, PROJECT / "sources" / PACK.name)
    (PROJECT / "script.txt").write_text(narration + "\n", encoding="utf-8")

    state = ProjectState(
        project_id=PROJECT.name,
        title="You've Been Lied To About Getting Sick — HANDSAFE V2",
        input_mode="script",
        target_duration_seconds=600,
        voice="am_eric",
        base_seed=920000,
        style_mode="bright_explainer",
        host_enabled=False,
        semantic_visual_routing=True,
        full_bleed_frames=True,
        voice_preset="energetic_explainer",
        speech_speed=0.96,
        music_profile="BRIGHT_FACTS",
        background_music_enabled=True,
        background_music_mode="procedural",
        background_music_gain_db=-1.0,
        background_music_duck_db=6.0,
        background_music_fade_in=1.2,
        background_music_fade_out=3.0,
        outro_enabled=True,
        outro_image_path="images/shot_039.png",
        pause_before_outro_ms=2000,
        outro_speed=0.93,
        script_status="complete",
        planning_status="complete",
    )
    composer = PromptComposer()
    shots: list[Shot] = []
    scenes: list[Scene] = []
    segments: list[dict[str, object]] = []
    overlays = {
        1: ["BIG MYTHS ABOUT SICKNESS"],
        4: ["WHAT REALLY MAKES YOU SICK?"],
        9: ["MYTH #2"],
        39: ["SUBSCRIBE FOR MORE FACTS & HIDDEN STORIES"],
    }
    motions = ["subtle_push", "static", "slow_zoom_in", "static", "slow_zoom_out", "static"]

    for index, (_, block) in enumerate(blocks, 1):
        text = field(block, "Narration")
        raw_visual = field(block, "Visual")
        visual = safe_visual(raw_visual)
        speed = float(field(block, "Speed") or 1.0)
        pause = float((field(block, "Pause after") or "0s").rstrip("s"))
        cat = category(raw_visual)
        sid = f"shot_{index:03d}"
        scene_id = f"scene_{index:03d}"
        # V2 deliberately renders faces and body silhouettes as graphic icons;
        # no photoreal human is required, which keeps every generated frame hand-safe.
        people_count = 0
        shot = Shot(
            id=sid,
            scene_id=scene_id,
            order=index,
            narration_context=text,
            visual_subject=visual,
            location="bright modern medical explainer environment",
            action=visual,
            composition="one bold full-screen 16:9 visual beat, large clear objects, strong depth, uncluttered silhouette",
            prompt="",
            negative_prompt="",
            seed=state.base_seed + index * 3253,
            estimated_duration=min(10, max(3, float((field(block, "Duration") or "8s").rstrip("s")))),
            camera_motion=motions[(index - 1) % len(motions)],
            visual_type=visual_type(cat),
            people_count=people_count,
            labels=overlays.get(index, []),
            visual_purpose="literal hand-safe medical myth explanation",
            subject_placement="OFF_CENTER",
            camera_angle="EYE_LEVEL",
            framing="CLOSEUP" if cat in {"object_single", "character_reaction"} else "MEDIUM_WIDE",
            foreground_elements=["one large relevant object or clean motion accent"],
            midground_elements=[visual],
            background_elements=["simple supporting medical or domestic context with depth"],
            environment_context="bright contemporary world, never ancient Rome; visual symbols only",
            action_description=visual,
            negative_space_direction="safe upper area for deterministic subtitle overlay",
            continuity_key="bright_medical_handsafe_v2",
            visual_category=cat,
            visual_focus=visual,
            host_present=False,
            routing_source="manual",
        )
        shot.prompt, shot.negative_prompt, _ = composer.compose(state, shot)
        shot.prompt += (
            " HAND-SAFE OBJECT-FIRST RULE: prefer objects, icons, diagrams, and environments. "
            "If a human is unavoidable, show face and shoulders only with both hands fully outside the frame. "
            "No lettering, words, numbers, signage, captions, logos, UI, labels, or pseudo-text inside the generated art."
        )
        shot.negative_prompt += ", hands, fingers, visible arms, extra limbs, malformed anatomy, writing, typography, pseudo-text"
        shots.append(shot)
        scenes.append(Scene(id=scene_id, section_id="section_001", order=index, narration_text=text, shot_ids=[sid]))
        segment: dict[str, object] = {"text": text, "speed": speed, "pause_after_ms": round(pause * 1000)}
        if index == 38:
            segment["silence_ms"] = 2000
        segments.append(segment)

    black = PROJECT / "images/shot_038.png"
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(black)
    outro_src = ROOT / "assets/channel/channel_outro_static.png"
    if not outro_src.exists():
        raise FileNotFoundError(outro_src)
    outro = PROJECT / "images/shot_039.png"
    shutil.copy2(outro_src, outro)
    for index, path in ((38, black), (39, outro)):
        shot = shots[index - 1]
        shot.image_path = str(path.relative_to(PROJECT))
        shot.status = "complete"
        shot.approved = True
        shot.prompt_hash = prompt_hash(shot.prompt, shot.negative_prompt)

    plan = ProjectPlan(
        sections=[StorySection(id="section_001", title=state.title, purpose="object-first medical myth-busting episode", scene_ids=[x.id for x in scenes])],
        scenes=scenes,
        shots=shots,
    )
    store = ProjectStore()
    store.save_state(PROJECT, state)
    store.save_plan(PROJECT, plan)
    (PROJECT / "voice_segments.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    print(PROJECT)


if __name__ == "__main__":
    main()
