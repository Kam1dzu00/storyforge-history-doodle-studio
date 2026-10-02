from __future__ import annotations

import json, subprocess, sys
from pathlib import Path
from .audio import TimestampEngine, VoiceEngine, audio_duration
from .config import DEFAULT_VOICE, ROOT, ensure_dirs
from .planner import LocalPlanner
from .render import render
from .schemas import ProjectState, WordStamp
from .storage import ProjectStore
from .subtitles import build as build_subtitles
from .timing import allocate_timeline

class Pipeline:
    def __init__(self, project: Path, event=lambda *_: None):
        ensure_dirs(); self.project = project; self.event = event; self.store = ProjectStore(); self.state = self.store.load_state(project)

    def _save(self): self.store.save_state(self.project, self.state)

    def create_script(self):
        if self.state.input_mode == "script":
            self.state.script_status = "complete"; self._save(); return (self.project/"script.txt").read_text()
        brief = (self.project/"brief.txt").read_text(encoding="utf-8"); self.event("Создаю английский сценарий…")
        script = LocalPlanner().create_script(brief, self.state.target_duration_seconds)
        (self.project/"script.txt").write_text(script, encoding="utf-8"); self.state.script_status="complete"; self._save(); return script

    def plan_video(self):
        script = (self.project/"script.txt").read_text(encoding="utf-8"); self.event("Разбиваю историю на разделы, сцены и кадры…")
        plan = LocalPlanner().plan(script, self.state.target_duration_seconds, self.state.base_seed)
        self.store.save_plan(self.project, plan); self.state.planning_status="complete"; self.state.images_status="stale"; self.state.subtitles_status="stale"; self.state.render_status="stale"; self._save(); return plan

    def generate_voice(self):
        script = (self.project/"script.txt").read_text(encoding="utf-8"); self.event("Создаю английскую озвучку…")
        wav = VoiceEngine().generate(script, self.project/"audio", self.state.voice, lambda i,n:self.event(f"Озвучиваю фрагмент {i} из {n}…"))
        self.state.voice_status="complete"; self._save(); self.event("Синхронизирую слова с аудио…")
        TimestampEngine().transcribe(wav, self.project/"audio/word_timestamps.json")
        plan = allocate_timeline(self.store.load_plan(self.project), audio_duration(wav)); self.store.save_plan(self.project, plan); return wav

    def generate_images(self, only: str|None=None, new_seed=False):
        self.event("Загружаю модель иллюстраций FLUX.2…")
        cmd = [str(ROOT/".venv/bin/python"), "-m", "history_doodle.image_worker", str(self.project)]
        if only: cmd += ["--only", only]
        if new_seed: cmd += ["--new-seed"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert process.stdout
        for line in process.stdout:
            try:
                msg=json.loads(line); self.event(f"Создаю иллюстрацию {msg.get('index','')} из {msg.get('total','')}… {msg.get('shot','')}")
            except json.JSONDecodeError: pass
        if process.wait(): raise RuntimeError("FLUX image stage failed. See logs/app.log")
        self.state.images_status="complete"; self._save()

    def build_subtitles(self):
        words = [WordStamp.model_validate(x) for x in json.loads((self.project/"audio/word_timestamps.json").read_text())]
        result=build_subtitles(words,self.project/"subtitles"); self.state.subtitles_status="complete"; self._save(); return result

    def render_video(self):
        self.event("Собираю готовое видео…"); plan=self.store.load_plan(self.project); music=Path(self.state.background_music) if self.state.background_music else None
        result=render(self.project,plan,self.project/"audio/narration.wav",self.project/"subtitles/subtitles.ass",music,lambda i,n:self.event(f"Обрабатываю кадр {i} из {n}…"))
        self.state.render_status="complete"; self._save(); return result

    def full(self):
        if self.state.script_status != "complete": self.create_script()
        if self.state.planning_status != "complete": self.plan_video()
        if self.state.voice_status != "complete": self.generate_voice()
        if self.state.images_status != "complete": self.generate_images()
        if self.state.subtitles_status != "complete": self.build_subtitles()
        if self.state.render_status != "complete": self.render_video()
        self.event("ВИДЕО ГОТОВО")
