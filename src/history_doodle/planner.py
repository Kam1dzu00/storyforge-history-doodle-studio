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

TAG_RE = re.compile(r"^\s*\[(VISUAL|CHARACTER|OBJECTS|LABELS|BACKGROUND|COMPOSITION|PLACEMENT|ANGLE|FOREGROUND|ACTION)\s*:\s*([^]]+)\]\s*$|^\s*\[(NO PEOPLE)\]\s*$", re.I)
VISUAL_ALIASES={"CHARACTER":"CHARACTER_MEDIUM","CLOSEUP":"CHARACTER_CLOSEUP","OBJECT":"OBJECT_HERO","OBJECT_COLLECTION":"OBJECT_COLLECTION","DETAIL":"DETAIL","ENVIRONMENT":"ENVIRONMENT","INFO":"INFO_CARD","MAP":"MAP","COMPARISON":"COMPARISON"}
PLACEMENT_ALIASES={"LEFT":"LEFT_THIRD","RIGHT":"RIGHT_THIRD","LOWER_LEFT":"LOWER_LEFT","LOWER_RIGHT":"LOWER_RIGHT","FOREGROUND_LEFT":"FOREGROUND_LEFT","FOREGROUND_RIGHT":"FOREGROUND_RIGHT","SMALL_IN_ENVIRONMENT":"SMALL_IN_ENVIRONMENT","LEFT_THIRD":"LEFT_THIRD","RIGHT_THIRD":"RIGHT_THIRD","CENTER":"CENTERED_CHARACTER"}
ANGLE_ALIASES={"PROFILE":"PROFILE","THREE_QUARTER":"THREE_QUARTER","TOP_DOWN":"TOP_DOWN_OBJECT","OVER_SHOULDER":"OVER_SHOULDER","EYE_LEVEL":"EYE_LEVEL","SLIGHT_LOW":"SLIGHT_LOW","SLIGHT_HIGH":"SLIGHT_HIGH"}

def parse_director_tags(script: str) -> tuple[str,list[dict]]:
    """Remove optional direction lines from spoken text and retain their cue."""
    spoken=[]; overrides=[]; current=None; pending=None
    for line in script.splitlines():
        match=TAG_RE.match(line)
        if match:
            if current is None:
                cue=(spoken[-1] if spoken else "").strip(); current={"cue":cue}
                overrides.append(current)
                pending=current
            key=(match.group(1) or match.group(3)).upper(); value=(match.group(2) or "true").strip()
            current[key]=value
        else:
            if line.strip():
                spoken.append(line)
                if pending is not None and not pending.get("next_cue"): pending["next_cue"]=line.strip()
            current=None
    return "\n".join(spoken).strip(),overrides

def strip_director_tags(script: str) -> str:
    return parse_director_tags(script)[0]

def extract_production_script(script: str) -> str:
    """Keep narration and director tags, discard production metadata/headings."""
    lines=script.splitlines()
    timed=next((i for i,line in enumerate(lines) if re.match(r"^\s*##\s*\d{1,2}:\d{2}",line)),None)
    if timed is not None: lines=lines[timed+1:]
    kept=[]
    for line in lines:
        stripped=line.strip()
        if re.match(r"^#{1,6}\s+",stripped) or re.match(r"^-{3,}$",stripped): continue
        kept.append(line)
    return "\n".join(kept).strip()

