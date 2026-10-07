from __future__ import annotations

import json, os, resource, shutil, subprocess, sys, time
from copy import deepcopy
from pathlib import Path
from .audio import TimestampEngine, VoiceEngine, audio_duration, quality_report
from .config import DEFAULT_VOICE, ROOT, ensure_dirs
from .planner import LocalPlanner, extract_production_script, strip_director_tags
from .render import render
from .schemas import ProjectState, WordStamp
from .storage import ProjectStore
from .subtitles import build as build_subtitles
from .timing import allocate_timeline
from .util import run

class Pipeline:
    def __init__(self, project: Path, event=lambda *_: None):
        ensure_dirs(); self.project = project; self.event = event; self.store = ProjectStore(); self.state = self.store.load_state(project); self.cancel_requested=False; self.metrics={}

    def cancel(self): self.cancel_requested=True
    def _check_cancel(self):
        if self.cancel_requested: raise RuntimeError("Операция отменена. Готовые материалы сохранены; проект можно продолжить позже.")

    def _save(self): self.store.save_state(self.project, self.state)
    def _merge_metrics(self):
        benchmark=self.project/"logs/long_form_benchmark.json"; combined={}
        if benchmark.exists():
            try: combined=json.loads(benchmark.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError): combined={}
        combined.update(self.metrics)
        benchmark.write_text(json.dumps(combined,indent=2),encoding="utf-8")

    def create_script(self):
        self._check_cancel()
        if self.state.input_mode == "script":
            self.state.script_status = "complete"; self._save(); return (self.project/"script.txt").read_text()
        brief = (self.project/"brief.txt").read_text(encoding="utf-8"); self.event("Создаю английский сценарий…")
        script = LocalPlanner().create_script(brief, self.state.target_duration_seconds)
        (self.project/"script.txt").write_text(script, encoding="utf-8"); self.state.script_status="complete"; self._save(); return script

    def plan_video(self):
        started=time.time()
        self._check_cancel()
        script = (self.project/"script.txt").read_text(encoding="utf-8"); self.event("Разбиваю историю на разделы, сцены и кадры…")
        plan = LocalPlanner().plan(script, self.state.target_duration_seconds, self.state.base_seed)
        self.store.save_plan(self.project, plan); self.state.planning_status="complete"; self.state.images_status="stale"; self.state.subtitles_status="stale"; self.state.render_status="stale"; self._save()
        self.metrics["planning_seconds"]=round(time.time()-started,2); return plan

    def generate_voice(self):
        self._check_cancel()
        script = strip_director_tags(extract_production_script((self.project/"script.txt").read_text(encoding="utf-8"))); self.event("Создаю английскую озвучку…")
        started=time.time()
        segment_map = self.project / "voice_segments.json"
        if segment_map.exists():
            segments = json.loads(segment_map.read_text(encoding="utf-8"))
            segment_text = "\n\n".join(str(x["text"]).strip() for x in segments).strip()
            if " ".join(segment_text.split()) != " ".join(script.split()):
                raise ValueError("Voice segment text does not exactly match locked narration")
            wav = VoiceEngine().generate_segments(segments, self.project/"audio", self.state.voice, lambda i,n:self.event(f"Озвучиваю фрагмент {i} из {n}…"))
        else:
            wav = VoiceEngine().generate(script, self.project/"audio", self.state.voice, lambda i,n:self.event(f"Озвучиваю фрагмент {i} из {n}…"))
        self.metrics["voice_generation_seconds"]=round(time.time()-started,2)
        self.state.voice_status="complete"; self._save(); self.event("Синхронизирую слова с аудио…")
        started=time.time()
        TimestampEngine().transcribe(wav, self.project/"audio/word_timestamps.json")
        self.metrics["whisper_alignment_seconds"]=round(time.time()-started,2)
        (self.project/"audio/quality_report.json").write_text(json.dumps(quality_report(wav),indent=2),encoding="utf-8")
        plan = self.store.load_plan(self.project)
        voice_timeline = self.project / "audio/voice_timeline.json"
        if voice_timeline.exists():
            timeline = json.loads(voice_timeline.read_text(encoding="utf-8"))
            ordered_scenes = sorted(plan.scenes, key=lambda x: x.order)
            ordered_shots = sorted(plan.shots, key=lambda x: x.order)
            if len(timeline) != len(ordered_scenes) or len(timeline) != len(ordered_shots):
                raise ValueError("Voice timeline does not match the planned shot count")
            final_duration = audio_duration(wav)
            for index, (scene, shot, timing) in enumerate(zip(ordered_scenes, ordered_shots, timeline)):
                scene.start_time = shot.start_time = float(timing["start"])
                end = final_duration if index + 1 == len(timeline) else float(timing["end"])
                scene.end_time = shot.end_time = end
        else:
            plan = allocate_timeline(plan, audio_duration(wav))
        self.store.save_plan(self.project, plan); return wav

    def generate_images(self, only: str|None=None, new_seed=False):
        self._check_cancel()
        started=time.time()
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
            if self.cancel_requested:
                process.terminate(); process.wait(); raise RuntimeError("Операция отменена после сохранения текущего кадра. Проект можно продолжить позже.")
        if process.wait(): raise RuntimeError("FLUX image stage failed. See logs/app.log")
        self.metrics["image_stage_seconds"]=round(time.time()-started,2)
        plan=self.store.load_plan(self.project)
        self.state.images_status="complete" if all(x.status=="complete" for x in plan.shots) else "stale"
        self._save()

    def build_subtitles(self):
        words = [WordStamp.model_validate(x) for x in json.loads((self.project/"audio/word_timestamps.json").read_text())]
        result=build_subtitles(words,self.project/"subtitles",self.state.output_width,self.state.output_height); self.state.subtitles_status="complete"; self._save(); return result

    def render_video(self):
        started=time.time()
        self.event("Собираю готовое видео…"); plan=self.store.load_plan(self.project)
        result=render(self.project,plan,self.project/"audio/narration.wav",self.project/"subtitles/subtitles.ass",None,lambda i,n:self.event(f"Обрабатываю кадр {i} из {n}…"),self.state.output_width,self.state.output_height)
        if self.state.background_music_enabled or self.state.background_music:
            from .mastering import master_background_music
            self.event("Добавляю фоновую атмосферу без повторного кодирования видео…")
            master_background_music(self.project, self.state)
        self.metrics["render_seconds"]=round(time.time()-started,2); self._merge_metrics()
        self.state.render_status="complete"; self._save(); return result

    def preview_scene(self, scene_id: str):
        plan=deepcopy(self.store.load_plan(self.project)); scene=next(x for x in plan.scenes if x.id==scene_id)
        start,end=scene.start_time,scene.end_time
        if start is None or end is None: raise RuntimeError("Сначала создайте озвучку и тайминг.")
        keep=set(scene.shot_ids); plan.shots=[x for x in plan.shots if x.id in keep]; plan.scenes=[scene]; plan.sections=[]
        for shot in plan.shots:
            shot.start_time-=start; shot.end_time-=start
            if shot.image_path: shot.image_path=str((self.project/shot.image_path).resolve())
        scene.start_time=0; scene.end_time=end-start
        preview=self.project/"render/preview"; preview.mkdir(parents=True,exist_ok=True)
        audio=preview/"narration.wav"
        run(["ffmpeg","-y","-ss",str(start),"-to",str(end),"-i",str(self.project/"audio/narration.wav"),str(audio)])
        words=[WordStamp.model_validate(x) for x in json.loads((self.project/"audio/word_timestamps.json").read_text()) if x["end"]>=start and x["start"]<=end]
        for word in words: word.start=max(0,word.start-start); word.end=min(end-start,word.end-start)
        _,ass=build_subtitles(words,preview,self.state.output_width,self.state.output_height)
        _,final=render(preview,plan,audio,ass,None,lambda i,n:self.event(f"Собираю превью {i} из {n}…"),self.state.output_width,self.state.output_height)
        return final

    def full(self):
        free=shutil.disk_usage(self.project).free
        if free < 15*1024**3: raise RuntimeError(f"Недостаточно свободного места: {free/1024**3:.1f} ГБ. Нужно минимум 15 ГБ.")
        guard=subprocess.Popen(["caffeinate","-dimsu","-w",str(os.getpid())]) if shutil.which("caffeinate") else None
        started=time.time(); did_work=any(getattr(self.state,f"{key}_status")!="complete" for key in ("script","planning","voice","images","subtitles","render"))
        try:
            if self.state.script_status != "complete": self.create_script()
            self._check_cancel()
            if self.state.planning_status != "complete": self.plan_video()
            self._check_cancel()
            if self.state.voice_status != "complete": self.generate_voice()
            self._check_cancel()
            if self.state.images_status != "complete": self.generate_images()
            self._check_cancel()
            if self.state.subtitles_status != "complete": self.build_subtitles()
            self._check_cancel()
            if self.state.render_status != "complete": self.render_video()
            self.event("ВИДЕО ГОТОВО")
        finally:
            if guard and guard.poll() is None: guard.terminate()
            if did_work: self.metrics["total_duration_seconds"]=round(time.time()-started,2)
            else: self.metrics["resume_check_seconds"]=round(time.time()-started,2)
            if did_work:
                divisor=1024**2 if sys.platform=="darwin" else 1024
                self.metrics["peak_memory_mb_self"]=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/divisor,1)
                self.metrics["peak_memory_mb_children"]=round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/divisor,1)
            (self.project/"logs/pipeline_metrics.json").write_text(json.dumps(self.metrics,indent=2),encoding="utf-8")
            self._merge_metrics()
