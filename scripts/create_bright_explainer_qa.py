from __future__ import annotations

import json
from pathlib import Path

from history_doodle.config import PROJECTS_DIR
from history_doodle.schemas import ProjectPlan, ProjectState, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore
from history_doodle.style_system import CharacterRegistry, PromptComposer, StyleRegistry, VisualRouter


PROJECT = PROJECTS_DIR / "bright-explainer-4-shot-qa"
CASES = [
    ("I thought the air conditioner was trying to kill me.", "host_reaction"),
    ("It was 38 degrees.", "infographic_metric"),
    ("This is an air conditioner.", "object_single"),
    ("Meningitis is inflammation of the protective membranes around the brain and spinal cord.", "medical_diagram"),
]


def main() -> None:
    for rel in ("planning", "audio/chunks", "images", "subtitles", "render/temp", "logs"):
        (PROJECT / rel).mkdir(parents=True, exist_ok=True)
    state = ProjectState(
        project_id=PROJECT.name, title="Bright Explainer 4-Shot QA", input_mode="script",
        target_duration_seconds=20, style_mode="bright_explainer_host", host_enabled=True,
        host_character_id="kam1dzu00_host", semantic_visual_routing=True, full_bleed_frames=True,
        planning_status="complete", output_width=1920, output_height=1080,
    )
    router = VisualRouter(); composer = PromptComposer(); shots = []
    for index, (narration, expected) in enumerate(CASES, 1):
        decision = router.route(narration)
        item = Shot(
            id=f"shot_{index:03d}", scene_id="scene_001", order=index,
            narration_context=narration, visual_subject=decision.visual_focus, location="modern explainer studio",
            action="show the exact narration beat", composition="dynamic asymmetric full-bleed composition",
            prompt="", negative_prompt="", seed=73000 + index, estimated_duration=5.0,
            visual_category=decision.visual_category, visual_focus=decision.visual_focus,
            host_present=decision.host_present, host_role=decision.host_role, routing_source="auto",
            host_expression="skeptical comic alarm" if decision.host_present else None,
            host_pose="recoiling beside a wall-mounted air conditioner" if decision.host_present else None,
            people_count=1 if decision.host_present else 0,
        )
        assert item.visual_category == expected
        item.prompt, item.negative_prompt, _ = composer.compose(state, item)
        shots.append(item)
    plan = ProjectPlan(
        sections=[StorySection(id="section_001", title="Style switch QA", purpose="Visual routing QA", scene_ids=["scene_001"])],
        scenes=[Scene(id="scene_001", section_id="section_001", order=1, narration_text="\n".join(x[0] for x in CASES), shot_ids=[x.id for x in shots])],
        shots=shots,
    )
    store = ProjectStore(); store.save_state(PROJECT, state); store.save_plan(PROJECT, plan)
    (PROJECT / "script.txt").write_text("\n".join(x[0] for x in CASES), encoding="utf-8")
    style_ok = StyleRegistry().get("bright_explainer_host")["style_id"] == "bright_explainer_host"
    host_ok = CharacterRegistry().get("kam1dzu00_host")["character_id"] == "kam1dzu00_host"
    real, stylized = CharacterRegistry().reference_status("kam1dzu00_host", "bright_explainer_host")
    report = []
    for item in shots:
        report.append({
            "shot_id": item.id, "visual_category": item.visual_category,
            "real_identity_reference_resolved": real == "Ready",
            "stylized_reference_resolved": stylized == "Ready",
            "host_profile_resolved": host_ok,
            "style_profile_resolved": style_ok,
            "references_actually_passed_to_image_backend": False,
            "blocked_reason": "HOST_IMAGE_REFERENCE_CONDITIONING_UNSUPPORTED" if item.host_present else None,
        })
    (PROJECT / "logs/reference_resolution_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(PROJECT)


if __name__ == "__main__":
    main()
