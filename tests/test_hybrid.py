import json

import pytest

from history_doodle.hybrid import (
    HybridGateResult,
    MimicSceneContract,
    detect_product_deck_contamination,
    load_contracts,
    require_shared_style_gate,
    route_shot,
)
from history_doodle.schemas import Shot


def shot():
    return Shot(id="s1", scene_id="scene", order=1, narration_context="A route crosses the ocean.", visual_subject="island map", location="Indian Ocean", action="route grows", composition="wide", prompt="x", negative_prompt="x", seed=1, estimated_duration=4)


def contract():
    return MimicSceneContract(id="M01", chapter="OPEN", route="mimic_overlay", duration_sec=4, narration_span="A route crosses the ocean.", historical_subject="ship route", visual_goal="show isolation", must_show=["island"], must_not_show=["dashboard"], movement="route begins at Madagascar; route reaches Tromelin", style="calm_animated_editorial_2d")


def test_explicit_contract_routes_and_requires_alpha():
    routed = route_shot(shot(), contract())
    assert routed.engine_route == "mimic_overlay"
    assert routed.motion_semantics and routed.motion_semantics.alpha_required
    assert routed.hybrid_status == "planned" and routed.mimic_contract_id == "M01"


def test_auto_without_contract_falls_back_to_storyforge():
    value = shot(); value.engine_route = "auto"
    assert route_shot(value).engine_route == "storyforge"


def test_product_deck_detector_is_literal_and_auditable():
    assert detect_product_deck_contamination("A generic icon grid on an abstract gradient") == ["generic icon grid", "abstract gradient"]
    assert detect_product_deck_contamination("A repaired bowl on sand") == []


def test_contract_loader_rejects_style_drift(tmp_path):
    value = contract().model_dump(); value["style"] = "other"
    path = tmp_path / "contracts.json"; path.write_text(json.dumps([value]))
    with pytest.raises(ValueError, match="wrong shared style"):
        load_contracts(path)


def test_full_episode_gate_requires_all_three_proofs():
    passed = HybridGateResult(passed=True, semantic_match=True, style_match=True, product_deck_clean=True, useful_motion=True, composition_variety=True, anatomy_clean=True, typography_clean=True)
    require_shared_style_gate({"opening": passed, "water_bowl": passed, "final_rescue": passed})
    failed = passed.model_copy(update={"passed": False})
    with pytest.raises(RuntimeError, match="FULL_EPISODE_BLOCKED"):
        require_shared_style_gate({"opening": passed, "water_bowl": failed})
