from __future__ import annotations

import json
import subprocess
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "projects/shorts-mega-pack-v1-batch"

# Hard rejects from the first visual pass. Every entry was inspected on the
# project contact sheet and failed for anatomy, conspicuous pseudo-text, or
# an immediately unreadable/incorrect visual metaphor.
REJECTS: dict[str, dict[int, str]] = {
    "shorts-v1-s01-what-happens-if-you-dont-sleep-for-72-hours": {2:"pseudo_text",3:"pseudo_text",6:"pseudo_text"},
    "shorts-v1-s09-the-cia-tried-to-turn-a-cat-into-a-spy": {i:"pseudo_text" for i in range(1,8)},
    "shorts-v1-s13-why-airplane-windows-are-round": {i:"pseudo_text_semantic" for i in range(1,8)},
    "shorts-v1-s11-ancient-roman-toilets-were-worse-than-you-think": {i:"semantic" for i in range(1,8)},
    "shorts-v1-s02-your-memory-is-lying-to-you": {i:"semantic" for i in range(1,8)},
    "shorts-v1-s03-antibiotics-cant-kill-a-virus": {1:"pseudo_text",5:"anatomy",6:"pseudo_text"},
    "shorts-v1-s20-why-popcorn-explodes-into-a-white-cloud": {i:"pseudo_text" for i in range(1,8)},
    "shorts-v1-s10-the-cia-built-a-giant-claw-to-steal-a-soviet-submarine": {1:"pseudo_text",2:"pseudo_text",3:"pseudo_text",5:"pseudo_text",7:"pseudo_text"},
    "shorts-v1-s14-why-shaken-soda-explodes": {1:"pseudo_text"},
    "shorts-v1-s12-why-medieval-cities-could-burn-so-fast": {1:"pseudo_text",4:"semantic",7:"pseudo_text"},
    "shorts-v1-s07-why-is-the-sky-blue": {i:"semantic" for i in range(1,8)},
    "shorts-v1-s05-green-mucus-does-not-automatically-mean-antibiotics": {4:"semantic",5:"anatomy_pseudo_text",6:"anatomy_pseudo_text",7:"pseudo_text"},
    "shorts-v1-s18-how-cats-twist-in-midair": {i:"pseudo_text" for i in range(1,8)},
    "shorts-v1-s19-why-metal-feels-colder-than-wood": {i:"anatomy_pseudo_text" for i in range(1,8)},
    "shorts-v1-s04-cold-weather-doesnt-give-you-a-cold": {i:"semantic_pseudo_text" for i in range(1,8)},
    "shorts-v1-s06-fever-is-not-always-the-enemy": {i:"pseudo_text" for i in range(1,8)},
    "shorts-v1-s15-why-you-can-see-your-breath-when-its-cold": {5:"semantic",7:"semantic"},
    "shorts-v1-s16-why-your-stomach-doesnt-digest-itself": {i:"pseudo_text" for i in range(1,8)},
}

