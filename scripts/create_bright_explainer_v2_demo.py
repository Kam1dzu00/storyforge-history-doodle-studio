from __future__ import annotations

import json

from history_doodle.config import PROJECTS_DIR
from history_doodle.schemas import ProjectPlan, ProjectState, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore
from history_doodle.style_system import PromptComposer


PROJECT=PROJECTS_DIR/"bright-explainer-v2-demo"
CASES=[
    ("Ancient Roman toilets were worse than you think.","hook_title_card","an alarmed ancient Roman beside a long communal stone latrine bench with multiple round openings, unmistakably ancient, no modern porcelain",1),
    ("Romans cleaned themselves with a sea sponge fixed to a wooden stick.","object_single","one large wet sea sponge fixed to a wooden stick, instantly recognizable",0),
    ("The same sponge could be rinsed and shared by many people.","process_sequence","three clear visual stages without labels: rinse the sponge, place it in a bucket, pass it onward",0),
    ("Modern plumbing is a blessing, so subscribe for more strange history.","comparison_split","left side ancient communal stone latrine, right side clean modern porcelain toilet, obvious contrast",1),
]


def main():
    for rel in ("planning","audio/chunks","images","subtitles","render/temp","logs"):(PROJECT/rel).mkdir(parents=True,exist_ok=True)
    state=ProjectState(project_id=PROJECT.name,title="Bright Explainer V2 Demo",input_mode="script",target_duration_seconds=20,voice="am_eric",voice_preset="energetic_explainer",speech_speed=1.04,style_mode="bright_explainer",host_enabled=False,semantic_visual_routing=True,full_bleed_frames=True,background_music_enabled=True,background_music_mode="procedural",music_profile="BRIGHT_FACTS",background_music_gain_db=1.5,background_music_duck_db=5,background_music_fade_in=1.2,background_music_fade_out=2.5,script_status="complete",planning_status="complete")
    composer=PromptComposer(); scenes=[]; shots=[]
    for index,(text,category,focus,people) in enumerate(CASES,1):
        scene_id=f"scene_{index:03d}"; shot=Shot(id=f"shot_{index:03d}",scene_id=scene_id,order=index,narration_context=text,visual_subject=focus,location="Ancient Rome or exact comparison setting",action=focus,composition="dynamic full-bleed scene",prompt="",negative_prompt="",seed=92000+index*311,estimated_duration=4.5,visual_category=category,visual_focus=focus,host_present=False,routing_source="manual",people_count=people,framing="WIDE" if index in (1,4) else "CLOSEUP" if index==2 else "MEDIUM_WIDE")
        shot.prompt,shot.negative_prompt,_=composer.compose(state,shot); shots.append(shot); scenes.append(Scene(id=scene_id,section_id="section_001",order=index,narration_text=text,shot_ids=[shot.id]))
    plan=ProjectPlan(sections=[StorySection(id="section_001",title="Roman toilet demo",purpose="Bright Explainer V2 workflow demo",scene_ids=[x.id for x in scenes])],scenes=scenes,shots=shots)
    store=ProjectStore(); store.save_state(PROJECT,state); store.save_plan(PROJECT,plan)
    script="\n\n".join(x[0] for x in CASES); (PROJECT/"script.txt").write_text(script,encoding="utf-8")
    segments=[{"text":x[0],"speed":1.04,"pause_after_ms":120} for x in CASES]
    (PROJECT/"voice_segments.json").write_text(json.dumps(segments,indent=2),encoding="utf-8")
    print(PROJECT)


if __name__=="__main__":main()
