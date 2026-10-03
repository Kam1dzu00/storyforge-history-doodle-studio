from pathlib import Path
import json
import pytest
from history_doodle.planner import target_words, finalize_plan_prompts, normalize_shot_counts
from history_doodle.render import ffmpeg_available, render
from history_doodle.schemas import CharacterCard, ProjectPlan, Scene, Shot, StorySection, WordStamp
from history_doodle.storage import ProjectStore
from history_doodle.subtitles import chunks
from history_doodle.timing import allocate_timeline, validate_word_timestamps
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

def test_long_manifest_has_50_plus_shots():
    plan=sample_plan(1); plan.scenes[0].narration_text="word "*1500
    plan=normalize_shot_counts(plan,600)
    assert 80 <= len(plan.shots) <= 95
    timed=allocate_timeline(plan,600)
    assert all(3 <= s.end_time-s.start_time <= 10 for s in timed.shots)

def test_locked_style_and_character_card_propagate():
    plan=sample_plan(1); plan.characters=[CharacterCard(id="hero",name="Hero",role="main",visual_identity="adult Viking",fixed_traits=["ginger beard","beige tunic"])] ; plan.shots[0].character_ids=["hero"]
    out=finalize_plan_prompts(plan,42,"LOCKED_STYLE_PROMPT","children's book")
    assert out.shots[0].prompt.startswith("LOCKED_STYLE_PROMPT")
    assert "CHARACTER CARD" in out.shots[0].prompt and "ginger beard" in out.shots[0].prompt

def test_word_timing_validation():
    words=[WordStamp(word="one",start=0,end=.3),WordStamp(word="two",start=.4,end=.7)]
    assert validate_word_timestamps(words,1.0)==[]
    with pytest.raises(ValueError): validate_word_timestamps([WordStamp(word="x",start=2,end=3)],1)

def test_failed_shot_blocks_render(tmp_path):
    p=sample_plan(1); p.shots[0].status="failed"; p.shots[0].start_time=0; p.shots[0].end_time=5
    with pytest.raises(RuntimeError,match="1 shots missing"): render(tmp_path,p,tmp_path/"voice.wav",tmp_path/"subs.ass")

def test_cancel_flag_is_resumable(tmp_path):
    from history_doodle.pipeline import Pipeline
    store=ProjectStore(tmp_path); project=store.create("cancel","script",60,"am_michael","hello")
    pipe=Pipeline(project); pipe.cancel()
    with pytest.raises(RuntimeError,match="отменена"): pipe._check_cancel()
    assert store.load_state(project).script_status=="pending"
