from __future__ import annotations

import json, logging, re, math
from difflib import SequenceMatcher
from pathlib import Path
from pydantic import ValidationError
from .config import LLM_REPO, NEGATIVE_PROMPT, STYLE_PROMPT
from .schemas import CharacterCard, ProjectPlan, Scene, Shot, StorySection
from .util import cleanup_models, json_from_model_text, shot_seed

log = logging.getLogger(__name__)

def target_words(seconds: int, wpm: int = 158) -> int:
    return round(seconds * wpm / 60)

class LocalPlanner:
    def __init__(self, model_repo: str = LLM_REPO): self.model_repo = model_repo

    def _run(self, system: str, user: str, max_tokens: int) -> str:
        from mlx_lm import load, generate
        model = tokenizer = None
        try:
            model, tokenizer = load(self.model_repo)
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            return generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, verbose=False)
        finally:
            del model, tokenizer
            cleanup_models()

    def create_script(self, brief: str, duration: int) -> str:
        words = target_words(duration)
        system = "You write compelling English narration for an adult, funny educational YouTube history explainer. Return narration only: no headings, markdown, citations, camera directions, music notes, or prompts."
        user = f"Write approximately {words} words ({duration/60:.1f} minutes at 158 WPM). Use a sharp hook, myth-versus-reality structure, concrete daily-life detail, witty modern comparisons, and a satisfying ending. Brief:\n{brief}"
        result = self._run(system, user, min(6000, words * 2)).strip()
        result = re.sub(r"[*_`#]", "", result)
        result = re.sub(r"\[(?:music|pause|sfx)[^]]*\]", "", result, flags=re.I)
        return re.sub(r"\s+", " ", result).strip()

    def plan(self, script: str, duration: int, base_seed: int) -> ProjectPlan:
        style = STYLE_PROMPT.read_text().strip(); negative = NEGATIVE_PROMPT.read_text().strip()
        expected = max(5, round(duration / 6.7))
        schema = json.dumps(ProjectPlan.model_json_schema(), ensure_ascii=False)
        system = "You are a precise visual director. Return only valid JSON matching the supplied schema. Never add markdown. Plan one coherent illustration per shot. Preserve the narration's exact chronological order: scene order 1 must cover the beginning and the final scene must cover the ending."
        scene_target = max(4, min(28, round(duration / 25)))
        user = f"""Analyse the exact narration without rewriting it. Build story sections, about {scene_target} chronological scenes, recurring character cards, and 1-2 representative shot templates per scene. The application will safely expand these templates to about {expected} shots at 5-8 seconds each. Every scene narration_text must be an exact contiguous excerpt of the source narration. Each shot shows one literal, readable action with historically recognizable details. Alternate compositions among wide, medium-wide, medium, close detail, object shot, and environment shot. camera_motion must be one allowed enum. Prompt order must be locked style + character identity + era + location + action + composition + shot-specific content. Avoid collage and panels. Use this locked style at the beginning of every prompt:\n{style}\nUse this negative_prompt for every shot:\n{negative}\nSet initial seeds to zero; the application replaces them deterministically.\nSCHEMA:\n{schema}\nNARRATION:\n{script}"""
        token_budget = min(8000, 2200 + scene_target * 220)
        raw = self._run(system, user, token_budget)
        error = ""
        for attempt in range(3):
            try:
                plan = ProjectPlan.model_validate(_repair_links(json_from_model_text(raw)))
                plan = _align_scene_narration(plan, script)
                if any(scene.narration_text.strip() not in script for scene in plan.scenes):
                    raise ValueError("Every scene narration_text must be an exact contiguous excerpt from the source narration")
                plan = normalize_shot_counts(plan, duration)
                return finalize_plan_prompts(plan, base_seed, style, negative)
            except (ValueError, ValidationError) as exc:
                error = str(exc)
                if attempt == 2 or (duration >= 300 and attempt == 0): break
                raw = self._run("Repair JSON. Return only a complete valid JSON object matching the schema; preserve semantic content.", f"SCHEMA:\n{schema}\nERROR:\n{error}\nBROKEN OUTPUT:\n{raw}", token_budget)
        log.warning("Qwen planning JSON invalid after repairs; using deterministic long-form fallback: %s", error)
        plan = _deterministic_fallback(script, duration)
        plan = normalize_shot_counts(plan, duration)
        return finalize_plan_prompts(plan, base_seed, style, negative)

