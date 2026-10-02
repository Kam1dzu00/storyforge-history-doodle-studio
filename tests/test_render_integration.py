from pathlib import Path
from PIL import Image
from history_doodle.render import _motion_filter, probe, render
from history_doodle.schemas import ProjectPlan, Scene, Shot, StorySection
from history_doodle.subtitles import build
from history_doodle.schemas import WordStamp
from history_doodle.util import run

def test_pan_filters_use_crop_frame_counter():
    assert "1-n/" in _motion_filter("pan_left",120)
    assert "96*n/" in _motion_filter("pan_right",120)

def test_real_ffmpeg_render(tmp_path):
    for rel in ("images","audio","subtitles","render/temp"):(tmp_path/rel).mkdir(parents=True,exist_ok=True)
    Image.new("RGB",(1024,576),(210,180,120)).save(tmp_path/"images/shot_001.png")
    Image.new("RGB",(1024,576),(100,130,150)).save(tmp_path/"images/shot_002.png")
    run(["ffmpeg","-y","-f","lavfi","-i","sine=frequency=220:sample_rate=48000","-t","6","-c:a","pcm_s16le",str(tmp_path/"audio/narration.wav")])
    _,ass=build([WordStamp(word="History",start=.1,end=.6),WordStamp(word="doodles.",start=.6,end=1.1)],tmp_path/"subtitles")
    shots=[]
    for i in (1,2): shots.append(Shot(id=f"s{i}",scene_id="scene",order=i,narration_context="x",visual_subject="x",location="x",action="x",composition="wide",camera_motion="static",prompt="x",negative_prompt="x",seed=i,estimated_duration=3,start_time=(i-1)*3,end_time=i*3,image_path=f"images/shot_{i:03d}.png",status="complete"))
    plan=ProjectPlan(sections=[StorySection(id="sec",title="x",purpose="x",scene_ids=["scene"])],scenes=[Scene(id="scene",section_id="sec",order=1,narration_text="x",shot_ids=["s1","s2"],start_time=0,end_time=6)],shots=shots)
    _,final=render(tmp_path,plan,tmp_path/"audio/narration.wav",ass)
    info=probe(final); video=next(x for x in info["streams"] if x["codec_type"]=="video"); audio=next(x for x in info["streams"] if x["codec_type"]=="audio")
    assert (video["width"],video["height"],video["codec_name"])==(1920,1080,"h264")
    assert audio["codec_name"]=="aac"
