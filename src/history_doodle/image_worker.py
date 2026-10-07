from __future__ import annotations

import argparse, json, sys, time
from pathlib import Path
from .config import STYLE_REFERENCE, configure_model_cache
from .schemas import ProjectPlan
from .storage import ProjectStore
from .util import prompt_hash
from .util import cleanup_models
from .style_system import HostReferenceConditioningUnsupported, LEGACY_STYLE_ID, PromptComposer

HOST_REFERENCE_CONDITIONING_SUPPORTED = False

def generate(project: Path, only: str | None = None, new_seed: bool = False) -> None:
    configure_model_cache()
    store = ProjectStore(); plan = store.load_plan(project); state = store.load_state(project)
    legacy = not state.style_mode or state.style_mode == LEGACY_STYLE_ID
    use_reference = legacy and STYLE_REFERENCE.exists()
    composer = PromptComposer()
    model = None; model_is_edit = None
    shots = sorted(plan.shots, key=lambda s: s.order)
    if only: shots = [s for s in shots if s.id == only]
    elif not legacy:
        # Keep model memory sequential: base-model object/diagram shots first,
        # then host reference-edit shots, while preserving order in each group.
        shots = [s for s in shots if not s.host_present] + [s for s in shots if s.host_present]
    if not legacy and any(s.host_present for s in shots) and not HOST_REFERENCE_CONDITIONING_SUPPORTED:
        raise HostReferenceConditioningUnsupported(
            "HOST_IMAGE_REFERENCE_CONDITIONING_UNSUPPORTED: the current image backend cannot accept "
            "real/stylized host image references as conditioning; the host consistency test cannot run."
        )
    from mflux.models.common.config import ModelConfig
    from mflux.models.flux2.variants import Flux2Klein, Flux2KleinEdit
    timings=[]; stage_started=time.time()
    for index, shot in enumerate(shots, 1):
        shot_started=time.time()
        references = [STYLE_REFERENCE] if use_reference else []
        if not legacy:
            positive, negative, references = composer.compose(state, shot, require_references=True)
            shot.prompt, shot.negative_prompt = positive, negative
        digest = prompt_hash(shot.prompt, shot.negative_prompt)
        target = project / "images" / f"shot_{shot.order:03d}.png"
        # A selected-shot request is an explicit regeneration. Full episode runs
        # still resume by skipping already valid files.
        if only is None and not new_seed and shot.status == "complete" and target.exists() and shot.prompt_hash == digest:
            print(json.dumps({"event":"skip", "index":index, "total":len(shots), "shot":shot.id}), flush=True); continue
        if new_seed: shot.seed = (shot.seed + 7919) % 2_147_483_647
        shot.status = "generating"; store.save_plan(project, plan)
        wants_edit = bool(references)
        if model is None or model_is_edit != wants_edit:
            if model is not None:
                del model
                cleanup_models()
            cls = Flux2KleinEdit if wants_edit else Flux2Klein
            model = cls(quantize=4, model_config=ModelConfig.flux2_klein_4b())
            model_is_edit = wants_edit
        prompt = f"{shot.prompt}. Avoid: {shot.negative_prompt}."
        error = None
        for attempt in range(3):
            try:
                if attempt == 2:
                    prompt = f"{shot.prompt}. Simplify minor background detail but preserve every locked style and character constraint."
                vertical = state.output_height > state.output_width
                kwargs = dict(
                    seed=shot.seed + attempt,
                    prompt=prompt,
                    num_inference_steps=4,
                    height=1024 if vertical else 576,
                    width=576 if vertical else 1024,
                    guidance=1.0,
                )
                if references:
                    kwargs["image_paths"] = [str(x) for x in references]
                    kwargs["image_strength"] = 0.35
                result = model.generate_image(**kwargs); result.save(target, overwrite=True)
                shot.image_path = str(target.relative_to(project)); shot.prompt_hash = digest; shot.status = "complete"; error = None; break
            except Exception as exc:
                error = exc; shot.seed = (shot.seed + 1009) % 2_147_483_647
        if error:
            shot.status = "failed"; store.save_plan(project, plan); print(json.dumps({"event":"failed", "shot":shot.id, "error":str(error)}), flush=True); continue
        store.save_plan(project, plan)
        audit = {
            "shot_id": shot.id, "style_id": state.style_mode or LEGACY_STYLE_ID,
            "visual_category": shot.visual_category, "host_present": bool(shot.host_present),
            "routing_source": shot.routing_source, "references_passed": [str(x) for x in references],
            "prompt_hash": digest, "seed": shot.seed,
        }
        audit_path=project/"logs/image_generation.jsonl"; audit_path.parent.mkdir(parents=True,exist_ok=True)
        with audit_path.open("a",encoding="utf-8") as handle: handle.write(json.dumps(audit,ensure_ascii=False)+"\n")
        timings.append(round(time.time()-shot_started,2))
        print(json.dumps({"event":"generated", "index":index, "total":len(shots), "shot":shot.id, "path":str(target)}), flush=True)
    metrics_path=project/"logs/long_form_benchmark.json"; metrics={}
    if metrics_path.exists():
        try: metrics=json.loads(metrics_path.read_text())
        except Exception: metrics={}
    if timings and only is None:
        metrics.update({"generated_images":len(timings),"average_image_generation_seconds":round(sum(timings)/len(timings),2),"total_image_generation_seconds":round(time.time()-stage_started,2)})
    elif timings:
        metrics["last_manual_regeneration_seconds"]=round(sum(timings),2)
    else:
        metrics["resume_scan_seconds"]=round(time.time()-stage_started,2)
    metrics_path.write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    if model is not None: del model
    cleanup_models()

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("project", type=Path); parser.add_argument("--only"); parser.add_argument("--new-seed", action="store_true")
    args = parser.parse_args(); generate(args.project, args.only, args.new_seed)

if __name__ == "__main__": main()
