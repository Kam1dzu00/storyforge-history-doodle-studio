from __future__ import annotations

import json
import traceback
from pathlib import Path

from history_doodle.pipeline import Pipeline


BATCH=Path("projects/shorts-mega-pack-v1-batch")


def main() -> None:
    projects=[Path(x) for x in json.loads((BATCH/"projects.json").read_text(encoding="utf-8"))]
    status_path=BATCH/"logs/batch_status.json"
    status={"projects":{},"complete":0,"failed":0}
    if status_path.exists(): status=json.loads(status_path.read_text(encoding="utf-8"))
    for index,project in enumerate(projects,1):
        try:
            print(f"BATCH_START {index}/20 {project}",flush=True)
            Pipeline(project,event=lambda msg,p=project:print(f"{p.name}: {msg}",flush=True)).full()
            status["projects"][project.name]={"status":"complete"}; print(f"BATCH_DONE {index}/20 {project}",flush=True)
        except Exception as exc:
            status["projects"][project.name]={"status":"failed","error":str(exc),"traceback":traceback.format_exc()}; print(f"BATCH_FAILED {index}/20 {project}: {exc}",flush=True)
        status["complete"]=sum(x.get("status")=="complete" for x in status["projects"].values()); status["failed"]=sum(x.get("status")=="failed" for x in status["projects"].values())
        status_path.write_text(json.dumps(status,indent=2),encoding="utf-8")
    if status["failed"]: raise RuntimeError(f"Batch finished with {status['failed']} failed projects; inspect {status_path}")


if __name__=="__main__": main()
