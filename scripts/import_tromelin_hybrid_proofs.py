from __future__ import annotations

import json
from pathlib import Path

from history_doodle.config import PROJECTS_DIR
from history_doodle.hybrid import MimicSceneContract, load_contracts, route_shot
from history_doodle.audio import audio_duration, quality_report
from history_doodle.schemas import ProjectPlan, ProjectState, QuestionBeat, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore
from history_doodle.style_system import prepare_plan
from history_doodle.util import shot_seed


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "projects/storyforge-hybrid-tromelin-production-v1/sources/StoryForge_HYBRID_TROMELIN_PRODUCTION_V1"
CONTRACTS = {item.id: item for item in load_contracts(PACK / "09_MIMIC_SCENE_CONTRACTS.json")}
STYLE = "calm_animated_editorial_2d"
NEGATIVE = "product deck, SaaS, dashboard, floating cards, corporate infographic, childlike, glossy 3D, photorealism, pseudo-text, gibberish, watermark, malformed anatomy, extra limbs"


PROOFS = {
    "tromelin-proof-opening": {
        "title": "Tromelin Hybrid Proof A — Opening",
        "script": """In 1761, a French ship struck a reef in the middle of the Indian Ocean.

The crew survived.

So did dozens of Malagasy people being transported in slavery.

But when the French crew finally built a boat and escaped the island, they did not take everyone with them.

They left the Malagasy survivors behind.

With a promise.

“We’ll come back.”

They did not come back for fifteen years.

[QUESTION_BEAT]
HOW DO YOU SURVIVE FIFTEEN YEARS ON AN ISLAND WITH ALMOST NOTHING?

This is the story of Tromelin Island — one of the strangest survival stories ever reconstructed from a shipwreck.

And the most remarkable part is that much of what we know today does not come from a diary.

It comes from the things the survivors repaired, rebuilt, and refused to throw away.""",
        "shots": [
            ("In 1761, a French ship struck a reef in the middle of the Indian Ocean.", "Night ocean map: Madagascar, tiny Tromelin, a small eighteenth-century ship route", "mimic_native_scene", "M01"),
            ("The crew survived. So did dozens of Malagasy people being transported in slavery.", "Dawn on a tiny sand island, diverse exhausted adult survivors among wreck timber, respectful distant grouping", "storyforge", None),
            ("But when the French crew finally built a boat and escaped the island, they did not take everyone with them.", "Makeshift wooden boat departing while Malagasy survivors remain small on the pale shore", "storyforge", None),
            ("They left the Malagasy survivors behind. With a promise. We’ll come back.", "Back-view survivors facing an empty horizon, boat shrinking in the distance, restrained grief", "storyforge", None),
            ("They did not come back for fifteen years.", "Fixed island horizon with weather and celestial cycles passing from 1761 to 1776", "mimic_overlay", "M02"),
            ("HOW DO YOU SURVIVE FIFTEEN YEARS ON AN ISLAND WITH ALMOST NOTHING?", "Tiny island silhouette surrounded by moving ocean texture, immense negative space", "mimic_native_scene", None),
            ("This is the story of Tromelin Island — one of the strangest survival stories ever reconstructed from a shipwreck.", "Aerial editorial view of Tromelin, reef ring, wreck traces and endless desaturated ocean", "storyforge", None),
            ("And the most remarkable part is that much of what we know today does not come from a diary. It comes from the things the survivors repaired, rebuilt, and refused to throw away.", "Archaeological still life of a repeatedly repaired metal bowl, rope, hand tools and weathered wood on sand", "storyforge", None),
        ],
    },
    "tromelin-proof-water-bowl": {
        "title": "Tromelin Hybrid Proof B — Water and Repaired Bowl",
        "script": """People can survive a long time without food.

Without water, the clock is much shorter.

So before anything else, the survivors had to solve the island itself.

They dug.

They reached brackish water.

It was not good water.

But it was water.

They collected rain whenever they could.

They hunted fish, seabirds, and turtles.

They pulled material from the wreck.

Wood became fuel.

Metal became tools and containers.

Anything that could be reused mattered.

Archaeologists would later recover metal objects repaired again and again.

One vessel had been patched seven times.

Think about what that means.

A broken bowl was not trash.

Trash is something you can replace.

On Tromelin, almost nothing could be replaced.

[QUESTION_BEAT]
WHAT DO YOU KEEP WHEN YOU KNOW NOTHING NEW IS COMING?

The answer was simple.

Almost everything.""",
        "shots": [
            ("People can survive a long time without food. Without water, the clock is much shorter.", "Close detail of a dry clay cup and cracked sand beside endless ocean, no people", "storyforge", None),
            ("So before anything else, the survivors had to solve the island itself. They dug. They reached brackish water.", "Island cross-section with shallow hand-dug well, water line and simple lowered vessel", "mimic_overlay", "M03"),
            ("It was not good water. But it was water. They collected rain whenever they could.", "Adults in profile collecting rain from a low stone shelter into salvaged metal vessels", "storyforge", None),
            ("They hunted fish, seabirds, and turtles.", "Wide shoreline survival scene with fishing silhouettes, seabirds overhead and turtle tracks, respectful distance", "storyforge", None),
            ("They pulled material from the wreck. Wood became fuel. Metal became tools and containers.", "Wreck timber beside a small controlled fire, salvaged metal reshaped into simple tools", "storyforge", None),
            ("Anything that could be reused mattered. Archaeologists would later recover metal objects repaired again and again.", "Excavated repaired metal objects emerging from pale sand, adult archaeology editorial frame", "storyforge", None),
            ("One vessel had been patched seven times. Think about what that means. A broken bowl was not trash.", "Single weathered metal bowl receives seven visible repair patches one by one", "mimic_native_scene", "M04"),
            ("Trash is something you can replace. On Tromelin, almost nothing could be replaced. WHAT DO YOU KEEP WHEN YOU KNOW NOTHING NEW IS COMING? The answer was simple. Almost everything.", "Repaired bowl centered low against the island horizon, seven patches glowing subtly, large quiet negative space", "mimic_native_scene", None),
        ],
    },
    "tromelin-proof-final-rescue": {
        "title": "Tromelin Hybrid Proof C — Final Rescue",
        "script": """In 1775, fourteen years after the wreck, a rescue attempt reached the island.

It failed.

A sailor became stranded during the attempt.

Now the castaways had one more person on the island.

The following year, that sailor and several of the remaining castaways built another raft and left.

Among them were the last men of the community.

Again, the island became quieter.

By late 1776, the people still waiting there were seven women and a baby only months old.

Fifteen years after the original shipwreck.

Fifteen years after the promise.

[QUESTION_BEAT]
WHAT WOULD RESCUE EVEN FEEL LIKE AFTER FIFTEEN YEARS?

On November twenty-ninth, 1776, a French corvette finally reached the island.

Its commander was Jacques Marie de Tromelin.

The survivors were taken aboard.

Seven women.

One infant.

The island that had been called the Isle of Sand would eventually carry Tromelin’s name.

But the story belonged to the people who had survived there.""",
        "shots": [
            ("In 1775, fourteen years after the wreck, a rescue attempt reached the island. It failed.", "Small rescue boat defeated by breaking reef surf under storm-gray sky", "storyforge", None),
            ("A sailor became stranded during the attempt. Now the castaways had one more person on the island.", "Distant sailor silhouette wading ashore toward a waiting group by stone shelters", "storyforge", None),
            ("The following year, that sailor and several of the remaining castaways built another raft and left. Among them were the last men of the community.", "Low timber raft leaving through pale surf, remaining community watched from behind", "storyforge", None),
            ("Again, the island became quieter. By late 1776, the people still waiting there were seven women and a baby only months old.", "Seven adult women and one bundled infant gathered in a shared stone courtyard, dignified silhouettes", "storyforge", None),
            ("Fifteen years after the original shipwreck. Fifteen years after the promise.", "Island with unobtrusive dates 1775, July 1776 and 29 November 1776 traced by small boat routes", "mimic_overlay", "M09"),
            ("WHAT WOULD RESCUE EVEN FEEL LIKE AFTER FIFTEEN YEARS?", "Back-view woman at the ocean horizon as a tiny sail slowly appears", "mimic_micro_character", None),
            ("On November twenty-ninth, 1776, a French corvette finally reached the island. Its commander was Jacques Marie de Tromelin. The survivors were taken aboard.", "French corvette beyond reef with launch approaching shore, survivors in restrained emotional wide", "storyforge", None),
            ("Seven women. One infant. The island that had been called the Isle of Sand would eventually carry Tromelin’s name. But the story belonged to the people who had survived there.", "Quiet final tableau: seven women and infant aboard ship looking back at tiny island at sunset", "storyforge", None),
        ],
    },
}


