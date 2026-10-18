from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ROOT
from .schemas import ProjectPlan, ProjectState, Shot


DATA = ROOT / "data"
REFERENCES = ROOT / "reference_assets"
LEGACY_STYLE_ID = "history_editorial"
FULL_BLEED_EXCLUSIONS = [
    "white frame", "white border", "white page", "poster border", "poster layout",
    "floating illustration card", "blank margins", "empty page background", "framed collage",
]


class RegistryError(ValueError):
    pass


class MissingHostIdentityError(FileNotFoundError):
    pass


class HostReferenceConditioningUnsupported(RuntimeError):
    pass


class StyleRegistry:
    def __init__(self, root: Path = DATA / "styles"): self.root = root

    def list_styles(self) -> list[dict[str, Any]]:
        legacy = {"style_id": LEGACY_STYLE_ID, "display_name": "Existing / Historical Editorial", "description": "Established StoryForge historical editorial illustration style.", "full_bleed_required": False}
        result = [legacy]
        for path in sorted(self.root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8")); self._validate(data, path); result.append(data)
        return result

    def _validate(self, data: dict[str, Any], path: Path) -> None:
        for key in ("style_id", "display_name", "description", "positive_prompt_keywords", "negative_prompt_keywords"):
            if key not in data: raise RegistryError(f"Invalid style profile {path}: missing {key}")

    def get(self, style_id: str) -> dict[str, Any]:
        if style_id == LEGACY_STYLE_ID:
            return self.list_styles()[0]
        path = self.root / f"{style_id}.json"
        if not path.exists(): raise RegistryError(f"Unknown style ID: {style_id}")
        data = json.loads(path.read_text(encoding="utf-8")); self._validate(data, path); return data

    def resolve_for_project(self, state: ProjectState) -> dict[str, Any]:
        return self.get(state.style_mode or LEGACY_STYLE_ID)


class CharacterRegistry:
    def __init__(self, root: Path = DATA / "characters"): self.root = root

    def list_characters(self) -> list[dict[str, Any]]:
        return [json.loads(x.read_text(encoding="utf-8")) for x in sorted(self.root.glob("*.json"))]

    def get(self, character_id: str) -> dict[str, Any]:
        path = self.root / f"{character_id}.json"
        if not path.exists(): raise RegistryError(f"Unknown character ID: {character_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("character_id") != character_id: raise RegistryError(f"Invalid character profile: {path}")
        return data

    @staticmethod
    def _resolve(path: str | None) -> Path | None:
        if not path: return None
        candidate = Path(path)
        return candidate if candidate.is_absolute() else ROOT / candidate

    def resolve_references(self, character_id: str, style_id: str, require_real: bool = True) -> list[Path]:
        profile = self.get(character_id)
        real = self._resolve(profile.get("reference_real_image_path"))
        if require_real and (real is None or not real.exists()):
            raise MissingHostIdentityError("HOST_REAL_IDENTITY_REFERENCE_MISSING: reference_assets/host_real_identity.jpg")
        refs = [real] if real and real.exists() else []
        stylized = self._resolve(profile.get("reference_stylized_by_style", {}).get(style_id))
        if stylized and stylized.exists(): refs.append(stylized)
        return refs

    def reference_status(self, character_id: str, style_id: str) -> tuple[str, str]:
        profile = self.get(character_id)
        real = self._resolve(profile.get("reference_real_image_path"))
        stylized = self._resolve(profile.get("reference_stylized_by_style", {}).get(style_id))
        return ("Ready" if real and real.exists() else "Missing", "Ready" if stylized and stylized.exists() else "Missing")


@dataclass(frozen=True)
class RouteDecision:
    visual_category: str
    visual_focus: str
    host_present: bool
    host_role: str | None
    rationale: str


class VisualRouter:
    OBJECTS = ("thermometer", "air conditioner", "cotton swab", "hat", "beer", "fan", "lemon")
    MEDICAL = ("meningitis", "membrane", "brain", "spinal cord", "bacteria", "bladder", "ear canal", "infection", "mucosa")
    ENVIRONMENTS = ("room", "mountain", "street", "hospital", "apartment", "city", "climate")

    def route(self, narration: str, shot: Shot | None = None) -> RouteDecision:
        if shot and (shot.routing_source == "manual" or shot.director_override) and shot.visual_category and shot.visual_focus:
            return RouteDecision(shot.visual_category, shot.visual_focus, bool(shot.host_present), shot.host_role, "manual override")
        text = narration.lower()
        if re.search(r"\b\d+(?:\.\d+)?\s*(?:°|degrees?|percent|%|km|miles?)\b", text):
            return RouteDecision("infographic_metric", "the named measurement shown as one dominant, instantly readable visual", False, None, "numeric metric")
        if any(x in text for x in self.MEDICAL):
            return RouteDecision("medical_diagram", "a clear stylized educational diagram of the exact medical structure or process named", False, None, "medical concept")
        if "air conditioner" in text and any(x in text for x in ("kill", "assassin", "thought", "trying")):
            return RouteDecision("host_reaction", "recurring host reacting skeptically to an ordinary wall-mounted air conditioner", True, "reaction", "comic first-person object myth")
        if "mother" in text and "hat" in text:
            return RouteDecision("host_reaction", "recurring host in an oversized winter hat reacting to worried parental advice", True, "reaction", "personal comedic reconstruction")
        for obj in self.OBJECTS:
            if re.search(rf"\b{re.escape(obj)}\b", text):
                return RouteDecision("object_single", f"one dominant {obj}", False, None, "named concrete object")
        if any(x in text for x in ("first ", " then ", "causes", "leads to", "route")):
            return RouteDecision("process_sequence", "the exact cause-and-effect sequence described by the narration", False, None, "process language")
        if any(x in text for x in ("versus", " vs ", "compared", "rather than", "difference")):
            return RouteDecision("comparison_split", "the two explicitly compared subjects, clearly separated", False, None, "comparison language")
        if any(x in text for x in self.ENVIRONMENTS):
            return RouteDecision("environment_wide", "the exact named location as a readable establishing scene", False, None, "named environment")
        if any(x in text for x in ("imagine", "seriously", "apparently", "you won't believe", "?")):
            return RouteDecision("host_reaction", "recurring host delivering the emotional or comic reaction in the narration", True, "reaction", "reaction/direct address")
        return RouteDecision("host_explaining", "recurring host clearly explaining the single central idea", True, "explaining", "no more exact subject detected")


class PromptComposer:
    def __init__(self, styles: StyleRegistry | None = None, characters: CharacterRegistry | None = None):
        self.styles = styles or StyleRegistry(); self.characters = characters or CharacterRegistry()

    @staticmethod
    def _template(name: str) -> str:
        return (DATA / "prompt_templates" / name).read_text(encoding="utf-8")

    @staticmethod
    def _join(value: Any) -> str:
        if isinstance(value, list): return ", ".join(str(x) for x in value)
        if isinstance(value, dict): return "; ".join(f"{k}: {PromptComposer._join(v)}" for k, v in value.items())
        return str(value or "")

    def compose(self, state: ProjectState, shot: Shot, require_references: bool = False) -> tuple[str, str, list[Path]]:
        style = self.styles.resolve_for_project(state)
        if style["style_id"] == LEGACY_STYLE_ID: return shot.prompt, shot.negative_prompt, []
        host = bool(state.host_enabled and shot.host_present)
        refs: list[Path] = []
        identity = ""
        if host:
            if not state.host_character_id: raise RegistryError("Host enabled but host_character_id is missing")
            character = self.characters.get(state.host_character_id)
            refs = self.characters.resolve_references(state.host_character_id, style["style_id"], require_real=require_references)
            identity = character["base_identity_description"] + "; " + ", ".join(character["immutable_visual_traits"] + character["do_not_change_rules"])
        values = {
            "style_id": style["style_id"], "visual_focus": shot.visual_focus or shot.visual_subject,
            "visual_category": shot.visual_category or shot.visual_type, "host_role": shot.host_role or "guide",
            "host_expression": shot.host_expression or "engaged and readable", "host_pose": shot.host_pose or shot.action_description,
            "environment": shot.environment_context, "action": shot.action_description, "foreground": self._join(shot.foreground_elements),
            "midground": self._join(shot.midground_elements), "background": self._join(shot.background_elements),
            "framing": shot.framing, "camera_angle": shot.camera_angle, "subject_placement": shot.subject_placement,
            # Object-only frames should be driven by the literal visual brief.
            # Passing spoken copy here invites image models to render that copy
            # as pseudo-text even when the negative prompt bans typography.
            "narration_summary": shot.narration_context if shot.people_count else (shot.visual_focus or shot.visual_subject),
        }
        template = self._template("host_scene_template.txt" if host else "non_host_scene_template.txt")
        prompt = template.format_map(values)
        style_block = "STYLE PROFILE: " + "; ".join(self._join(style.get(k)) for k in ("visual_identity", "composition_rules", "camera_rules", "background_rules", "positive_prompt_keywords"))
        if identity: prompt = style_block + "\nIDENTITY PRIORITY: " + identity + "\n" + prompt
        else: prompt = style_block + "\n" + prompt
        negative = ", ".join(style.get("negative_prompt_keywords", []))
        if host:
            prompt += "\nOUTPUT DISCIPLINE: ONE recurring host only, in ONE continuous cinematic scene. References are identity/style anchors only; never reproduce their panels, labels, layouts, or extra figures."
            negative += ", collage, contact sheet, character sheet, multiple panels, split screen, duplicate person, extra people, reference labels, gibberish text"
        elif shot.people_count == 0:
            prompt += "\nOUTPUT DISCIPLINE: object/concept only; absolutely no person, face, body, hand, presenter, or host."
            negative += ", person, people, human, face, body, hand, presenter, host"
        if style["style_id"] == "bright_explainer" or style["style_id"].startswith("shorts_"):
            prompt += "\nV3 SHOW ENERGY: Create a finished adult animated-show frame with one instantly readable visual beat, dramatic perspective, expressive acting or a world-grounded hero object, strong depth layers, cinematic warm/cool lighting, controlled motion accents, and no empty infographic staging."
            prompt += "\nABSOLUTE TEXT BAN: generate no readable or unreadable text of any kind: no letters, words, numbers, signs, captions, labels, bubbles, pseudo-language, gibberish, typography, watermark, UI, or debug marks. Leave clean composition space only when the deterministic renderer will add text later."
            negative += ", text, letters, words, numbers, captions, speech bubble, sign, label, pseudo-language, typography, watermark, UI text, debug text, gibberish"
        if style["style_id"] == "clean_editorial":
            prompt += "\nCLEAN EDITORIAL DISCIPLINE: one dominant focal point, calm 70/20/10 palette, mature hand-drawn editorial documentary linework, soft cel shading and subtle paper-gouache texture. Preserve generous negative space and long-form visual comfort. Never render final typography inside the generated image."
            negative += ", childish illustration, school infographic, glossy vector art, glossy 3D, photorealism, anime, comic overload, hyper-saturation, crowded labels, arrows, pseudo-text, watermark"
        if style.get("full_bleed_required"): negative += ", " + ", ".join(FULL_BLEED_EXCLUSIONS)
        return prompt, negative, refs


def prepare_plan(plan: ProjectPlan, state: ProjectState) -> ProjectPlan:
    if not state.style_mode or state.style_mode == LEGACY_STYLE_ID: return plan
    router = VisualRouter(); composer = PromptComposer()
    for shot in sorted(plan.shots, key=lambda x: x.order):
        decision = router.route(shot.narration_context, shot)
        if shot.routing_source != "manual":
            shot.visual_category = decision.visual_category; shot.visual_focus = decision.visual_focus
            shot.host_present = decision.host_present and state.host_enabled
            shot.host_role = decision.host_role
        shot.prompt, shot.negative_prompt, _ = composer.compose(state, shot)
        shot.status = "pending"; shot.prompt_hash = None
    return plan