def _auto_visual_type(text: str) -> str:
    low=text.lower()
    if re.search(r"\b(?:he|she|farmer|worker)\b.*\b(?:carried|walked|fed|woke|entered|left|returned)\b",low): return "CHARACTER_MEDIUM"
    if any(x in low for x in ("route","map","connected","across the sea","distant regions")): return "MAP"
    if any(x in low for x in ("compared","versus","rather than","less like","more like","then and now")): return "COMPARISON"
    if re.search(r"\b\d+(?:[.,]\d+)?\s*(?:%|percent|years?|people|times?)\b",low) or any(x in low for x in ("statistics","timeline","three reasons","four reasons")): return "INFO_CARD"
    object_words=[x for x in ("axe","sickle","knife","tools","coins","nails","rope","boots","bucket") if x in low]
    if len(object_words)>=2 or ("several" in low and "tool" in low): return "OBJECT_COLLECTION"
    if object_words: return "OBJECT_HERO"
    if any(x in low for x in ("bowl","porridge","bread","fabric","fire","hearth","carved")): return "DETAIL"
    if any(x in low for x in ("village","house","home","farm","field","fjord","workshop","street","ship","boat","coast","landscape")): return "ENVIRONMENT"
    if any(x in low for x in ("felt","afraid","angry","worried","surprised","tired")): return "CHARACTER_CLOSEUP"
    return "CHARACTER_MEDIUM"

def _historical_details(text: str, location: str) -> list[str]:
    details=[]
    groups=[
        (("modern bathroom","modern shower","private toilet"),["clean ceramic fixtures","glass shower partition","electric lighting"]),
        (("modern apartment","modern kitchen","smartphone","wi-fi"),["clean painted walls","electric fixtures","contemporary domestic objects"]),
        (("insula","roman apartment","upper-floor","apartment block"),["Roman brick-and-rubble insula walls","rough lime plaster","timber floor and roof beams","small shuttered window"]),
        (("roman street","rome is already","commute","cart","market"),["basalt paving stones","raised stone curb","open-front tabernae","terracotta amphorae"]),
        (("fountain","aqueduct"),["weathered limestone basin","bronze or stone water spout","clay water jugs","gravity-fed Roman waterworks"]),
        (("latrine","public toilet","parasite"),["communal stone seats","running drainage channel","plain plastered Roman masonry"]),
        (("bath","strigil","grooming"),["marble-lined bathing pool","hypocaust-warmed chamber","bronze strigil and oil flask"]),
        (("garum","fish sauce","roman food","breakfast"),["coarse Roman pottery bowl","round scored bread loaf","olives and dried figs","amphora of fermented fish sauce"]),
        (("vigiles","firefighter","fire","brazier","oil lamp"),["terracotta oil lamp","timber roof beams","soot-darkened Roman plaster","leather fire bucket and iron hook"]),
        (("forum","merchant","coins","balance scale","transaction"),["bronze balance scale","wax writing tablet and stylus","Roman bronze and silver coins","stone-and-timber shop counter"]),
        (("workshop","metalworker","bakery","millstone"),["open-front Roman workshop","charcoal brazier","iron hand tools","heavy stone mill"]),
        (("doctor","physician","medical","medicine","bloodletting"),["bronze Roman medical instruments","small pottery medicine jars","linen bandage roll","wooden examination stool"]),
        (("night","darkness","lamp","dusk"),["unlit basalt street","small terracotta oil lamp","deep insula doorway shadows"]),
        (("hearth","longhouse","inside","house"),["timber longhouse construction","central hearth with clay vessel","rough wooden bench"]),
        (("farm","animal","chicken","goat","fence"),["rough woven wooden fence","packed-earth farmyard","timber longhouse","stacked split firewood"]),
        (("coast","sea","fjord","boat"),["clinker-built wooden boat","northern coastal landscape","tarred rope and timber planks"]),
        (("tool","axe","sickle","knife","repair"),["simple iron tool","worn wooden handle","rough timber work surface"]),
        (("food","porridge","cook","bowl"),["wooden bowl","simple clay pot","glowing hearth embers"]),
        (("trade","market"),["simple wooden chest","balance weights","bundled wool textile"]),
    ]
    # The current narration beat is authoritative. A broad scene location may
    # supply continuity only when the beat itself has no specific context.
    for source in (text.lower(), location.lower()):
        for words,cues in groups:
            if any(x in source for x in words): details.extend(cues)
        if details: break
    if not details:
        roman="roman" in (text+" "+location).lower() or "rome" in (text+" "+location).lower()
        details=(["period-appropriate Roman masonry and timber","wool tunics, leather sandals and terracotta objects"] if roman else ["period-appropriate architecture and everyday materials","historically accurate clothing and hand-made objects"])
    return list(dict.fromkeys(details))[:4]