def _deterministic_fallback(script: str, duration: int) -> ProjectPlan:
    protected = re.sub(r"\b([ap])\.m\.", lambda m: f"{m.group(1)}<DOT>m<DOT>", script, flags=re.I)
    sentences = [x.replace("<DOT>", ".").strip() for x in re.split(r"(?<=[.!?])\s+", protected) if x.strip()]
    scene_count = max(4, min(len(sentences), round(duration / 25)))
    groups=[]; cursor=0
    for index in range(scene_count):
        remaining=len(sentences)-cursor; take=remaining if index==scene_count-1 else max(1, round(remaining/(scene_count-index)))
        groups.append(" ".join(sentences[cursor:cursor+take])); cursor+=take
    character=CharacterCard(
        id="recurring_adult", name="Recurring adult protagonist", role="visual anchor",
        visual_identity=("the same adult man about thirty-five years old, lean average-height body, "
                         "narrow oval face, brown eyes, shoulder-length chestnut hair tied low, short brown stubble, "
                         "wearing a muted olive period-appropriate working garment, dark brown trousers, leather belt and brown boots"),
        fixed_traits=["same narrow oval face", "same chestnut tied-back hair", "same short brown stubble", "same olive and dark-brown clothing palette", "natural adult proportions"],
    )
    scenes=[]; shots=[]
    for i,text in enumerate(groups,1):
        sid=f"scene_{i:03d}"; shid=f"shot_{i:03d}"
        scenes.append(Scene(id=sid,section_id="section_001",order=i,narration_text=text,shot_ids=[shid]))
        shots.append(Shot(id=shid,scene_id=sid,order=i,narration_context=text,visual_subject=text,location="the single historically appropriate location explicitly implied by this narration beat; never a modern setting",action="show one literal action from this narration beat",historical_props=["strictly period-appropriate everyday clothing", "historically recognizable tools and architecture from the era and culture named in the narration", "no modern clothing or objects"],character_ids=[character.id],composition="wide establishing shot",camera_motion="static",prompt="",negative_prompt="",seed=0,estimated_duration=7))
    return ProjectPlan(sections=[StorySection(id="section_001",title="Chronological story",purpose="Preserve exact narration order",scene_ids=[x.id for x in scenes])],scenes=scenes,shots=shots,characters=[character])

def _safe_visual_phrase(value: str) -> str:
    value = re.sub(r"['\"]?\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?['\"]?", "", value, flags=re.I)
    value = re.sub(r"\b(?:wears?|holds?)\b[^,;]{0,60}\bsign\b[^,;]*", "", value, flags=re.I)
    value = re.sub(r"(?:\bTikTok\b|\bapp\b|\bnotification\b|\bdisplay\b|\bscreen shows?\b|\bwith a video of\b|\bphoto\b)", "blank-screen device", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" ,;:-")
    return value

def _concrete_visual_beat(value: str) -> str:
    """Keep narration semantics while removing clauses that invite drawn dialogue/text."""
    value = _safe_visual_phrase(value)
    value = re.split(r"\b(?:and the (?:guild|law|rule)|the rule (?:is|was)|which means|in other words|according to|as they say)\b", value, maxsplit=1, flags=re.I)[0]
    value = re.sub(r"[“”\"].*?[“”\"]", "", value)
    return value.strip(" ,;:-") or "one historically accurate everyday action from this narration beat"

def finalize_plan_prompts(plan: ProjectPlan, base_seed: int, style: str | None = None, negative: str | None = None) -> ProjectPlan:
    style = style or STYLE_PROMPT.read_text().strip(); negative = negative or NEGATIVE_PROMPT.read_text().strip()
    cards = {c.id: c for c in plan.characters}
    for i, shot in enumerate(sorted(plan.shots, key=lambda s: s.order)):
        shot.seed = shot_seed(base_seed, i)
        identities = "; ".join("CHARACTER CARD: " + _safe_visual_phrase(cards[c].visual_identity) + "; FIXED: " + ", ".join(cards[c].fixed_traits) for c in shot.character_ids if c in cards)
        props = ", ".join(_safe_visual_phrase(x) for x in shot.historical_props)
        action = _concrete_visual_beat(shot.action); subject = _concrete_visual_beat(shot.visual_subject); composition = _safe_visual_phrase(shot.composition)
        shot.prompt = "; ".join(x for x in [style, identities, f"ERA DESCRIPTION AND PROPS: {props}" if props else "ERA DESCRIPTION: historically accurate period details", f"LOCATION: {_safe_visual_phrase(shot.location)}", f"ACTION: {action}", f"COMPOSITION: {composition}", f"SHOT-SPECIFIC CONTENT: {subject}", "silent visual moment with no depicted dialogue; no speech bubbles; single coherent 16:9 illustration; one clear foreground action; absolutely no writing anywhere; no letters, no numbers, no symbols, no logos; clocks have no digits; device screens are blank; one continuous camera view; no panels, no divisions, no collage, no split screen"] if x)
        shot.negative_prompt = negative; shot.status = "pending"; shot.prompt_hash = None
    return plan

