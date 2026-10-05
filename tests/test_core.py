from pathlib import Path
import json
import pytest
from history_doodle.planner import target_words, finalize_plan_prompts, normalize_shot_counts, parse_director_tags, apply_visual_grammar, apply_composition_engine, extract_production_script
from history_doodle.render import ffmpeg_available, render
from history_doodle.schemas import CharacterCard, ProjectPlan, Scene, Shot, StorySection, WordStamp
from history_doodle.storage import ProjectStore


def test_segment_voice_map_must_match_locked_narration(tmp_path, monkeypatch):
    project = ProjectStore(tmp_path).create("Voice map", "script", 60, "am_michael", "First line.\n\nSecond line.")
    (project / "voice_segments.json").write_text('[{"text":"Changed line.","speed":0.9,"pause_after_ms":300}]')
    from history_doodle.pipeline import Pipeline
    monkeypatch.setattr("history_doodle.pipeline.VoiceEngine.generate_segments", lambda *args, **kwargs: None)
    try:
        Pipeline(project).generate_voice()
    except ValueError as exc:
        assert "does not exactly match" in str(exc)
    else:
        raise AssertionError("mismatched voice metadata must be rejected")


def test_silent_outro_segments_are_accepted_by_locked_text_validation(tmp_path, monkeypatch):
    from history_doodle.pipeline import Pipeline
    project = ProjectStore(tmp_path).create("Outro", "script", 60, "am_michael", "Final line.")
    (project / "voice_segments.json").write_text('[{"text":"Final line.","speed":0.93,"pause_after_ms":0},{"text":"","speed":0.93,"pause_after_ms":0,"silence_ms":1200}]')
    monkeypatch.setattr("history_doodle.pipeline.VoiceEngine.generate_segments", lambda *args, **kwargs: project / "audio/narration.wav")
    monkeypatch.setattr("history_doodle.pipeline.TimestampEngine.transcribe", lambda *args, **kwargs: [])
    monkeypatch.setattr("history_doodle.pipeline.quality_report", lambda *args, **kwargs: {})
    with pytest.raises(FileNotFoundError):
        Pipeline(project).generate_voice()
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

def test_director_tags_are_not_narrated():
    raw="Tools were essential.\n[VISUAL: OBJECT_COLLECTION]\n[OBJECTS: axe | sickle | knife]\n[NO PEOPLE]\nThey worked every day."
    spoken,tags=parse_director_tags(raw)
    assert "[" not in spoken and spoken=="Tools were essential.\nThey worked every day."
    assert tags[0]["VISUAL"]=="OBJECT_COLLECTION" and tags[0]["NO PEOPLE"]=="true"

def test_manual_object_override_removes_character_card():
    plan=sample_plan(1); plan.shots[0].narration_context="Tools were essential."
    plan.characters=[CharacterCard(id="hero",name="Hero",role="main",visual_identity="adult farmer")]; plan.shots[0].character_ids=["hero"]
    plan=apply_visual_grammar(plan,[{"cue":"Tools were essential.","VISUAL":"OBJECT_COLLECTION","OBJECTS":"axe | sickle | knife","NO PEOPLE":"true"}])
    out=finalize_plan_prompts(plan,42,"STYLE","NEG")
    assert out.shots[0].visual_type=="OBJECT_COLLECTION" and out.shots[0].people_count==0
    assert out.shots[0].objects==["axe","sickle","knife"] and "CHARACTER CARD" not in out.shots[0].prompt and "NO PEOPLE" in out.shots[0].prompt

def test_visual_diversity_breaks_three_identical_types():
    plan=sample_plan(3)
    for shot in plan.shots: shot.narration_context="He walked to work."
    plan=apply_visual_grammar(plan)
    assert not (plan.shots[0].visual_type==plan.shots[1].visual_type==plan.shots[2].visual_type)

def test_old_manifest_gets_visual_defaults():
    data=sample_plan(1).model_dump(); shot=data["shots"][0]
    for key in ("visual_type","people_count","objects","labels","background_style","director_override"): shot.pop(key)
    loaded=ProjectPlan.model_validate(data).shots[0]
    assert loaded.visual_type=="CHARACTER_MEDIUM" and loaded.people_count==1

def test_labels_metadata_roundtrip_without_image_text():
    plan=sample_plan(1); plan.shots[0].labels=["Axe","Sickle"]
    assert ProjectPlan.model_validate(plan.model_dump()).shots[0].labels==["Axe","Sickle"]

def test_anatomy_safety_is_added_to_human_prompt():
    plan=sample_plan(1); plan.shots[0].people_count=1
    out=finalize_plan_prompts(plan,42,"STYLE","NEG")
    assert "exactly two arms and two legs" in out.shots[0].prompt
    assert "no overlapping limbs" in out.shots[0].prompt