def _specific_action(text: str, visual_type: str) -> str:
    low=text.lower()
    if ("chicken" in low or "goat" in low) and re.search(r"\b(?:feed|feeds|feeding|fed)\b",low):
        return "bending beside a rough fence while scattering grain toward waiting chickens and goats"
    actions=[
        (("repair","fence"),"kneeling beside a broken fence rail and tying it securely with rough rope"),
        (("boat","maint"),"pressing a replacement timber plank against the side of a pulled-up wooden boat"),
        (("wake","sunrise"),"pushing aside a wool blanket and sitting up beside the smoking hearth"),
        (("sharpen",),"drawing an iron blade steadily across a worn whetstone"),
        (("carry","bucket"),"walking toward the longhouse while carrying a wooden bucket"),
        (("cook","porridge","hearth"),"stirring a clay pot carefully above the hearth embers"),
    ]
    for words,action in actions:
        if all(x in low for x in words): return action
    if visual_type.startswith("CHARACTER"):
        cleaned=_concrete_visual_beat(text)
        if re.search(r"\b(?:standing|posing|looking at camera|viking in scene)\b",cleaned,re.I) or len(cleaned.split())<4:
            return "performing the practical historical task explicitly described by the narration, naturally focused on the activity"
        return cleaned
    return "show the concrete object, detail or environment described by the narration"

