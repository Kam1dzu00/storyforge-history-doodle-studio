from __future__ import annotations

import json
import sys
from pathlib import Path

from history_doodle.schemas import ProjectState
from history_doodle.storage import ProjectStore
from history_doodle.style_system import PromptComposer


PROJECT=Path("projects/youve-been-lied-to-about-getting-sick")
CORRECTIONS={
    "shot_002":"three confident adults gesturing around one confused sick adult, advice represented only by floating coat thermometer and germ icons, no devices, screens, bubbles, panels, papers, or written marks",
    "shot_004":"colorful cartoon germs fleeing from a giant bright cleaning beam that sweeps diagonally across a laboratory, clean open upper area, no card, sign, banner, panel, or writing",
    "shot_005":"one simple half-body adult shivering without a jacket at an open doorway with snow outside, large cold breath and strong warm-cool contrast, no signs, bubbles, panels, or writing",
    "shot_007":"one cohesive crowded indoor room in winter, a bright sneeze cloud carrying virus icons between people while snow is visible outside, simple poses and no bubbles, panels, beams, signs, or writing",
    "shot_010":"one single blue bacterium being visibly crushed by one enormous antibiotic capsule, centered impact action against a plain cyan gradient background, no virus, people, secondary scene, split screen, panels, captions, labels, banners, boxes, marks, or writing",
    "shot_019":"glowing human torso silhouette surrounded by a red-orange heat aura, sweating germs retreat while blue immune cells become energized, no charts, panels, labels, arrows, or writing",
    "shot_021":"one giant thermometer, one plain analog clock face without numbers, and one worried face icon floating as three clean dimensional symbols against an abstract deep navy gradient, no room, counter, screen, board, checklist, labels, numbers, marks, or writing",
    "shot_022":"comically green tissue emerging dramatically from a completely plain unlabeled tissue box, bold closeup with no packaging marks, signs, words, numbers, or writing",
    "shot_024":"one giant green mucus drop under a magnifying glass, beside a plain analog clock without numbers and a simple red cheek-pain silhouette, abstract clean background, no people, arrows, papers, speech bubbles, boards, labels, marks, or writing",
    "shot_025":"an anthropomorphic tissue wearing toy doctor glasses and a stethoscope being stopped by a large red no-entry symbol, no badge, card, paper, packaging, labels, or writing",
    "shot_029":"one patient moving through a single clean clinic environment from a bed in foreground toward a calm doctor and then a glowing emergency light in the distance, no forms, desks, signs, bubbles, panels, or writing",
    "shot_030":"a completely plain unlabeled antibiotic bottle used like the wrong tool beside a giant virus, scattered capsules and chaotic motion accents, no toolbox board, package label, sign, words, or writing",
    "shot_037":"warm triumphant montage of thermometer, virus, orange, tissue and shield icons being untangled by one bright ribbon, clean blank space on the right, no book, phone, card, banner, labels, or writing"
}


def main():
    store=ProjectStore(); state=ProjectState.model_validate_json((PROJECT/"project.json").read_text()); plan=store.load_plan(PROJECT); composer=PromptComposer()
    selected=set(sys.argv[1:]) or set(CORRECTIONS)
    for shot in plan.shots:
        if shot.id not in selected: continue
        focus=CORRECTIONS[shot.id]; shot.visual_focus=shot.visual_subject=shot.action=shot.action_description=focus
        shot.labels=[]; shot.seed=(shot.seed+104729)%2147483647; shot.routing_source="manual"
        shot.prompt,shot.negative_prompt,_=composer.compose(state,shot); shot.prompt_hash=None; shot.status="stale"; shot.approved=False
    store.save_plan(PROJECT,plan)
    log={"regenerated_shots":list(CORRECTIONS),"reason":"visible AI pseudo-text in initial QA","strategy":"single-shot regeneration with simplified no-text compositions and new seeds"}
    (PROJECT/"logs/regenerated_shots.json").write_text(json.dumps(log,indent=2),encoding="utf-8")
    print(" ".join(x for x in CORRECTIONS if x in selected))


if __name__=="__main__":main()
