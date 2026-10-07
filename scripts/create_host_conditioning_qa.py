from __future__ import annotations

import json

from history_doodle.config import PROJECTS_DIR
from history_doodle.schemas import ProjectPlan, ProjectState, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore
from history_doodle.style_system import CharacterRegistry, PromptComposer, StyleRegistry


PROJECT = PROJECTS_DIR / "bright-explainer-host-conditioning-qa"
CASES = [
    ("Neutral explanation at a desk.", "host_explaining", "calm and engaged", "seated at a desk, one open hand"),
    ("A skeptical close-up.", "host_reaction", "skeptical raised eyebrow", "close-up, hand near chin"),
    ("A shocked reaction.", "host_reaction", "shocked but readable", "leaning back with two visible hands"),
    ("The host points at a thermometer.", "host_explaining", "confident explainer", "pointing at one large thermometer"),
    ("The host reacts to an air conditioner.", "host_reaction", "comic suspicion", "standing beside a wall-mounted air conditioner"),
    ("The host stands outdoors in cold weather.", "host_explaining", "cold but composed", "standing outdoors in a winter coat"),
    ("A thermometer showing 38 degrees.", "infographic_metric", None, None),
    ("One wall-mounted air conditioner.", "object_single", None, None),
]


def main() -> None:
    for rel in ("planning", "audio/chunks", "images", "subtitles", "render/temp", "logs"):
        (PROJECT / rel).mkdir(parents=True, exist_ok=True)
    state = ProjectState(
        project_id=PROJECT.name, title="Bright Explainer Host Conditioning QA", input_mode="script",
        target_duration_seconds=40, style_mode="bright_explainer_host", host_enabled=True,
        host_character_id="kam1dzu00_host", semantic_visual_routing=True, full_bleed_frames=True,
        planning_status="complete", output_width=1920, output_height=1080,
    )
    composer = PromptComposer(); shots = []
    for index, (narration, category, expression, pose) in enumerate(CASES, 1):
        host = index <= 6
        focus = narration.rstrip(".")
        item = Shot(
            id=f"shot_{index:03d}", scene_id="scene_001", order=index,
            narration_context=narration, visual_subject=focus, location="modern explainer studio" if index != 6 else "cold outdoor city",
            action=pose or focus, composition="dynamic asymmetric full-bleed 16:9 scene",
            prompt="", negative_prompt="", seed=84000 + index * 137, estimated_duration=5.0,
            visual_category=category, visual_focus=focus, host_present=host,
            host_role="explainer" if category == "host_explaining" else "reaction" if host else None,
            host_expression=expression, host_pose=pose, routing_source="manual",
            people_count=1 if host else 0,
        )
        item.prompt, item.negative_prompt, _ = composer.compose(state, item)
        shots.append(item)
    plan = ProjectPlan(
        sections=[StorySection(id="section_001", title="Host conditioning QA", purpose="Identity and routing QA", scene_ids=["scene_001"])],
        scenes=[Scene(id="scene_001", section_id="section_001", order=1, narration_text="\n".join(x[0] for x in CASES), shot_ids=[x.id for x in shots])],
        shots=shots,
    )
    store = ProjectStore(); store.save_state(PROJECT, state); store.save_plan(PROJECT, plan)
    (PROJECT / "script.txt").write_text("\n".join(x[0] for x in CASES), encoding="utf-8")
    registry = CharacterRegistry(); real, stylized = registry.reference_status("kam1dzu00_host", "bright_explainer_host")
    report = [{
        "shot_id": item.id, "host_present": bool(item.host_present),
        "real_identity_reference_resolved": real == "Ready",
        "stylized_reference_resolved": stylized == "Ready",
        "host_profile_resolved": registry.get("kam1dzu00_host")["character_id"] == "kam1dzu00_host",
        "style_profile_resolved": StyleRegistry().get("bright_explainer_host")["style_id"] == "bright_explainer_host",
        "references_expected_by_backend": bool(item.host_present),
        "references_actually_passed_to_image_backend": False,
    } for item in shots]
    (PROJECT / "logs/reference_resolution_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(PROJECT)


if __name__ == "__main__":
    main()
