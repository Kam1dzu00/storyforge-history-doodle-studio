from pathlib import Path

from history_doodle.image_worker import backup_current_version
from history_doodle.pipeline import Pipeline
from history_doodle.schemas import ProjectPlan, Scene, Shot, StorySection
from history_doodle.storage import ProjectStore


def plan():
    item=Shot(id="shot_001",scene_id="scene_001",order=1,narration_context="x",visual_subject="x",location="x",action="x",composition="x",prompt="old prompt",negative_prompt="",seed=11,estimated_duration=3,image_path="images/shot_001.png",status="complete",start_time=0,end_time=3,approved=True)
    return ProjectPlan(sections=[StorySection(id="sec",title="x",purpose="x",scene_ids=["scene_001"])],scenes=[Scene(id="scene_001",section_id="sec",order=1,narration_text="x",shot_ids=[item.id])],shots=[item])


def test_single_shot_backup_is_versioned_and_bounded_by_caller(tmp_path):
    target=tmp_path/"images/shot_001.png"; target.parent.mkdir(); target.write_bytes(b"old")
    item=plan().shots[0]; version=backup_current_version(tmp_path,item,target)
    assert version["seed"]==11 and version["prompt"]=="old prompt"
    assert (tmp_path/version["image_path"]).read_bytes()==b"old"


def test_restore_previous_swaps_only_selected_frame(tmp_path):
    store=ProjectStore(tmp_path); project=store.create("demo","script",10,"am_eric","x"); current=project/"images/shot_001.png"; current.write_bytes(b"new")
    previous=project/"images/versions/shot_001_v1.png"; previous.parent.mkdir(); previous.write_bytes(b"old")
    value=plan(); value.shots[0].image_versions=[{"version":1,"image_path":"images/versions/shot_001_v1.png","seed":7,"prompt":"previous prompt","approved":True}]; store.save_plan(project,value)
    Pipeline(project).restore_previous_shot("shot_001")
    restored=store.load_plan(project).shots[0]
    assert current.read_bytes()==b"old" and previous.read_bytes()==b"new"
    assert restored.seed==7 and restored.prompt=="previous prompt" and restored.approved


def test_update_only_rebuild_backs_up_final_and_reuses_existing_assets(tmp_path,monkeypatch):
    store=ProjectStore(tmp_path); project=store.create("demo","script",10,"am_eric","x"); store.save_plan(project,plan())
    (project/"render").mkdir(exist_ok=True); final=project/"render/final_video.mp4"; final.write_bytes(b"old video")
    (project/"audio").mkdir(exist_ok=True); (project/"audio/narration.wav").write_bytes(b"voice")
    (project/"subtitles").mkdir(exist_ok=True); (project/"subtitles/subtitles.ass").write_text("subs")
    calls=[]
    def fake_render(project_path,loaded_plan,narration,subtitles,*args,**kwargs):
        calls.append((loaded_plan.shots[0].image_path,narration,subtitles)); final.write_bytes(b"updated video"); return final,final
    monkeypatch.setattr("history_doodle.pipeline.render",fake_render)
    Pipeline(project).rebuild_final_video()
    assert len(calls)==1 and calls[0][0]=="images/shot_001.png"
    assert next((project/"render/backups").glob("final_video_*.mp4")).read_bytes()==b"old video"
    assert final.read_bytes()==b"updated video"