def apply_composition_engine(plan: ProjectPlan, overrides: list[dict] | None=None) -> ProjectPlan:
    """Turn visual grammar into concrete, layered, historically specific direction."""
    overrides=overrides or []; ordered=sorted(plan.shots,key=lambda x:x.order)
    placements=["RIGHT_THIRD","LEFT_THIRD","FOREGROUND_RIGHT","SMALL_IN_ENVIRONMENT","LOWER_LEFT","FOREGROUND_LEFT"]
    angles=["THREE_QUARTER","PROFILE","EYE_LEVEL","SLIGHT_HIGH","OVER_SHOULDER","SLIGHT_LOW"]
    for index,shot in enumerate(ordered):
        text=shot.narration_context or shot.visual_subject
        character=shot.visual_type.startswith("CHARACTER") or shot.visual_type in {"GROUP","SILHOUETTE"}
        shot.visual_purpose=("show the specific human action or reaction in this narration beat" if character else f"show the concrete {shot.visual_type.lower().replace('_',' ')} that communicates this narration beat")
        shot.action_description=_specific_action(text,shot.visual_type)
        shot.historical_story_details=_historical_details(text,shot.location)
        shot.environment_context=", ".join(shot.historical_story_details[:2])
        shot.continuity_key=shot.scene_id
        shot.time_of_day="dawn" if any(x in text.lower() for x in ("sunrise","morning","wakes")) else "evening" if "evening" in text.lower() else "day"
        shot.weather="cool muted northern atmosphere" if any(x in text.lower() for x in ("farm","coast","fjord","outside")) else "interior firelight" if any(x in text.lower() for x in ("inside","hearth","longhouse")) else "neutral muted daylight"
        if character:
            shot.subject_placement=placements[index%len(placements)]
            shot.camera_angle=angles[index%len(angles)]
            shot.framing={"CHARACTER_CLOSEUP":"CLOSEUP","CHARACTER_WIDE":"MEDIUM_WIDE"}.get(shot.visual_type,"MEDIUM")
            shot.foreground_elements=shot.objects[:1] or (["wooden bucket and chickens"] if "feed" in text.lower() else [])
            shot.midground_elements=[shot.action_description]
            shot.background_elements=shot.historical_story_details[:3]
            shot.negative_space_direction="left" if "RIGHT" in shot.subject_placement else "right"
        elif shot.visual_type in {"OBJECT_HERO","OBJECT_COLLECTION","DETAIL","INFO_CARD","MAP"}:
            shot.subject_placement="CENTERED_OBJECT"; shot.camera_angle="TOP_DOWN_OBJECT" if shot.visual_type in {"OBJECT_COLLECTION","DETAIL","INFO_CARD","MAP"} else "FRONTAL_OBJECT"
            shot.framing="DETAIL" if shot.visual_type=="DETAIL" else "CLOSEUP"
            shot.foreground_elements=shot.objects[:5]; shot.midground_elements=[]; shot.background_elements=[]
        else:
            shot.subject_placement="SMALL_IN_ENVIRONMENT"; shot.camera_angle="THREE_QUARTER"; shot.framing="ENVIRONMENTAL_WIDE"
            shot.foreground_elements=shot.historical_story_details[:1]; shot.midground_elements=shot.historical_story_details[1:2]; shot.background_elements=shot.historical_story_details[2:4]
        for override in overrides:
            cues=[override.get("next_cue",""),override.get("cue","")]
            if not any(c and (c in text or SequenceMatcher(None,c.lower(),text.lower()).ratio()>.55) for c in cues): continue
            if "PLACEMENT" in override: shot.subject_placement=PLACEMENT_ALIASES.get(override["PLACEMENT"].upper(),shot.subject_placement)
            if "ANGLE" in override: shot.camera_angle=ANGLE_ALIASES.get(override["ANGLE"].upper(),shot.camera_angle)
            if "FOREGROUND" in override: shot.foreground_elements=[override["FOREGROUND"]]
            if "BACKGROUND" in override: shot.background_elements=[override["BACKGROUND"]]
            if "ACTION" in override: shot.action_description=override["ACTION"]
            if "COMPOSITION" in override: shot.composition=override["COMPOSITION"]
            break
        if character and shot.subject_placement=="CENTERED_CHARACTER" and not shot.centered_justification:
            shot.subject_placement="RIGHT_THIRD" if index%2==0 else "LEFT_THIRD"
        if character and not shot.action_description.strip(): shot.action_description=_specific_action(text,shot.visual_type)
        if index>=2:
            a,b=ordered[index-2],ordered[index-1]
            if (a.subject_placement,a.camera_angle,a.framing)==(b.subject_placement,b.camera_angle,b.framing)==(shot.subject_placement,shot.camera_angle,shot.framing):
                shot.subject_placement="LEFT_THIRD" if shot.subject_placement!="LEFT_THIRD" else "RIGHT_THIRD"
                shot.camera_angle="PROFILE" if shot.camera_angle!="PROFILE" else "THREE_QUARTER"
                shot.framing="MEDIUM_WIDE" if shot.framing!="MEDIUM_WIDE" else "CLOSEUP"
        contextual=(len(shot.historical_story_details)>=2 or shot.visual_type in {"OBJECT_HERO","OBJECT_COLLECTION","DETAIL","INFO_CARD","MAP"})
        specific=not bool(re.fullmatch(r"(?:historical background|viking background|medieval environment|ancient scene)",shot.environment_context.strip(),re.I))
        action_ok=(not character) or (bool(shot.action_description.strip()) and not bool(re.fullmatch(r"(?:standing|posing|looking|viking farmer)",shot.action_description.strip(),re.I)))
        relevance=any(word in (" ".join([shot.action_description,shot.environment_context]+shot.objects)).lower() for word in re.findall(r"[a-z]{4,}",text.lower())[:12]) or bool(shot.objects)
        shot.validation_checks={"ACTION_PRESENT":action_ok,"COMPOSITION_SPECIFIC":specific,"HISTORICAL_CONTEXT":contextual,"THEMATIC_RELEVANCE":relevance,"DIVERSITY_OK":True}
    return plan

