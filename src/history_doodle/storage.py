from __future__ import annotations

import json, re
from datetime import datetime, timezone
from pathlib import Path
from .config import PROJECTS_DIR
from .schemas import ProjectPlan, ProjectState

def slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value[:64] or "history-project"

class ProjectStore:
    def __init__(self, root: Path = PROJECTS_DIR): self.root = root

    def create(self, title: str, input_mode: str, duration: int, voice: str, text: str) -> Path:
        base = slugify(title); path = self.root / base; index = 2
        while path.exists(): path = self.root / f"{base}-{index}"; index += 1
        for rel in ("planning", "audio/chunks", "images", "subtitles", "render/temp", "logs"):
            (path / rel).mkdir(parents=True, exist_ok=True)
        state = ProjectState(project_id=path.name, title=title, input_mode=input_mode, target_duration_seconds=duration, voice=voice)
        self.save_state(path, state)
        (path / ("brief.txt" if input_mode == "brief" else "script.txt")).write_text(text, encoding="utf-8")
        return path

    def save_state(self, path: Path, state: ProjectState) -> None:
        state.updated_at = datetime.now(timezone.utc).isoformat()
        self._atomic_json(path / "project.json", state.model_dump())

    def load_state(self, path: Path) -> ProjectState:
        return ProjectState.model_validate_json((path / "project.json").read_text(encoding="utf-8"))

    def save_plan(self, path: Path, plan: ProjectPlan) -> None:
        self._atomic_json(path / "planning/story.json", plan.model_dump())
        self._atomic_json(path / "planning/characters.json", [c.model_dump() for c in plan.characters])
        self._atomic_json(path / "planning/scene_manifest.json", {"scenes": [s.model_dump() for s in plan.scenes], "shots": [s.model_dump() for s in plan.shots]})

    def load_plan(self, path: Path) -> ProjectPlan:
        return ProjectPlan.model_validate_json((path / "planning/story.json").read_text(encoding="utf-8"))

    @staticmethod
    def _atomic_json(path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"); temp.replace(path)

