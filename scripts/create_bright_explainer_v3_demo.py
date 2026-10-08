from __future__ import annotations

import json

from history_doodle.config import PROJECTS_DIR
from history_doodle.schemas import ProjectPlan, ProjectState, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore
from history_doodle.style_system import PromptComposer


PROJECT = PROJECTS_DIR / "bright-explainer-v3-demo"
CASES = [
    ("Ancient Roman toilets were worse than you think.", "character_reaction", "an alarmed Roman citizen recoiling from an enormous communal stone latrine that rushes toward camera, shocking scale and strong cyan-orange contrast", 1, "SLIGHT_LOW", "WIDE"),
    ("Imagine sharing a public toilet with a whole crowd.", "character_reaction", "one expressive Roman citizen in the foreground staring in disgust over his shoulder at a busy communal latrine, other Romans only as distant context", 3, "OVER_SHOULDER", "MEDIUM"),
    ("Romans cleaned themselves with a sea sponge fixed to a wooden stick.", "object_single", "a giant wet sea sponge fixed to a wooden stick almost filling the frame inside a torchlit Roman latrine, bucket behind and one tiny horrified reaction figure far away", 1, "SLIGHT_LOW", "CLOSEUP"),
    ("They rinsed it, dipped it, and passed it to the next person.", "process_sequence", "one cohesive Roman latrine scene showing a hand rinsing the sponge in flowing water, a bucket at center, and another hand receiving it, connected by clean motion arcs without panels", 2, "SLIGHT_HIGH", "MEDIUM_WIDE"),
    ("Ancient sanitation was nothing like a modern bathroom.", "comparison_split", "a single cinematic doorway transition: grim torchlit ancient communal latrine on the left and sparkling modern bathroom on the right, strong warm-cool contrast without labels", 0, "EYE_LEVEL", "WIDE"),
    ("Shared sponges could carry bacteria and health risks.", "medical_diagram", "towering stylized bacteria swarm invading around the wet sponge while an expressive Roman recoils in the background, dramatic microscopic scale and red danger accents", 1, "SLIGHT_LOW", "CLOSEUP"),
    ("Modern plumbing suddenly feels like a superpower.", "character_reaction", "relieved modern adult embracing a gleaming toilet like a heroic invention, dramatic bathroom lighting, comic rays and dynamic diagonal composition", 1, "SLIGHT_HIGH", "MEDIUM_WIDE"),
    ("Want more strange history? Subscribe and watch the full Ancient Rome episode.", "closing_cta", "confident expressive Roman presenter pointing toward clean empty space on the right, iconic sponge-on-stick resting safely in the background, triumphant warm cinematic finale", 1, "SLIGHT_LOW", "MEDIUM"),
]


def main():
    for rel in ("planning", "audio/chunks", "images", "subtitles", "render/temp", "logs"):
        (PROJECT / rel).mkdir(parents=True, exist_ok=True)
    state = ProjectState(
        project_id=PROJECT.name, title="Bright Explainer Polish V3 Demo", input_mode="script",
        target_duration_seconds=32, voice="am_eric", voice_preset="energetic_explainer", speech_speed=1.06,
        style_mode="bright_explainer", host_enabled=False, semantic_visual_routing=True, full_bleed_frames=True,
        background_music_enabled=True, background_music_mode="procedural", music_profile="BRIGHT_FACTS",
        background_music_gain_db=1.5, background_music_duck_db=5,
        background_music_fade_in=1.0, background_music_fade_out=2.0,
        script_status="complete", planning_status="complete",
    )
    composer=PromptComposer(); scenes=[]; shots=[]
    for index,(text,category,focus,people,angle,framing) in enumerate(CASES,1):
        scene_id=f"scene_{index:03d}"
        shot=Shot(
            id=f"shot_{index:03d}",scene_id=scene_id,order=index,narration_context=text,
            visual_subject=focus,location="historically grounded Roman or modern environment",action=focus,
            environment_context="complete cinematic environment with foreground midground background depth",
            foreground_elements=["cropped foreground element or action accent"],midground_elements=[focus],
            background_elements=["environmental context with atmospheric depth"],composition="dynamic diagonal full-bleed animated-show frame",
            prompt="",negative_prompt="",seed=330000+index*1777,estimated_duration=4.0,
            visual_category=category,visual_focus=focus,host_present=False,routing_source="manual",
            people_count=people,framing=framing,camera_angle=angle,
            subject_placement="OFF_CENTER" if index not in (4,5) else "FOREGROUND_LEFT",
        )
        shot.prompt,shot.negative_prompt,_=composer.compose(state,shot)
        shots.append(shot); scenes.append(Scene(id=scene_id,section_id="section_001",order=index,narration_text=text,shot_ids=[shot.id]))
    plan=ProjectPlan(sections=[StorySection(id="section_001",title="Roman sanitation V3",purpose="Bright Explainer Polish V3 acceptance demo",scene_ids=[x.id for x in scenes])],scenes=scenes,shots=shots)
    store=ProjectStore(); store.save_state(PROJECT,state); store.save_plan(PROJECT,plan)
    (PROJECT/"script.txt").write_text("\n\n".join(x[0] for x in CASES),encoding="utf-8")
    segments=[{"text":x[0],"speed":1.06,"pause_after_ms":100} for x in CASES]
    (PROJECT/"voice_segments.json").write_text(json.dumps(segments,indent=2),encoding="utf-8")
    print(PROJECT)


if __name__ == "__main__": main()