def apply_visual_grammar(plan: ProjectPlan, overrides: list[dict] | None=None) -> ProjectPlan:
    object_types={"OBJECT_HERO","OBJECT_COLLECTION","ENVIRONMENT","INFO_CARD","MAP"}
    ordered=sorted(plan.shots,key=lambda x:x.order); overrides=overrides or []
    known={c.id for c in plan.characters}
    for ident in dict.fromkeys(x.get("CHARACTER") for x in overrides if x.get("CHARACTER")):
        if ident in known: continue
        modern="modern" in ident.lower()
        plan.characters.append(CharacterCard(
            id=ident,
            name=ident.replace("_"," ").title(),
            role="recurring visual anchor",
            visual_identity=("the same adult modern office worker, natural adult proportions, tired oval face, short brown hair, plain muted T-shirt and lounge trousers" if modern else "the same adult Viking-age farmer, natural adult proportions, weathered oval face, tied brown hair, short brown beard, muted wool tunic, dark trousers, leather boots"),
            fixed_traits=(["same adult face","same short brown hair","same muted modern clothing","natural adult proportions"] if modern else ["same adult face","same tied brown hair","same short beard","same muted Viking-age clothing","natural adult proportions"]),
        )); known.add(ident)
    for shot in ordered:
        shot.visual_type=_auto_visual_type(shot.narration_context or shot.visual_subject)
        shot.director_override=False
        for override in overrides:
            cues=[override.get("next_cue",""),override.get("cue","")]
            if any(cue and (cue in shot.narration_context or SequenceMatcher(None,cue.lower(),shot.narration_context.lower()).ratio()>.55) for cue in cues):
                requested=VISUAL_ALIASES.get(override.get("VISUAL","").upper())
                if requested: shot.visual_type=requested
                if "OBJECTS" in override: shot.objects=[x.strip() for x in override["OBJECTS"].split("|") if x.strip()]
                if "BACKGROUND" in override: shot.background_style=override["BACKGROUND"]
                if "COMPOSITION" in override: shot.composition=override["COMPOSITION"]
                if "CHARACTER" in override: shot.character_ids=[override["CHARACTER"]]
                if "NO PEOPLE" in override: shot.people_count=0; shot.character_ids=[]
                shot.director_override=True; break
        if shot.visual_type in object_types:
            shot.people_count=0; shot.character_ids=[]
        elif shot.visual_type=="DETAIL":
            shot.people_count=0; shot.character_ids=[]
        elif shot.visual_type=="GROUP": shot.people_count=max(3,shot.people_count)
        else: shot.people_count=max(1,min(2,shot.people_count))
        if not shot.objects:
            shot.objects=[x for x in ("axe","sickle","knife","coin","rope","bucket","porridge","bread") if x in (shot.narration_context or "").lower()][:5]
        if shot.visual_type=="OBJECT_COLLECTION" and not shot.objects:
            shot.objects=["the separate period objects explicitly named in the narration"]
        if shot.visual_type=="OBJECT_COLLECTION":
            shot.composition=shot.composition if shot.director_override and shot.composition else "two to five large period objects evenly spaced in one row, clean gaps between every object, no overlap"
            shot.background_style=shot.background_style or "quiet nearly monochrome aged parchment field"
        elif shot.visual_type=="OBJECT_HERO":
            shot.composition=shot.composition if shot.director_override and shot.composition else "one large centered object filling most of the frame, readable silhouette"
            shot.background_style=shot.background_style or "simple muted period-appropriate surface"
        elif shot.visual_type=="DETAIL":
            shot.composition=shot.composition if shot.director_override and shot.composition else "tight macro detail of material, tool, food, handcraft or architectural feature; no full human body"
        elif shot.visual_type=="ENVIRONMENT":
            shot.composition=shot.composition if shot.director_override and shot.composition else "wide empty establishing view with strong foreground, middle ground and background"
        elif shot.visual_type=="MAP":
            shot.composition=shot.composition if shot.director_override and shot.composition else "single stylized historical map with land, water and one clear route, no written labels"
        elif shot.visual_type=="INFO_CARD":
            shot.composition=shot.composition if shot.director_override and shot.composition else "simple visual infographic made from objects, marks and relative scale, no written words or numbers"
        elif shot.visual_type=="COMPARISON":
            shot.composition=shot.composition if shot.director_override and shot.composition else "two clearly separated subjects in one continuous scene, left and right, no dividing line"
    for index in range(2,len(ordered)):
        if ordered[index].visual_type==ordered[index-1].visual_type==ordered[index-2].visual_type and not ordered[index].director_override:
            ordered[index].visual_type="DETAIL"
            ordered[index].people_count=0; ordered[index].character_ids=[]
    character_types={"CHARACTER_WIDE","CHARACTER_MEDIUM","CHARACTER_CLOSEUP","GROUP","SILHOUETTE"}
    character_indices=[i for i,s in enumerate(ordered) if s.visual_type in character_types]
    allowed=math.floor(len(ordered)*.70)
    for i in character_indices[allowed:]:
        shot=ordered[i]
        if shot.director_override: continue
        shot.visual_type="DETAIL" if i%2 else "ENVIRONMENT"
        shot.people_count=0; shot.character_ids=[]
        shot.composition="tight historically meaningful detail, no full human body" if shot.visual_type=="DETAIL" else "wide empty establishing view with layered depth"
    return plan

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
        script = extract_production_script(script)
        script, director_overrides = parse_director_tags(script)
        style = STYLE_PROMPT.read_text().strip(); negative = NEGATIVE_PROMPT.read_text().strip()
        expected = max(5, round(duration / 6.7))
        schema = json.dumps(ProjectPlan.model_json_schema(), ensure_ascii=False)
        system = "You are a precise visual director. Return only valid JSON matching the supplied schema. Never add markdown. Plan one coherent illustration per shot. Preserve exact chronological order. Your job is not to place the recurring character in every shot. Choose the clearest visual grammar. Prefer objects, details, empty environments, maps and informational compositions whenever they communicate the idea better than a person. Use characters only when human action or emotion is central."
        scene_target = max(4, min(28, round(duration / 25)))
        user = f"""Analyse the exact narration without rewriting it. Build story sections, about {scene_target} chronological scenes, recurring character cards, and 1-2 representative shot templates per scene. The application will safely expand these templates to about {expected} shots at 5-8 seconds each. Every scene narration_text must be an exact contiguous excerpt of the source narration. Each shot shows one literal, readable action with historically recognizable details. Alternate compositions among wide, medium-wide, medium, close detail, object shot, and environment shot. camera_motion must be one allowed enum. Prompt order must be locked style + character identity + era + location + action + composition + shot-specific content. Avoid collage and panels.
Examples: several named tools -> OBJECT_COLLECTION, zero people; a person walking outside to feed animals -> CHARACTER_WIDE, one person; the center of a home is its hearth -> ENVIRONMENT, zero people; trade connects distant regions -> MAP, zero people; a tired farmer compared with a movie warrior -> CHARACTER_MEDIUM, one person.
Use this locked style at the beginning of every prompt:\n{style}\nUse this negative_prompt for every shot:\n{negative}\nSet initial seeds to zero; the application replaces them deterministically.\nSCHEMA:\n{schema}\nNARRATION:\n{script}"""
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
                plan = apply_visual_grammar(plan, director_overrides)
                plan = apply_composition_engine(plan, director_overrides)
                return finalize_plan_prompts(plan, base_seed, style, negative)
            except (ValueError, ValidationError) as exc:
                error = str(exc)
                if attempt == 2 or (duration >= 300 and attempt == 0): break
                raw = self._run("Repair JSON. Return only a complete valid JSON object matching the schema; preserve semantic content.", f"SCHEMA:\n{schema}\nERROR:\n{error}\nBROKEN OUTPUT:\n{raw}", token_budget)
        log.warning("Qwen planning JSON invalid after repairs; using deterministic long-form fallback: %s", error)
        plan = _deterministic_fallback(script, duration)
        plan = normalize_shot_counts(plan, duration)
        plan = apply_visual_grammar(plan, director_overrides)
        plan = apply_composition_engine(plan, director_overrides)
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

