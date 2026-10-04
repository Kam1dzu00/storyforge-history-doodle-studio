#!/usr/bin/env python3
"""Build the seven-shot acceptance project for the composition engine patch."""
from pathlib import Path

from history_doodle.config import DEFAULT_VOICE, NEGATIVE_PROMPT, STYLE_PROMPT
from history_doodle.pipeline import Pipeline
from history_doodle.planner import apply_composition_engine, apply_visual_grammar, finalize_plan_prompts
from history_doodle.schemas import CharacterCard, ProjectPlan, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore


LINES = [
    "A Viking wakes before sunrise inside a smoky timber longhouse.",
    "The hearth in the middle of the room provides heat, light and a place to cook.",
    "Outside, chickens and goats are already waiting to be fed.",
    "His tools are simple: an axe, a sickle and a knife.",
    "Later, he repairs a broken section of fence.",
    "Near the coast, a wooden boat needs maintenance too.",
    "By evening, the farm becomes quiet and the family returns to the warmth of the house.",
]


def main() -> None:
    script = "\n\n".join(LINES)
    store = ProjectStore()
    project = store.create("Composition Engine Acceptance Test", "script", 30, DEFAULT_VOICE, script)
    character = CharacterCard(
        id="main_viking",
        name="Viking farmer",
        role="recurring adult protagonist",
        visual_identity="the same adult Viking-age farmer with natural adult proportions, weathered oval face, tied brown hair, short brown beard, muted wool tunic, dark trousers and leather boots",
        fixed_traits=["same adult face", "same tied brown hair", "same short beard", "same muted wool clothing", "natural adult proportions"],
    )
    shots = []
    for index, line in enumerate(LINES, 1):
        shots.append(Shot(
            id=f"shot_{index:03d}", scene_id="scene_001", order=index,
            narration_context=line, visual_subject=line,
            location="Viking-age Scandinavian farmstead and coast",
            action="show the exact concrete narration beat",
            historical_props=["Viking-age timber construction", "wool, leather, iron and rough wood only", "no modern objects"],
            character_ids=[character.id], composition="single coherent historical scene",
            prompt="", negative_prompt="", seed=0, estimated_duration=4,
        ))
    plan = ProjectPlan(
        sections=[StorySection(id="section_001", title="Daily work", purpose="Seven-shot acceptance test", scene_ids=["scene_001"])],
        scenes=[Scene(id="scene_001", section_id="section_001", order=1, narration_text=" ".join(LINES), shot_ids=[x.id for x in shots])],
        shots=shots, characters=[character],
    )
    plan = apply_visual_grammar(plan)
    plan = apply_composition_engine(plan)
    plan = finalize_plan_prompts(plan, 73001, STYLE_PROMPT.read_text().strip(), NEGATIVE_PROMPT.read_text().strip())
    store.save_plan(project, plan)
    state = store.load_state(project)
    state.script_status = "complete"
    state.planning_status = "complete"
    store.save_state(project, state)
    print(project, flush=True)
    pipeline = Pipeline(project, lambda message: print(message, flush=True))
    pipeline.generate_voice()
    pipeline.generate_images()
    pipeline.build_subtitles()
    final = pipeline.render_video()
    print(final, flush=True)


if __name__ == "__main__":
    main()