def build_project(project_id: str, spec: dict) -> Path:
    project = PROJECTS_DIR / project_id
    if (project / "planning/story.json").exists():
        print(f"SKIP existing {project}")
        return project
    for rel in ("planning", "audio/chunks", "images", "subtitles", "render/temp", "logs", "hybrid"):
        (project / rel).mkdir(parents=True, exist_ok=True)
    (project / "script.txt").write_text(spec["script"], encoding="utf-8")
    state = ProjectState(
        project_id=project_id,
        title=spec["title"],
        input_mode="script",
        target_duration_seconds=65,
        voice="am_michael",
        speech_speed=1.03,
        style_mode=STYLE,
        hybrid_enabled=True,
        hybrid_style_profile=STYLE,
        output_width=1920,
        output_height=1080,
        background_music_enabled=True,
        background_music_mode="procedural",
        music_profile="HISTORICAL_AMBIENCE",
        script_status="complete",
        planning_status="complete",
    )
    store = ProjectStore()
    store.save_state(project, state)
    shots = []
    scenes = []
    for index, (narration, focus, route, contract_id) in enumerate(spec["shots"], 1):
        shot = Shot(
            id=f"shot_{index:03d}", scene_id=f"scene_{index:03d}", order=index,
            narration_context=narration, visual_subject=focus, location="Tromelin Island, western Indian Ocean",
            action=focus, composition="adult editorial documentary composition with one dominant focal point",
            prompt=focus, negative_prompt=NEGATIVE, seed=shot_seed(761000 + len(project_id), index),
            estimated_duration=8, visual_type="ENVIRONMENT", people_count=0 if not any(x in focus.lower() for x in ("survivor", "adult", "women", "sailor", "community")) else 8,
            visual_category="historical_documentary", visual_focus=focus, routing_source="manual",
            engine_route=route, hybrid_status="planned" if route != "storyforge" else "not_applicable",
            mimic_contract_id=contract_id,
            camera_motion="static" if route != "storyforge" else ("subtle_push" if index % 3 == 0 else "static"),
        )
        if contract_id:
            route_shot(shot, CONTRACTS[contract_id])
        shots.append(shot)
        scenes.append(Scene(id=shot.scene_id, section_id="proof", order=index, narration_text=narration, shot_ids=[shot.id]))
    section = StorySection(id="proof", title=spec["title"], purpose="shared-style hybrid proof", scene_ids=[x.id for x in scenes])
    plan = prepare_plan(ProjectPlan(sections=[section], scenes=scenes, shots=shots), state)
    store.save_plan(project, plan)
    (project / "hybrid/routing_report.json").write_text(json.dumps({"style": STYLE, "shots": [{"id": s.id, "engine_route": s.engine_route, "contract": s.mimic_contract_id, "motion_semantics": s.motion_semantics.model_dump() if s.motion_semantics else None} for s in plan.shots]}, indent=2), encoding="utf-8")
    print(project)
    return project


