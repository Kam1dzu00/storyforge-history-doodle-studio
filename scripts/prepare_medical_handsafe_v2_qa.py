from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from history_doodle.config import ROOT
from history_doodle.storage import ProjectStore
from history_doodle.style_system import PromptComposer
from history_doodle.util import prompt_hash


PROJECT = Path("projects/youve-been-lied-to-about-getting-sick-handsafe-v2")
CORRECTIONS = {
    "shot_001": "one glass thermometer surrounded by several playful virus particles against a clean cyan background, objects only",
    "shot_002": "an old rotary telephone, vintage radio, winter coat, and colorful germ shapes caught in one swirling vortex, isolated objects only",
    "shot_004": "one enormous red eraser colliding with three dark germ shapes in a burst of clean motion lines, isolated objects only",
    "shot_006": "cold blue snowflake on the left and a large red virus on the right, one bold arrow points only toward the virus, objects only",
    "shot_007": "snow outside a window, tightly clustered chairs indoors, and virus particles passing between the chairs, visual chain made only from objects",
    "shot_009": "one completely plain amber antibiotic bottle with a white cap against a radiant cyan background, no printed surface",
    "shot_010": "two distinct microscope organisms: one blue rod-shaped bacterium stopped by an antibiotic capsule, one red spiked virus completely unaffected, objects only",
    "shot_012": "a balance scale carrying a stomach warning symbol on one pan and shielded resistant bacteria on the other, objects only",
    "shot_013": "one vivid orange and three plain vitamin tablets exploding from a yellow sunburst, isolated objects only",
    "shot_015": "two plain calendars without numbers, the second only slightly smaller, beside an orange with a tiny crossed-out cape, objects only",
    "shot_017": "one glass thermometer surrounded by a controlled orange heat aura, isolated object only",
    "shot_018": "a simple faceless torso-shaped medical icon with all limbs omitted, glowing immune shield surrounding germs inside it",
    "shot_019": "several germs sweating and retreating from a bright red-orange heat field while blue immune shield symbols advance, objects only",
    "shot_020": "three clean safety symbols: a swaddled baby icon, immune shield icon, and medical cross icon beneath one caution triangle, objects only",
    "shot_021": "one thermometer, one plain circular clock with no markings, and three colored symptom dots arranged cleanly, objects only",
    "shot_022": "one plain unmarked tissue box with a comically green tissue emerging, isolated object closeup",
    "shot_023": "a clean cutaway sinus model with yellow and green mucus beside two plain tissues, anatomical object model only",
    "shot_024": "one green mucus drop beneath a magnifying glass resting flat on a tabletop beside three colored severity dots, isolated objects only",
    "shot_026": "water glass, bed pillow, soap bar, vaccine shield, and medical cross arranged radially around a bright empty center, isolated objects only",
    "shot_027": "one enormous virus icon beside one much smaller bacterium icon, clean proportional comparison, objects only",
    "shot_028": "bed pillow, water glass, thermometer, medicine cup, soup bowl, and folded blanket arranged in one clean row, objects only",
    "shot_029": "three tabletop miniature models in a row: bed with water, small clinic building, and glowing warning triangle, isolated objects only",
    "shot_030": "a plain antibiotic capsule used as the obviously wrong tool against a huge virus beside a simple toolbox, objects only",
    "shot_031": "soap bubbles washing germs away, vaccine shield blocking a virus, mask icon covering a cough cloud, and a closed home door, objects only",
    "shot_032": "one overly simple straight blue line colliding with a tangled cluster of colorful cords, abstract objects only",
    "shot_033": "a tangled bundle of colored cords transforming into four clean parallel colored lines, objects only",
    "shot_034": "virus, thermometer, clock, tissue, water glass, and immune shield connected by clean colored lines, objects only",
    "shot_037": "thermometer, virus, orange, tissue, and shield icons untangled into a calm balanced arrangement, objects only",
}


def main() -> None:
    store = ProjectStore()
    state = store.load_state(PROJECT)
    plan = store.load_plan(PROJECT)
    composer = PromptComposer()
    selected = set(sys.argv[1:]) or set(CORRECTIONS)
    regenerated = []
    for shot in plan.shots:
        if shot.id not in selected:
            continue
        focus = CORRECTIONS[shot.id]
        shot.visual_focus = shot.visual_subject = shot.action = shot.action_description = focus
        shot.people_count = 0
        shot.host_present = False
        shot.labels = []
        shot.composition = "one clean full-screen object composition with no panels or inset scenes"
        shot.foreground_elements = ["one large relevant object"]
        shot.midground_elements = [focus]
        shot.background_elements = ["clean abstract cyan gradient with no room details"]
        shot.environment_context = "abstract bright medical explainer background, objects only"
        shot.seed = (shot.seed + 104729) % 2_147_483_647
        shot.routing_source = "manual"
        shot.prompt, shot.negative_prompt, _ = composer.compose(state, shot)
        shot.prompt_hash = None
        shot.status = "stale"
        shot.approved = False
        regenerated.append(shot.id)

    # Restore deterministic frames that the first full-run prompt recompose invalidated.
    black = PROJECT / "images/shot_038.png"
    from PIL import Image
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(black)
    outro = PROJECT / "images/shot_039.png"
    shutil.copy2(ROOT / "assets/channel/channel_outro_static.png", outro)
    for order, path in ((38, black), (39, outro)):
        shot = next(x for x in plan.shots if x.order == order)
        shot.prompt, shot.negative_prompt, _ = composer.compose(state, shot)
        shot.prompt_hash = prompt_hash(shot.prompt, shot.negative_prompt)
        shot.image_path = str(path.relative_to(PROJECT))
        shot.status = "complete"
        shot.approved = True

    store.save_plan(PROJECT, plan)
    log_path = PROJECT / "logs/regenerated_shots.json"
    previous = []
    if log_path.exists():
        previous = json.loads(log_path.read_text(encoding="utf-8")).get("regenerated_shots", [])
    unique = list(dict.fromkeys(previous + regenerated))
    log = {
        "regenerated_shots": unique,
        "reason": "manual QA: pseudo-text, people/hands, or insufficiently literal object-first composition",
        "strategy": "single-shot regeneration with simplified object-only text-free prompts and new seeds",
    }
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(" ".join(regenerated))


if __name__ == "__main__":
    main()
