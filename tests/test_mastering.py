from pathlib import Path

import pytest

from history_doodle.mastering import generate_bright_facts_bed, generate_procedural_ambience, master_background_music, probe_duration
from history_doodle.render import probe
from history_doodle.schemas import ProjectState
from history_doodle.util import run


def state(**overrides):
    values = dict(project_id="x", title="x", input_mode="script")
    values.update(overrides)
    return ProjectState(**values)


def make_media(root: Path, duration=2.0):
    (root / "render").mkdir(parents=True)
    (root / "audio").mkdir()
    (root / "logs").mkdir()
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=30", "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(root / "render/final_video.mp4")])
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000", "-t", str(duration), "-ac", "2", "-c:a", "pcm_s24le", str(root / "audio/narration.wav")])


def test_music_defaults_disabled_and_legacy_projects_load():
    value = state()
    assert value.background_music_enabled is False
    assert value.background_music_mode == "procedural"


def test_procedural_music_duration_and_fades(tmp_path):
    out = generate_procedural_ambience(tmp_path / "music.wav", 2.0, .2, .4)
    assert probe_duration(out) == pytest.approx(2.0, abs=.03)
    info = probe(out); audio = next(x for x in info["streams"] if x["codec_type"] == "audio")
    assert audio["sample_rate"] == "48000" and audio["channels"] == 2


def test_bright_facts_profile_is_distinct_and_reported(tmp_path):
    out=generate_bright_facts_bed(tmp_path/"bright.wav",2.0,.2,.4)
    assert probe_duration(out)==pytest.approx(2.0,abs=.03)
    make_media(tmp_path/"project")
    master_background_music(tmp_path/"project",state(background_music_enabled=True,music_profile="BRIGHT_FACTS",background_music_fade_in=.2,background_music_fade_out=.4))
    import json
    report=json.loads((tmp_path/"project/logs/audio_mastering.json").read_text())
    assert report["profile"]=="BRIGHT_FACTS" and report["music_target_lufs"]==-23 and report["duck_release_ms"]==700


def test_music_master_preserves_original_and_copies_video(tmp_path):
    make_media(tmp_path)
    original = tmp_path / "render/final_video.mp4"
    no_music, final, generated = master_background_music(tmp_path, state(background_music_enabled=True))
    assert no_music.exists() and final.exists() and generated.exists()
    assert probe_duration(final) == pytest.approx(probe_duration(no_music), abs=.03)
    streams = probe(final)["streams"]
    video = next(x for x in streams if x["codec_type"] == "video")
    audio = next(x for x in streams if x["codec_type"] == "audio")
    assert video["codec_name"] == "h264"
    assert audio["codec_name"] == "aac" and audio["sample_rate"] == "48000"
    assert (tmp_path / "audio/final_mix.wav").exists()


def test_failed_mastering_does_not_destroy_original(tmp_path):
    make_media(tmp_path)
    original = (tmp_path / "render/final_video.mp4").read_bytes()
    with pytest.raises(FileNotFoundError):
        master_background_music(tmp_path, state(background_music_enabled=True, background_music_mode="user_file", background_music="missing.wav"))
    assert (tmp_path / "render/final_video.mp4").read_bytes() == original
    assert (tmp_path / "render/final_video_no_music.mp4").exists()