def finalize_existing_voice(project: Path) -> None:
    wav = project / "audio/narration.wav"
    stamps = project / "audio/word_timestamps.json"
    if not wav.exists() or not stamps.exists():
        return
    store = ProjectStore(); state = store.load_state(project); plan = store.load_plan(project)
    duration = audio_duration(wav); shots = sorted(plan.shots, key=lambda item: item.order)
    for index, shot in enumerate(shots):
        shot.start_time = duration * index / len(shots)
        shot.end_time = duration * (index + 1) / len(shots)
        scene = next(item for item in plan.scenes if item.id == shot.scene_id)
        scene.start_time, scene.end_time = shot.start_time, shot.end_time
        if "?" in shot.narration_context and shot.narration_context.upper() == shot.narration_context:
            shot.question_beat = QuestionBeat(question_text=shot.narration_context, background_visual=shot.visual_focus or shot.visual_subject)
            shot.labels = [shot.narration_context]
    store.save_plan(project, plan)
    state.voice_status = "complete"; state.images_status = "stale"; state.subtitles_status = "stale"; state.render_status = "stale"
    store.save_state(project, state)
    (project / "audio/quality_report.json").write_text(json.dumps(quality_report(wav), indent=2), encoding="utf-8")
    (project / "audio/voice_timeline.json").write_text(json.dumps([{"shot_id": shot.id, "start": shot.start_time, "end": shot.end_time} for shot in shots], indent=2), encoding="utf-8")
    print(f"VOICE_READY {project.name} {duration:.3f}s")


if __name__ == "__main__":
    for key, value in PROOFS.items():
        project = build_project(key, value)
        finalize_existing_voice(project)