def _repair_links(data: dict) -> dict:
    """Repair harmless ID/reference mistakes produced by the local planner."""
    sections = data.get("sections") or []
    scenes = data.get("scenes") or []
    shots = data.get("shots") or []
    characters = data.get("characters") or []
    scene_ids = {x.get("id") for x in scenes}
    char_ids = {x.get("id") for x in characters}
    shot_to_scene = {}
    for scene in scenes:
        for shot_id in scene.get("shot_ids") or []:
            shot_to_scene[shot_id] = scene.get("id")
    fallback_scene = scenes[0].get("id") if scenes else None
    for shot in shots:
        if shot.get("scene_id") not in scene_ids:
            shot["scene_id"] = shot_to_scene.get(shot.get("id"), fallback_scene)
        shot["character_ids"] = [x for x in shot.get("character_ids", []) if x in char_ids]
    for scene in scenes:
        scene["shot_ids"] = [x.get("id") for x in shots if x.get("scene_id") == scene.get("id")]
    section_ids = {x.get("id") for x in sections}
    fallback_section = sections[0].get("id") if sections else None
    for scene in scenes:
        if scene.get("section_id") not in section_ids:
            scene["section_id"] = fallback_section
    for section in sections:
        section["scene_ids"] = [x.get("id") for x in scenes if x.get("section_id") == section.get("id")]
    return data

def _align_scene_narration(plan: ProjectPlan, script: str) -> ProjectPlan:
    """Guarantee ordered, exact source excerpts without asking the LLM to copy punctuation perfectly."""
    protected = re.sub(r"\b([ap])\.m\.", lambda m: f"{m.group(1)}<DOT>m<DOT>", script, flags=re.I)
    sentences = [x.replace("<DOT>", ".").strip() for x in re.split(r"(?<=[.!?])\s+", protected) if x.strip()]
    def source_position(scene):
        needle = re.sub(r"\W+", " ", scene.narration_text.lower()).strip()
        scores = []
        for i in range(len(sentences)):
            candidate = " ".join(sentences[i:i + 3])
            candidate = re.sub(r"\W+", " ", candidate.lower()).strip()
            scores.append((SequenceMatcher(None, needle, candidate).ratio(), i))
        return max(scores)[1] if scores else scene.order
    scenes = sorted(plan.scenes, key=lambda x: (source_position(x), x.order))
    for index, scene in enumerate(scenes, 1): scene.order = index
    plan.scenes = scenes
    for section in plan.sections:
        section.scene_ids = [x.id for x in scenes if x.section_id == section.id]
    plan.sections.sort(key=lambda x: min((s.order for s in scenes if s.section_id == x.id), default=10**9))
    for section in plan.sections: section.scene_ids.sort(key=lambda x: next(s.order for s in scenes if s.id == x))
    if not scenes or len(sentences) < len(scenes):
        return plan
    weights = [max(1, len(x.narration_text.split())) for x in scenes]
    remaining_sentences = len(sentences); remaining_weight = sum(weights); cursor = 0
    for index, (scene, weight) in enumerate(zip(scenes, weights)):
        scenes_left = len(scenes) - index
        if scenes_left == 1:
            take = remaining_sentences
        else:
            take = max(1, min(remaining_sentences - (scenes_left - 1), round(remaining_sentences * weight / remaining_weight)))
        scene.narration_text = " ".join(sentences[cursor:cursor + take])
        cursor += take; remaining_sentences -= take; remaining_weight -= weight
    return plan

