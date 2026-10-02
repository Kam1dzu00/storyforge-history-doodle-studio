from pathlib import Path
import json
import pytest
from history_doodle.planner import target_words
from history_doodle.render import ffmpeg_available
from history_doodle.schemas import CharacterCard, ProjectPlan, Scene, Shot, StorySection, WordStamp
from history_doodle.storage import ProjectStore
from history_doodle.subtitles import chunks
from history_doodle.timing import allocate_timeline
from history_doodle.util import prompt_hash, shot_seed

def sample_plan(nshots=2):
    shots=[Shot(id=f"shot_{i}",scene_id="scene_1",order=i,narration_context="x",visual_subject="x",location="x",action="x",composition="wide",prompt="single",negative_prompt="none",seed=i,estimated_duration=5) for i in range(1,nshots+1)]
    return ProjectPlan(sections=[StorySection(id="sec_1",title="A",purpose="B",scene_ids=["scene_1"])],scenes=[Scene(id="scene_1",section_id="sec_1",order=1,narration_text="one two three four",shot_ids=[s.id for s in shots])],shots=shots)

def test_manifest_validation(): assert ProjectPlan.model_validate(sample_plan().model_dump())
def test_word_target(): assert target_words(600)==1580
def test_invalid_json_schema():
    data=sample_plan().model_dump(); data["scenes"][0]["shot_ids"]=["missing"]
    with pytest.raises(ValueError): ProjectPlan.model_validate(data)
def test_timeline_equals_audio():
    p=allocate_timeline(sample_plan(),14); assert p.shots[-1].end_time==14; assert sum(s.end_time-s.start_time for s in p.shots)==pytest.approx(14)
def test_duration_guard():
    with pytest.raises(ValueError): allocate_timeline(sample_plan(1),20)
def test_subtitle_chunking():
    w=[WordStamp(word=x,start=i*.2,end=i*.2+.18) for i,x in enumerate("one two three four five six".split())]; assert max(map(len,chunks(w)))<=5
def test_seed_determinism(): assert shot_seed(42,3)==shot_seed(42,3)!=shot_seed(42,4)
def test_prompt_hash(): assert prompt_hash("a")==prompt_hash("a")!=prompt_hash("b")
def test_project_roundtrip(tmp_path):
    s=ProjectStore(tmp_path); p=s.create("A title","brief",60,"am_michael","hello"); assert s.load_state(p).title=="A title"
def test_resume_fields(tmp_path):
    p=sample_plan(); sh=p.shots[0]; sh.status="complete"; sh.prompt_hash=prompt_hash(sh.prompt,sh.negative_prompt); sh.image_path="images/a.png"; assert sh.status=="complete"
def test_ffmpeg(): assert ffmpeg_available()

