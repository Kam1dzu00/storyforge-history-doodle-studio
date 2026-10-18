from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .schemas import EngineRoute, MotionSemantics, Shot
from .util import run


class HybridStyleProfile(BaseModel):
    style_id: str
    palette: dict[str, str]
    typography: dict[str, str]
    line_weight_px: list[float] = Field(min_length=1)
    shape_language: list[str] = Field(min_length=1)
    background_texture: str
    character_proportions: str
    shadow_softness: str
    transition_rhythm: str


class MimicSceneContract(BaseModel):
    id: str
    chapter: str
    route: Literal["mimic_native_scene", "mimic_overlay", "mimic_micro_character"]
    duration_sec: float = Field(gt=0)
    narration_span: str
    historical_subject: str
    visual_goal: str
    must_show: list[str] = Field(min_length=1)
    must_not_show: list[str] = Field(default_factory=list)
    movement: str
    style: str

    @model_validator(mode="after")
    def validate_motion(self):
        if len(self.movement.split()) < 3:
            raise ValueError("movement must describe a concrete visual change")
        if self.route == "mimic_overlay" and not self.visual_goal:
            raise ValueError("overlay scene requires a visual goal")
        return self

    def motion_semantics(self) -> MotionSemantics:
        first, _, last = self.movement.partition(";")
        return MotionSemantics(
            moving_element=self.historical_subject,
            narrative_purpose=self.visual_goal,
            start_state=first.strip(),
            end_state=(last or first).strip(),
            intensity="moderate" if self.route == "mimic_native_scene" else "subtle",
            alpha_required=self.route == "mimic_overlay",
        )


class HybridGateResult(BaseModel):
    passed: bool
    semantic_match: bool
    style_match: bool
    product_deck_clean: bool
    useful_motion: bool
    composition_variety: bool
    anatomy_clean: bool
    typography_clean: bool
    notes: list[str] = Field(default_factory=list)


PRODUCT_DECK_SIGNALS = (
    "floating rounded cards", "generic icon grid", "abstract gradient",
    "startup promo", "dashboard", "saas", "corporate choreography",
)


def detect_product_deck_contamination(description: str) -> list[str]:
    text = description.lower()
    return [signal for signal in PRODUCT_DECK_SIGNALS if signal in text]


def load_contracts(path: Path, expected_style: str = "calm_animated_editorial_2d") -> list[MimicSceneContract]:
    contracts = [MimicSceneContract.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]
    ids = [item.id for item in contracts]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate Mimic scene contract id")
    wrong = [item.id for item in contracts if item.style != expected_style]
    if wrong:
        raise ValueError(f"Mimic contracts use the wrong shared style: {', '.join(wrong)}")
    return contracts


def route_shot(shot: Shot, contract: MimicSceneContract | None = None) -> Shot:
    """Apply only an explicit scoped contract; StoryForge remains the default."""
    if contract is None:
        if shot.engine_route == "auto":
            shot.engine_route = "storyforge"
        return shot
    shot.engine_route = contract.route
    shot.mimic_contract_id = contract.id
    shot.motion_semantics = contract.motion_semantics()
    shot.hybrid_status = "planned"
    return shot


def probe_alpha(path: Path) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt", "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return "a" in result.stdout.strip().lower()


def encode_alpha_overlay(frame_pattern: Path, output: Path, fps: int = 30) -> Path:
    """Encode RGBA PNG frames losslessly; never key a black background."""
    output.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-framerate", str(fps), "-i", str(frame_pattern), "-c:v", "qtrle", "-pix_fmt", "argb", str(output)])
    if not probe_alpha(output):
        raise RuntimeError("alpha overlay export did not preserve an alpha pixel format")
    return output


def composite_overlay(base_video: Path, overlay_video: Path, output: Path) -> Path:
    if not probe_alpha(overlay_video):
        raise ValueError("overlay must contain a real alpha channel")
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-i", str(base_video), "-i", str(overlay_video),
        "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1:format=auto[v]",
        "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", str(output),
    ])
    return output


def require_shared_style_gate(results: dict[str, HybridGateResult]) -> None:
    required = {"opening", "water_bowl", "final_rescue"}
    missing = required - set(results)
    failed = sorted(name for name, result in results.items() if name in required and not result.passed)
    if missing or failed:
        details = []
        if missing: details.append("missing=" + ",".join(sorted(missing)))
        if failed: details.append("failed=" + ",".join(failed))
        raise RuntimeError("FULL_EPISODE_BLOCKED_BY_SHARED_STYLE_GATE: " + "; ".join(details))
