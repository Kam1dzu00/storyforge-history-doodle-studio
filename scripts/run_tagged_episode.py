#!/usr/bin/env python3
"""Import an explicitly directed script and run it without losing tagged shots."""
from __future__ import annotations

import argparse
from pathlib import Path

from history_doodle.config import DEFAULT_VOICE, NEGATIVE_PROMPT, STYLE_PROMPT
from history_doodle.pipeline import Pipeline
from history_doodle.planner import apply_composition_engine, apply_visual_grammar, extract_production_script, finalize_plan_prompts, parse_director_tags
from history_doodle.schemas import ProjectPlan, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--duration", type=int, default=480)
    args = parser.parse_args()
    raw = extract_production_script(args.script.read_text(encoding="utf-8"))
    spoken, overrides = parse_director_tags(raw)
    blocks = [x for x in overrides if x.get("next_cue")]
    if not blocks:
        raise ValueError("The script contains no directed narration blocks")
    store = ProjectStore()
    project = store.create(args.title, "script", args.duration, DEFAULT_VOICE, raw)
    shots = []
    for index, direction in enumerate(blocks, 1):
        cue = direction["next_cue"]
        location = direction.get("BACKGROUND", "ancient Rome in the first or second century CE")
        shots.append(Shot(
            id=f"shot_{index:03d}", scene_id="scene_001", order=index,
            narration_context=cue, visual_subject=cue, location=location,
            action=direction.get("ACTION", "show the exact concrete narration beat"),
            historical_props=["historically accurate first- or second-century Roman materials and architecture", "no anachronistic objects unless the narration explicitly describes the modern comparison"],
            composition=direction.get("COMPOSITION", "single coherent historical scene"),
            prompt="", negative_prompt="", seed=0, estimated_duration=4,
        ))
    plan = ProjectPlan(
        sections=[StorySection(id="section_001", title=args.title, purpose="Preserve every explicitly directed narration beat", scene_ids=["scene_001"])],
        scenes=[Scene(id="scene_001", section_id="section_001", order=1, narration_text=spoken, shot_ids=[x.id for x in shots])],
        shots=shots,
    )
    plan = apply_visual_grammar(plan, overrides)
    plan = apply_composition_engine(plan, overrides)
    plan = finalize_plan_prompts(plan, 81001, STYLE_PROMPT.read_text().strip(), NEGATIVE_PROMPT.read_text().strip())
    store.save_plan(project, plan)
    state = store.load_state(project)
    state.script_status = "complete"
    state.planning_status = "complete"
    store.save_state(project, state)
    print(f"PROJECT={project}", flush=True)
    Pipeline(project, lambda message: print(message, flush=True)).full()


if __name__ == "__main__":
    main()
