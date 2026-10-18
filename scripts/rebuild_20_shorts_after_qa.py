from __future__ import annotations

import json
import traceback
from pathlib import Path

from history_doodle.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "projects/shorts-mega-pack-v1-batch"
STATUS = BATCH / "logs/qa_rebuild_status.json"


def save(data: dict) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    projects = [Path(item) for item in json.loads((BATCH / "projects.json").read_text(encoding="utf-8"))]
    data = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {"projects": {}}
    for project in projects:
        name = project.name
        if data["projects"].get(name, {}).get("status") == "complete":
            continue
        data["projects"][name] = {"status": "running"}; save(data)
        try:
            result = Pipeline(project, print).rebuild_final_video()
            data["projects"][name] = {"status": "complete", "final": str(result)}
        except Exception as exc:
            data["projects"][name] = {"status": "failed", "error": str(exc), "traceback": traceback.format_exc()}
            save(data)
            raise
        save(data)


if __name__ == "__main__":
    main()