def build_shot_prompt(shot: Shot, cards: dict[str, CharacterCard], style: str | None = None, negative: str | None = None) -> Shot:
    style = style or STYLE_PROMPT.read_text().strip(); negative = negative or NEGATIVE_PROMPT.read_text().strip()
    identities = "; ".join("CHARACTER CARD: " + _safe_visual_phrase(cards[c].visual_identity) + "; FIXED: " + ", ".join(cards[c].fixed_traits) for c in shot.character_ids if c in cards) if shot.people_count else ""
    props = ", ".join(_safe_visual_phrase(x) for x in shot.historical_props)
    action = _safe_visual_phrase(shot.action_description or shot.action); subject = _concrete_visual_beat(shot.visual_subject); composition = _safe_visual_phrase(shot.composition)
    if shot.people_count==0:
        named_objects=", ".join(shot.objects[:5]) or "the historically accurate objects explicitly named in the narration"
        if shot.visual_type in {"OBJECT_HERO","OBJECT_COLLECTION"}:
            action=f"objects only, display {named_objects} as a clean still life"
            subject=f"only {named_objects}; empty scene"
        elif shot.visual_type=="ENVIRONMENT":
            action="empty location only, establish the historically accurate place"
            subject="architecture, landscape and period objects only; empty scene"
        elif shot.visual_type=="DETAIL":
            action="one tight material or object detail only"
            subject="historically meaningful close detail; no full body"
    if shot.people_count==0: anatomy="NO PEOPLE: no people, no human figures, no hands, no body parts"
    elif shot.people_count==1: anatomy="exactly one clearly separated adult human figure, clean readable body silhouette, simple natural pose, exactly two arms and two legs, all limbs visually separated, no overlapping limbs, no overlapping legs, hands visible only if necessary, character naturally focused on the activity and not looking at viewer"
    elif shot.people_count==2: anatomy="exactly two clearly separated adult human figures with visible space between bodies, clean readable silhouettes, no fused torsos, no merged limbs, no overlapping legs, simple natural poses, not looking at viewer"
    else: anatomy="distant simplified background silhouettes only, no interlocked bodies, no detailed hands"
    object_rule = f"OBJECTS: {', '.join(shot.objects[:5])}; isolated large forms, evenly spaced, nothing overlaps" if shot.objects else ""
    final_safety="OBJECTS AND SETTING ONLY; EMPTY OF ALL PEOPLE; do not draw a person, face, hand, arm, leg or human silhouette" if shot.people_count==0 else ""
    layers=[
        f"FOREGROUND: {', '.join(shot.foreground_elements[:2])}" if shot.foreground_elements else "",
        f"MIDGROUND: {', '.join(shot.midground_elements[:2])}" if shot.midground_elements else "",
        f"BACKGROUND: {', '.join(shot.background_elements[:3])}" if shot.background_elements else (f"BACKGROUND: {_safe_visual_phrase(shot.background_style)}" if shot.background_style else ""),
    ]
    history=", ".join(shot.historical_story_details[:4]) or props
    shot.prompt = "; ".join(x for x in [style, f"VISUAL PURPOSE: {_safe_visual_phrase(shot.visual_purpose)}", f"MAIN SUBJECT: {subject}", f"EXACT ACTION: {action}", f"SUBJECT PLACEMENT: {shot.subject_placement}", f"CAMERA: {shot.camera_angle}, {shot.framing}", *layers, f"ENVIRONMENT: {_safe_visual_phrase(shot.environment_context)}", f"HISTORICAL STORY DETAILS: {history}" if history else "", f"COMPOSITION: {composition}", object_rule, identities, anatomy, final_safety, "silent visual moment with no depicted dialogue; single coherent 16:9 illustration; no text, no letters, no numbers, no symbols, no logos; no collage, no panels, no split screen"] if x)
    shot.negative_prompt = negative; shot.status = "pending"; shot.prompt_hash = None
    return shot

def finalize_plan_prompts(plan: ProjectPlan, base_seed: int, style: str | None = None, negative: str | None = None) -> ProjectPlan:
    cards = {c.id: c for c in plan.characters}
    for i, shot in enumerate(sorted(plan.shots, key=lambda s: s.order)):
        shot.seed = shot_seed(base_seed, i)
        build_shot_prompt(shot, cards, style, negative)
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
