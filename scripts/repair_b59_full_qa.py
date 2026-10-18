#!/usr/bin/env python3
"""Sequentially regenerate the B-59 frames rejected during visual QA."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path("projects/the-soviet-submarine-that-almost-started-world-war-iii-clean-editorial")
STORY = PROJECT / "planning/story.json"
LOG = PROJECT / "logs/regenerated_shots.json"

VISUALS = {
    "shot_003": "claustrophobic submarine machinery corridor under oppressive heat, condensation on unmarked steel pipes, one empty folded cloth on a valve wheel",
    "shot_008": "high overhead view of an unmarked Cold War destroyer silhouette cutting through dark Atlantic water, sonar ripples beneath the hull",
    "shot_014": "underwater pressure waves and pale concussion rings surrounding a submerged diesel submarine silhouette in deep navy water",
    "shot_015": "dark ocean cross-section with an unaware surface ship far above and a hidden submarine silhouette far below",
    "shot_019": "single smooth unmarked torpedo silhouette secured inside a shadowed submarine weapons bay, ominous pale-cyan rim light",
    "shot_038": "top-down maritime quarantine zone shown only through ships, wakes, and a circular patrol formation, no map symbols or writing",
    "shot_046": "four unmarked diesel submarine silhouettes departing a cold northern harbor at dusk, seen from a distant elevated viewpoint",
    "shot_047": "four distinct unmarked Foxtrot-class submarine silhouettes moving in formation through rough gray water",
    "shot_049": "orderly rack of smooth unmarked torpedoes inside a submarine compartment, repeating cylindrical forms fading into shadow",
    "shot_066": "wide Atlantic patrol scene with several unmarked destroyer silhouettes sweeping the sea around a distant island coastline",
    "shot_083": "submarine engine-room thermometer represented only by a glowing red mercury column without scale or markings, heat haze and sweating steel pipes",
    "shot_097": "single submerged submarine silhouette slipping through a dark gap between distant searchlight cones, no surface markings",
    "shot_131": "tense submarine command compartment with one adult officer silhouette facing a blank instrument panel, hands fully out of frame",
    "shot_134": "one adult officer silhouette standing calmly between a closed torpedo-room hatch and an unmarked control console, hands out of frame",
    "shot_146": "closed unmarked torpedo tube door lit by a narrow red warning glow inside a dark submarine compartment",
    "shot_147": "three adult officer silhouettes separated by pools of dim light in a cramped command compartment, hands out of frame",
    "shot_157": "blank sonar scope glowing pale cyan in a dark command room, one cropped observer silhouette, all controls abstract and unmarked",
    "shot_213": "messy convergence of opposing ship wakes and submarine sonar rings in a dark ocean, an abstract systems-risk metaphor",
    "shot_239": "calm dawn breaking over an empty Atlantic horizon after a storm, one distant unmarked submarine silhouette surfacing into pale light",
    "shot_250": "three ambiguous signal waves converging around a submerged unmarked submarine silhouette, restrained editorial risk metaphor",
}

BASE = (
    "FULL-SCREEN 16:9 CLEAN EDITORIAL DOCUMENTARY KEYFRAME. Mature hand-drawn "
    "editorial illustration, clean dark-ink linework with varied weight, soft cel "
    "shading, subtle paper-gouache texture, restrained warm cream, muted navy, "
    "dusty blue and charcoal palette with one signal-red or pale-cyan accent. "
    "One dominant focal point, generous negative space, historically plausible "
    "October 1962 Cold War atmosphere. EXACT VISUAL IDEA: {idea}. All visible "
    "surfaces are completely blank and smooth. ZERO writing, ZERO letters, ZERO "
    "numbers, ZERO labels, ZERO flags, ZERO insignia, ZERO speech bubbles, ZERO "
    "captions, ZERO diagrams. No watermark, no collage, no split screen, no "
    "childlike clip-art, no glossy 3D, no photorealism. One coherent scene."
)

NEGATIVE = (
    "text, typography, letters, words, numbers, labels, logo, watermark, pseudo-text, "
    "gibberish, ship name, hull number, flag, insignia, speech bubble, caption, map text, "
    "diagram text, childlike clip-art, glossy 3D, photorealism, anime, comic overload, "
    "extra limbs, extra hands, malformed fingers, duplicated faces, crowded scene"
)


def main() -> int:
    data = json.loads(STORY.read_text())
    by_id = {shot["id"]: shot for shot in data["shots"]}
    for shot_id, idea in VISUALS.items():
        shot = by_id[shot_id]
        shot["prompt"] = BASE.format(idea=idea)
        shot["negative_prompt"] = NEGATIVE
        shot["status"] = "pending"
        shot["approved"] = False
    STORY.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    existing = []
    if LOG.exists():
        loaded = json.loads(LOG.read_text())
        existing = loaded if isinstance(loaded, list) else loaded.get("regenerations", [])
    seen = {(item.get("shot_id"), item.get("reason")) for item in existing}

    for shot_id in VISUALS:
        print(f"Regenerating {shot_id}", flush=True)
        subprocess.run(
            [sys.executable, "-m", "history_doodle.image_worker", str(PROJECT), "--only", shot_id, "--new-seed"],
            check=True,
        )
        key = (shot_id, "visual QA: generated text or markings")
        if key not in seen:
            existing.append(
                {
                    "shot_id": shot_id,
                    "reason": key[1],
                    "strategy": "text-free object/environment or silhouette",
                    "regenerated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            seen.add(key)
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