def normalize_shot_counts(plan: ProjectPlan, duration: int) -> ProjectPlan:
    by_id = {s.id: s for s in plan.shots}; words = sum(max(1, len(s.narration_text.split())) for s in plan.scenes)
    ordered = []
    for scene in sorted(plan.scenes, key=lambda x: x.order):
        expected = duration * max(1, len(scene.narration_text.split())) / words
        minimum, maximum = max(1, math.ceil(expected / 10)), max(1, math.floor(expected / 3))
        wanted = min(maximum, max(minimum, round(expected / 7)))
        source = [by_id[x] for x in scene.shot_ids if x in by_id]
        if not source: raise ValueError(f"Scene {scene.id} has no visual shots")
        selected = source[:wanted]
        while len(selected) < wanted:
            base = source[len(selected) % len(source)].model_copy(deep=True)
            base.composition = f"{base.composition}; alternate visual beat and camera distance, visibly different from the previous shot"
            base.visual_subject = f"Alternate visual beat: {base.visual_subject}"
            selected.append(base)
        selected = _diversify_scene_shots(scene.narration_text, selected)
        scene.shot_ids = []
        for shot in selected:
            shot.scene_id = scene.id; ordered.append(shot)
    for index, shot in enumerate(ordered, 1):
        shot.id=f"shot_{index:03d}"; shot.order=index; shot.status="pending"; scene=next(s for s in plan.scenes if s.id==shot.scene_id); scene.shot_ids.append(shot.id)
    plan.shots=ordered
    return plan

def _diversify_scene_shots(narration: str, shots: list) -> list:
    """Turn repeated/panel-like planner output into distinct single illustrations.

    Small local models sometimes satisfy a request for multiple beats by cloning one
    split-screen prompt.  That is structurally valid JSON but visually unusable.  We
    deterministically bind each repeated shot to a different sentence/beat and remove
    text-bearing UI directions before the image model sees it.
    """
    protected = re.sub(r"\b([ap])\.m\.", lambda m: f"{m.group(1)}<DOT>m<DOT>", narration, flags=re.I)
    beats = [x.replace("<DOT>", ".").strip() for x in re.split(r"(?<=[.!?])\s+", protected) if x.strip()]
    if not beats:
        beats = [narration.strip()]
    signatures = [(s.visual_subject, s.location, s.action, s.composition) for s in shots]
    repeated = len(set(signatures)) < len(signatures)
    forbidden = any(re.search(r"split[ -]?screen|collage|panel", " ".join((s.location, s.composition)), re.I) for s in shots)
    useful = lambda text: {x for x in re.findall(r"[a-z]{4,}", text.lower()) if x not in {"with","from","that","this","into","only","shot","wide","close","person","shows","showing"}}
    scene_terms = useful(narration)
    mismatched = any(len(useful(" ".join((s.visual_subject,s.action,s.location))) & scene_terms) / max(1,len(scene_terms)) < .08 for s in shots)
    derived = any(s.visual_subject.startswith("One literal moment from the narration:") for s in shots)
    if not (repeated or forbidden or mismatched or derived):
        return shots

    cameras = [
        "wide establishing shot with one clear focal action",
        "medium-wide character shot with one clear focal action",
        "medium character shot at eye level with one clear focal action",
        "close detail of one object or gesture",
        "environment shot with one clear focal action",
    ]
    for i, shot in enumerate(shots):
        beat = " ".join(beats[i:]) if i == len(shots) - 1 and len(beats) > len(shots) else beats[min(i, len(beats) - 1)]
        low = beat.lower()
        is_norse = any(k in low for k in ("viking", "norse", "longhouse", "raid", "scandinav"))
        is_medieval = any(k in low for k in ("medieval", "middle ages", "guild", "manor", "serf", "feudal"))
        is_roman = any(k in low for k in ("roman", "rome", "legion", "forum", "senate"))
        shot.narration_context = beat
        shot.visual_subject = f"One literal moment from the narration: {beat}"
        shot.action = f"Depict only this action as one frozen readable moment: {beat}"
        if is_norse:
            shot.location = "one early-medieval Norse longhouse interior or farmyard appropriate to the action"
            shot.historical_props = ["wool and linen Norse clothing", "wooden household tools", "period-appropriate timber architecture"]
        elif is_medieval:
            shot.location = "one medieval European home, workshop, farm or street appropriate to the action"
            shot.historical_props = ["medieval wool and linen work clothing", "handmade wooden tools", "stone, timber and limewashed architecture"]
        elif is_roman:
            shot.location = "one ancient Roman home, workshop, farm or street appropriate to the action"
            shot.historical_props = ["ancient Roman everyday clothing", "period hand tools", "stone, plaster and timber architecture"]
        else:
            shot.location = re.sub(r"split[ -]?screen.*", "one coherent location appropriate to the action", shot.location, flags=re.I)
            shot.historical_props = [p for p in shot.historical_props if not re.search(r"app|notification|screen|photo|display|text|letter|number", p, re.I)]
        shot.composition = cameras[i % len(cameras)] + "; one continuous scene, one camera view"
    return shots
