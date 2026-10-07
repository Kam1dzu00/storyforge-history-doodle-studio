from __future__ import annotations

import json
from pathlib import Path

from history_doodle.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
REPAIRS = {
    "rome-short-01-night": {
        1: "Ancient Roman street at night, looming insulae, torch bowls, dark windows, one wooden cart wheel entering foreground. No typography or signs.",
        2: "Dark ancient Roman alley with only small oil lamps, broken paving and two uneasy distant silhouettes. Absolutely no words or signs.",
        5: "Single cramped upper-floor Roman room, one adult commoner jolting awake in bed while wooden shutters and walls rattle from a cart below. No panels, no text.",
        9: "One adult Roman traveler in tunic and cloak hurrying through a narrow torchlit alley, anxious side glance, full body, no speech bubbles, no text.",
        10: "Dense block of historically plausible Roman insulae at night, one upper window glowing dangerously with faint smoke, tense residents below. No labels or captions.",
        12: "Clean vertical triptych without borders or labels: wooden cart wheel, narrow dark alley, small clay pot falling from upper window. No text anywhere.",
        14: "Elegant ancient Rome night skyline with torchlight and empty lower area for later subtitles. Pure illustration, no title, no logo, no writing.",
    },
    "rome-short-02-apartments": {
        1: "Historically plausible Roman insula of five storeys, visibly cramped and slightly unstable, fast upward perspective, ordinary residents small below. No modern tower, no text.",
        3: "Vertical cutaway comparison inside one Roman insula: spacious masonry lower room versus tiny rough wooden upper room, unmistakable rich-low poor-high contrast. No speech bubbles or words.",
        4: "Tiny miserable top-floor Roman rental room under a slanted tiled roof, one adult resident squeezed beside a straw bed. No toilet, no box, no text.",
        9: "Authentic ancient Roman terracotta oil lamp with small flame beside dry timber beam and hanging cloth in cramped room. No modern glass lantern, no text.",
        10: "Exterior of crowded Roman insula block, many stacked windows and laundry, busy residents at street level, ancient clothing only. No logo, title or writing.",
        11: "One cramped adult tenant visible in a tiny upper-floor insula window, ironic luxury-penthouse composition. No speech bubble, no text.",
        12: "Four clean visual zones without frames or labels: steep stairs, heavy water amphora, smoking wooden beam, narrow escape corridor. No words anywhere.",
        14: "Clean premium vertical ending: Roman insula foreground and ancient Rome skyline behind, warm afternoon light, open lower subtitle-safe space. No title, logo, labels or writing.",
    },
    "rome-short-03-toilets": {
        1: "Authentic Roman public latrine interior: continuous stone bench with several keyhole-shaped seat openings side by side, no porcelain, no modern toilets, no text.",
        3: "Symmetrical empty ancient Roman stone latrine bench with five adjacent openings, awkward communal layout obvious. No road, no people, no text.",
        5: "Close downward explanatory view of shallow clean water channel running directly in front of an ancient Roman stone latrine bench. No plaza, no modern plumbing, no text.",
        8: "One xylospongium, a natural sea sponge tied to the end of a plain wooden stick, dramatic isolated shadow, tasteful, no hand, no text.",
        9: "One adult Roman citizen in simple tunic giving a horrified side-eye toward an off-screen sponge, expressive but anatomically natural. No speech bubbles, no text.",
        11: "Clean-looking ancient stone latrine surface with subtle symbolic translucent microbe shapes, no words, no labels, no logo.",
        12: "Impressive wide ancient Roman communal latrine: long continuous stone bench with many seat openings and visible water channel below, no porcelain, no modern toilet, no text.",
        13: "Split composition without border: authentic stone latrine bench on left, sea sponge tied to wooden stick on right. No porcelain toilets, no text.",
        14: "Stylish hero view of authentic ancient Roman public latrine interior, continuous stone seating and water channel, elegant but awkward, no modern toilet, no text.",
        15: "Clean Rome-themed vertical end frame with aqueduct and bathhouse courtyard motifs, empty lower space for subtitles, no bathtub, no toilet, no text or logo.",
    },
}


def main() -> None:
    store = ProjectStore()
    for slug, repairs in REPAIRS.items():
        project = ROOT / "projects" / slug
        plan = store.load_plan(project)
        for shot in plan.shots:
            if shot.order in repairs:
                shot.prompt = (
                    "VERTICAL 9:16 adult editorial history cartoon in the established StoryForge style, bold ink outlines, "
                    "premium mobile composition, punchy terracotta and teal colors, historically grounded first-century ancient Rome. "
                    + repairs[shot.order]
                    + " ABSOLUTELY ZERO LETTERS, WORDS, NUMBERS, SIGNS, CAPTIONS, SPEECH BUBBLES, LOGOS OR WATERMARKS. "
                    "Do not imitate a comic cover or infographic. Show one coherent full-frame scene."
                )
                shot.negative_prompt += ", typography, comic cover, comic panels, speech bubble, modern toilet, porcelain toilet"
                shot.status = "stale"
        store.save_plan(project, plan)
        (project / "logs/regenerated_shots.json").write_text(
            json.dumps([f"shot_{x:03d}" for x in repairs], indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
