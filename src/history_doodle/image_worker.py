from __future__ import annotations

import argparse, json, sys
from pathlib import Path
from .config import STYLE_REFERENCE, configure_model_cache
from .schemas import ProjectPlan
from .storage import ProjectStore
from .util import prompt_hash

def generate(project: Path, only: str | None = None, new_seed: bool = False) -> None:
    configure_model_cache()
    from mflux.models.common.config import ModelConfig
    from mflux.models.flux2.variants import Flux2Klein, Flux2KleinEdit
    store = ProjectStore(); plan = store.load_plan(project)
    use_reference = STYLE_REFERENCE.exists()
    cls = Flux2KleinEdit if use_reference else Flux2Klein
    model = cls(quantize=4, model_config=ModelConfig.flux2_klein_4b())
    shots = sorted(plan.shots, key=lambda s: s.order)
    if only: shots = [s for s in shots if s.id == only]
    for index, shot in enumerate(shots, 1):
        digest = prompt_hash(shot.prompt, shot.negative_prompt)
        target = project / "images" / f"shot_{shot.order:03d}.png"
        if not new_seed and shot.status == "complete" and target.exists() and shot.prompt_hash == digest:
            print(json.dumps({"event":"skip", "index":index, "total":len(shots), "shot":shot.id}), flush=True); continue
        if new_seed: shot.seed = (shot.seed + 7919) % 2_147_483_647
        shot.status = "generating"; store.save_plan(project, plan)
        prompt = f"{shot.prompt}. Avoid: {shot.negative_prompt}."
        error = None
        for attempt in range(3):
            try:
                if attempt == 2:
                    prompt = f"{shot.visual_subject} in {shot.location}, {shot.action}, {shot.composition}. simple hand-drawn 2D history doodle, flat muted earthy colors, thick imperfect dark outlines, single coherent 16:9 illustration, no text, no collage."
                kwargs = dict(seed=shot.seed + attempt, prompt=prompt, num_inference_steps=4, height=576, width=1024, guidance=1.0)
                if use_reference: kwargs["image_paths"] = [str(STYLE_REFERENCE)]; kwargs["image_strength"] = 0.35
                result = model.generate_image(**kwargs); result.save(target, overwrite=True)
                shot.image_path = str(target.relative_to(project)); shot.prompt_hash = digest; shot.status = "complete"; error = None; break
            except Exception as exc:
                error = exc; shot.seed = (shot.seed + 1009) % 2_147_483_647
        if error:
            shot.status = "failed"; store.save_plan(project, plan); print(json.dumps({"event":"failed", "shot":shot.id, "error":str(error)}), flush=True); continue
        store.save_plan(project, plan)
        print(json.dumps({"event":"generated", "index":index, "total":len(shots), "shot":shot.id, "path":str(target)}), flush=True)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("project", type=Path); parser.add_argument("--only"); parser.add_argument("--new-seed", action="store_true")
    args = parser.parse_args(); generate(args.project, args.only, args.new_seed)

if __name__ == "__main__": main()