def test_viking_tools_script_has_varied_object_first_grammar():
    lines=["A Viking farmer used several simple tools.","An axe helped split wood.","A sickle cut grain.","A knife handled dozens of small daily tasks.","His house centered around a warm hearth.","Outside, the farm stretched toward the fjord.","At the end of the day, he carried a bucket back to the house."]
    plan=sample_plan(len(lines))
    for shot,line in zip(plan.shots,lines): shot.narration_context=shot.visual_subject=line
    plan=apply_visual_grammar(plan)
    types=[x.visual_type for x in plan.shots]
    assert sum(x.startswith("CHARACTER") for x in types)<4
    assert "OBJECT_COLLECTION" in types and "ENVIRONMENT" in types

def test_production_blueprint_metadata_is_not_narrated():
    raw="# TITLE\nA title\n# CORE IDEA\nA pitch\n## 0:00–0:30 — HOOK\n[VISUAL: OBJECT]\n[NO PEOPLE]\nThe real narration starts here."
    clean=extract_production_script(raw); spoken,tags=parse_director_tags(clean)
    assert spoken=="The real narration starts here."
    assert tags[0]["next_cue"]=="The real narration starts here."

def test_unknown_director_character_creates_valid_card():
    plan=sample_plan(1); plan.shots[0].narration_context="A farmer wakes."
    plan=apply_visual_grammar(plan,[{"cue":"","next_cue":"A farmer wakes.","VISUAL":"CHARACTER","CHARACTER":"main_viking"}])
    assert plan.shots[0].character_ids==["main_viking"]
    assert ProjectPlan.model_validate(plan.model_dump())

def test_optional_composition_tags_are_not_narrated():
    raw="He repairs a fence.\n[PLACEMENT: LEFT]\n[ANGLE: PROFILE]\n[FOREGROUND: broken rail]\n[ACTION: tying the rail with rope]"
    spoken,tags=parse_director_tags(raw)
    assert spoken=="He repairs a fence."
    assert tags[0]["PLACEMENT"]=="LEFT" and tags[0]["ACTION"]=="tying the rail with rope"

def test_centered_character_without_justification_is_moved():
    plan=sample_plan(1); shot=plan.shots[0]
    shot.narration_context="A farmer repairs a fence."; shot.visual_type="CHARACTER_MEDIUM"; shot.subject_placement="CENTERED_CHARACTER"
    out=apply_composition_engine(plan,[{"cue":"A farmer repairs a fence.","PLACEMENT":"CENTER"}])
    assert out.shots[0].subject_placement in {"LEFT_THIRD","RIGHT_THIRD"}

def test_character_action_and_historical_details_are_specific():
    plan=sample_plan(1); shot=plan.shots[0]
    shot.narration_context="Later, he repairs a broken section of fence."; shot.location="Viking farm"; shot.visual_type="CHARACTER_MEDIUM"
    out=apply_composition_engine(plan).shots[0]
    assert "fence" in out.action_description and out.action_description not in {"standing","posing"}
    assert len(out.historical_story_details)>=2

def test_composition_overrides_win():
    plan=sample_plan(1); shot=plan.shots[0]
    shot.narration_context="He repairs a fence."; shot.visual_type="CHARACTER_MEDIUM"
    out=apply_composition_engine(plan,[{"cue":"He repairs a fence.","PLACEMENT":"LEFT","ANGLE":"PROFILE","ACTION":"tying a broken rail with rope"}]).shots[0]
    assert out.subject_placement=="LEFT_THIRD" and out.camera_angle=="PROFILE"
    assert out.action_description=="tying a broken rail with rope"

def test_object_and_environment_shots_have_no_people():
    plan=sample_plan(2)
    plan.shots[0].narration_context="His tools are simple: an axe, a sickle and a knife."
    plan.shots[1].narration_context="Near the coast, a wooden boat needs maintenance too."
    out=apply_composition_engine(apply_visual_grammar(plan))
    assert out.shots[0].visual_type=="OBJECT_COLLECTION" and out.shots[0].people_count==0
    assert out.shots[1].visual_type=="ENVIRONMENT" and out.shots[1].people_count==0

def test_three_identical_compositions_are_broken():
    plan=sample_plan(3)
    for shot in plan.shots:
        shot.narration_context="A farmer works."; shot.visual_type="CHARACTER_MEDIUM"
    out=apply_composition_engine(plan)
    triples=[(x.subject_placement,x.camera_angle,x.framing) for x in out.shots]
    assert len(set(triples))>1

def test_old_manifest_gets_composition_defaults_and_continuity_roundtrip():
    data=sample_plan(1).model_dump(); shot=data["shots"][0]
    new_fields=("visual_purpose","subject_placement","camera_angle","framing","foreground_elements","midground_elements","background_elements","environment_context","historical_story_details","action_description","negative_space_direction","centered_justification","continuity_key","time_of_day","weather","validation_checks")
    for key in new_fields: shot.pop(key)
    loaded=ProjectPlan.model_validate(data)
    assert loaded.shots[0].subject_placement=="OFF_CENTER"
    enriched=apply_composition_engine(loaded)
    restored=ProjectPlan.model_validate(enriched.model_dump()).shots[0]
    assert restored.continuity_key=="scene_1" and restored.time_of_day