# Concrete, text-free replacements for abstract story directions that the image
# model otherwise tends to turn into dashboards, posters, or unrelated mascots.
CONCRETE: dict[tuple[str, int], str] = {
    ("shorts-v1-s01-what-happens-if-you-dont-sleep-for-72-hours", 2):
        "one large glass hourglass half sunk in thick black tar, sand barely moving, a small red tortoise beside it",
    ("shorts-v1-s01-what-happens-if-you-dont-sleep-for-72-hours", 3):
        "seven plain blank photograph cards falling from an open wooden memory box, several cards crooked and cracked",
    ("shorts-v1-s01-what-happens-if-you-dont-sleep-for-72-hours", 6):
        "a glowing human brain shaped like an overheating control room, red warning lights with no symbols, smoke and tangled cables",
    ("shorts-v1-s09-the-cia-tried-to-turn-a-cat-into-a-spy", 1):
        "one natural black cat silhouette beside one tiny microphone capsule on a plain table in a dark spy room",
    ("shorts-v1-s09-the-cia-tried-to-turn-a-cat-into-a-spy", 2):
        "one natural black cat lying on a plain veterinary examination table, one tiny microphone capsule beside its ear",
    ("shorts-v1-s09-the-cia-tried-to-turn-a-cat-into-a-spy", 3):
        "one natural black cat wearing a small plain harness containing one microphone capsule, side view in a dim empty room",
    ("shorts-v1-s09-the-cia-tried-to-turn-a-cat-into-a-spy", 4):
        "one natural black cat walking past a simple park bench while a distant microphone capsule glows faintly",
    ("shorts-v1-s09-the-cia-tried-to-turn-a-cat-into-a-spy", 5):
        "one natural black cat distracted by a small bowl of food, tiny spy microphone lying forgotten behind it",
    ("shorts-v1-s09-the-cia-tried-to-turn-a-cat-into-a-spy", 6):
        "one natural black cat suddenly running across a quiet street, broken microphone capsule left on the curb",
    ("shorts-v1-s09-the-cia-tried-to-turn-a-cat-into-a-spy", 7):
        "one abandoned tiny microphone capsule under a single spotlight in an empty dark room, black cat silhouette exiting far away",
}


def prompt_for(project_name: str, number: int, shot: dict) -> str:
    subject = CONCRETE.get((project_name, number)) or shot.get("visual_subject") or shot.get("action_description") or shot["narration_context"]
    return f"""FULL-SCREEN VERTICAL CARTOON MOVIE FRAME, 9:16.
ONE LITERAL SUBJECT ONLY: {subject}
Large central subject, simple real setting, bold clean silhouette, cinematic depth, vivid color, no small details.
ZERO WRITING. ZERO LETTERS. ZERO NUMBERS. ZERO SIGNS. ZERO LABELS. ZERO LOGOS. ZERO INTERFACES.
NOT a poster. NOT an infographic. NOT a diagram. NOT a page. NOT a collage. NOT a blueprint. NOT a chart. NOT packaging.
No border, no margin, no panels. Avoid people and hands. If an animal is essential, show exactly one anatomically natural animal with no duplicated parts."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project")
    parser.add_argument("--shots", nargs="*", type=int)
    args = parser.parse_args()
    for project_name, rejected in REJECTS.items():
        if args.project and project_name != args.project:
            continue
        project = ROOT / "projects" / project_name
        story_path = project / "planning/story.json"
        story = json.loads(story_path.read_text(encoding="utf-8"))
        by_id = {shot["id"]: shot for shot in story["shots"]}
        log_entries = []
        for number, reason in rejected.items():
            if args.shots and number not in args.shots:
                continue
            shot_id = f"shot_{number:03d}"
            shot = by_id[shot_id]
            shot["prompt"] = prompt_for(project_name, number, shot)
            shot["negative_prompt"] = "text, letters, words, numbers, labels, captions, logo, watermark, pseudo-text, gibberish, typography, infographic, diagram, poster, page, collage, blueprint, interface, card, chart, packaging, sign, gauge markings, schematic, border, white margin, extra limbs, extra fingers, malformed hands, duplicated body parts, unrelated mascot, generic filler"
            shot["status"] = "pending"
            shot["director_override"] = True
            story_path.write_text(json.dumps(story, indent=2, ensure_ascii=False), encoding="utf-8")
            subprocess.run([
                str(ROOT / ".venv/bin/python"), "-m", "history_doodle.image_worker",
                str(project), "--only", shot_id, "--new-seed",
            ], cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src")}, check=True)
            story = json.loads(story_path.read_text(encoding="utf-8"))
            by_id = {item["id"]: item for item in story["shots"]}
            log_entries.append({"shot_id": shot_id, "reason": reason, "seed": by_id[shot_id]["seed"]})
        (project / "logs/regenerated_shots.json").write_text(
            json.dumps(log_entries, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
