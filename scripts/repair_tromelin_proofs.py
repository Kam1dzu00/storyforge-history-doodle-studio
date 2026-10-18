from pathlib import Path
import sys

from history_doodle.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
FIXES = {
    "tromelin-proof-opening": {
        "shot_002": "Object-and-environment metaphor after anatomy rejection: dawn on a flat treeless sandbar, broken eighteenth-century ship timbers, scattered wet footprints leading out of the surf and a row of salvaged cloth bundles suggesting survivors just beyond frame. Absolutely no people, no bodies, no faces, no hands, no palm trees, no readable text.",
        "shot_003": "Object-and-environment-only composition: a rough eighteenth-century makeshift wooden boat already far offshore, sailing away from a perfectly flat treeless pale sandbar. Empty ocean horizon, a few broken timbers on shore, absolutely no people, no vegetation taller than grass, no palm trees, no modern objects, no readable text.",
        "shot_005": "Environment-only fixed wide view from a perfectly flat treeless pale sandbar toward an empty ocean horizon. Only low grass, pale sand, one broken timber at the extreme frame edge and vast blank sky. No people, no sun, no moon, no stars, no dates, no numbers, no writing, no marks in sand, no map, no palm trees; clean plate for transparent animation.",
        "shot_008": "Object-only archaeological still life on pale sand: one shallow weathered metal bowl with seven distinct hammered repair patches, coiled natural rope, one small period hand tool and weathered wreck wood. No bucket, no cooking pot, no people, no hands, no labels, no pseudo-text.",
    },
    "tromelin-proof-water-bowl": {
        "shot_003": "Object-and-environment survival mechanism, no people: rainwater runs from a sloped salvaged sailcloth into three irregular hammered eighteenth-century metal vessels beside a low dry-stone shelter on a flat treeless sandbar. No modern cans, no modern roof, no fence, no trees, no people, no hands, no readable text.",
        "shot_008": "Object-only final question image: one shallow weathered metal bowl with seven distinct hammered repair patches sits on flat pale sand against an empty ocean horizon. Vast quiet negative space, low grass only, no palm trees, no people, no fire, no writing, no numbers, no labels.",
    },
    "tromelin-proof-final-rescue": {
        "shot_001": "Historically accurate eighteenth-century rescue attempt: a small open wooden longboat with oars and one simple lateen sail is turned away by violent reef surf near a flat treeless sandbar. No engine, no cabin, no metal hull, no modern boat, no people close-up, no letters or numbers on hull.",
        "shot_004": "Dignified silhouette scene on a flat treeless sandbar: exactly seven adult women in simple eighteenth-century Malagasy wrap garments and one bundled infant, clearly separated back/profile silhouettes around a low dry-stone shelter and shared fire. No European dresses, no masonry village, no palm trees, no modern clothing, no extra people.",
        "shot_005": "Clean base plate for transparent route overlay: aerial oblique view of a flat treeless pale sandbar, reef and desaturated ocean. One tiny empty open wooden rowboat near shore. No people, no text, no dates, no numbers, no route lines, no map labels, no palm trees.",
        "shot_007": "Historically accurate late-eighteenth-century French corvette under square sails beyond a reef, wooden hull and rigging only; a small open launch rows toward a flat treeless sandbar where distant survivor silhouettes wait. No engine, no smokestack, no metal hull, no modern ship, no flags with text, no labels.",
        "shot_008": "Object-and-environment metaphor after group-count failure: on the wooden deck of an eighteenth-century sailing corvette, exactly seven neatly folded weathered shawls are arranged beside one small woven infant cradle, all facing a tiny flat island at sunset. No people, no bodies, no faces, no hands, no extra shawls, no modern objects, no readable text.",
    },
}


if __name__ == "__main__":
    store = ProjectStore()
    for project_name, fixes in FIXES.items():
        project = ROOT / "projects" / project_name
        plan = store.load_plan(project)
        selectors = set(sys.argv[1:])
        selected = {value.split(":", 1)[1] for value in selectors if value.startswith(project_name + ":")}
        if selectors and not selected:
            continue
        for shot in plan.shots:
            if shot.id in fixes and (not selected or shot.id in selected):
                shot.prompt = fixes[shot.id] + " Adult calm editorial documentary, clean dark-ink linework, soft cel shading, subtle paper-gouache texture, desaturated ocean blue, warm sand, charcoal, one dominant focal point, full bleed 16:9."
                shot.negative_prompt += ", palm tree, tropical resort, rock island, bucket, cooking pot, pseudo-text, map labels, tangled bodies, overlapping limbs"
                shot.director_override = True
                shot.seed += 7919
                shot.status = "stale"
                shot.prompt_hash = None
                shot.approved = False
        store.save_plan(project, plan)
        state = store.load_state(project); state.images_status = "stale"; state.render_status = "stale"; store.save_state(project, state)
