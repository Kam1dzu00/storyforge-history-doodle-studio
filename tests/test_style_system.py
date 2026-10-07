from __future__ import annotations

import json

import pytest

from history_doodle.schemas import ProjectState, Shot
from history_doodle.style_system import (
    FULL_BLEED_EXCLUSIONS,
    CharacterRegistry,
    LEGACY_STYLE_ID,
    PromptComposer,
    RegistryError,
    StyleRegistry,
    VisualRouter,
)
from history_doodle.image_worker import generation_kwargs, requires_host_conditioning


def shot(narration: str, **updates) -> Shot:
    values = dict(
        id="shot_001", scene_id="scene_001", order=1, narration_context=narration,
        visual_subject="the exact narrated subject", location="studio", action="explain",
        composition="dynamic asymmetry", prompt="legacy prompt", negative_prompt="legacy negative",
        seed=42, estimated_duration=4.0,
    )
    values.update(updates)
    return Shot(**values)


def bright_state(**updates) -> ProjectState:
    values = dict(project_id="qa", title="QA", input_mode="script", style_mode="bright_explainer_host")
    values.update(updates)
    return ProjectState(**values)


def test_legacy_state_loads_and_preserves_unknown_fields():
    state = ProjectState.model_validate({"project_id": "old", "title": "Old", "input_mode": "script", "future_field": "kept"})
    assert state.style_mode is None
    assert state.model_dump()["future_field"] == "kept"
    assert StyleRegistry().resolve_for_project(state)["style_id"] == LEGACY_STYLE_ID


def test_registry_lists_profiles_and_rejects_unknown_style():
    ids = {item["style_id"] for item in StyleRegistry().list_styles()}
    assert {LEGACY_STYLE_ID, "bright_explainer_host"} <= ids
    with pytest.raises(RegistryError, match="Unknown style ID"):
        StyleRegistry().get("does_not_exist")


@pytest.mark.parametrize(
    ("narration", "category", "host"),
    [
        ("It was 38 degrees.", "infographic_metric", False),
        ("Meningitis inflames the membrane around the brain.", "medical_diagram", False),
        ("This air conditioner is on the wall.", "object_single", False),
        ("I thought the air conditioner was trying to kill me.", "host_reaction", True),
        ("Imagine that?", "host_reaction", True),
    ],
)
def test_semantic_router(narration, category, host):
    decision = VisualRouter().route(narration)
    assert decision.visual_category == category
    assert decision.host_present is host


def test_manual_route_is_preserved():
    item = shot("38 degrees", visual_category="symbol_metaphor", visual_focus="a custom symbol", routing_source="manual")
    decision = VisualRouter().route(item.narration_context, item)
    assert (decision.visual_category, decision.visual_focus) == ("symbol_metaphor", "a custom symbol")


def test_non_host_prompt_is_deterministic_full_bleed_and_has_no_identity():
    state = bright_state(host_enabled=False)
    item = shot("It was 38 degrees.", visual_category="infographic_metric", visual_focus="a huge thermometer at 38 degrees", host_present=False)
    first = PromptComposer().compose(state, item)
    second = PromptComposer().compose(state, item)
    assert first == second
    assert first[2] == []
    assert "full-bleed" in first[0]
    assert "REAL IDENTITY REFERENCE" not in first[0]
    assert all(value in first[1] for value in FULL_BLEED_EXCLUSIONS)


def test_host_prompt_resolves_profile_without_claiming_backend_conditioning():
    state = bright_state(host_enabled=True, host_character_id="kam1dzu00_host")
    item = shot("Imagine that?", visual_category="host_reaction", visual_focus="the host reacting", host_present=True)
    prompt, _, refs = PromptComposer().compose(state, item, require_references=False)
    assert "tattoo on LEFT forearm" in prompt
    assert "watch on LEFT wrist" in prompt
    assert all(path.exists() for path in refs)


def test_host_backend_receives_real_then_character_sheet_references():
    state = bright_state(host_enabled=True, host_character_id="kam1dzu00_host")
    item = shot("Imagine that?", visual_category="host_reaction", visual_focus="the host reacting", host_present=True)
    _, _, refs = PromptComposer().compose(state, item, require_references=True)
    kwargs = generation_kwargs(state, item, "prompt", refs)
    assert requires_host_conditioning(state, item)
    assert kwargs["image_paths"][0].endswith("host_real_identity.jpg")
    assert kwargs["image_paths"][1].endswith("host_character_sheet_bright.png")


def test_non_host_backend_does_not_receive_host_references():
    state = bright_state(host_enabled=True, host_character_id="kam1dzu00_host")
    item = shot("This is an air conditioner.", visual_category="object_single", host_present=False)
    _, _, refs = PromptComposer().compose(state, item, require_references=True)
    kwargs = generation_kwargs(state, item, "prompt", refs)
    assert not requires_host_conditioning(state, item)
    assert "image_paths" not in kwargs


def test_missing_stylized_reference_falls_back_to_real_when_available(tmp_path, monkeypatch):
    real = tmp_path / "real.jpg"; real.write_bytes(b"real")
    characters = tmp_path / "characters"; characters.mkdir()
    (characters / "host.json").write_text(json.dumps({
        "character_id": "host", "reference_real_image_path": str(real),
        "reference_stylized_by_style": {"bright": str(tmp_path / "missing.png")},
    }))
    assert CharacterRegistry(characters).resolve_references("host", "bright") == [real]
