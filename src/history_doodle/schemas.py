from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Motion = Literal["slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right", "subtle_push", "static"]
EngineRoute = Literal["storyforge", "mimic_native_scene", "mimic_overlay", "mimic_micro_character", "auto"]
VisualType = Literal["CHARACTER_WIDE", "CHARACTER_MEDIUM", "CHARACTER_CLOSEUP", "OBJECT_HERO", "OBJECT_COLLECTION", "DETAIL", "ENVIRONMENT", "INFO_CARD", "MAP", "COMPARISON", "SILHOUETTE", "GROUP"]
SubjectPlacement = Literal["LEFT_THIRD","RIGHT_THIRD","LOWER_LEFT","LOWER_RIGHT","FOREGROUND_LEFT","FOREGROUND_RIGHT","SMALL_IN_ENVIRONMENT","OFF_CENTER","CENTERED_OBJECT","CENTERED_CHARACTER"]
CameraAngle = Literal["EYE_LEVEL","SLIGHT_LOW","SLIGHT_HIGH","THREE_QUARTER","PROFILE","OVER_SHOULDER","TOP_DOWN_OBJECT","FRONTAL_OBJECT"]
Framing = Literal["WIDE","MEDIUM_WIDE","MEDIUM","CLOSEUP","DETAIL","ENVIRONMENTAL_WIDE"]

class QuestionBeat(BaseModel):
    """Structured long-form retention beat with deterministic presentation."""
    question_text: str = Field(min_length=1)
    pause_before_ms: int = Field(default=850, ge=600, le=1200)
    voice_mode: Literal["QUESTION"] = "QUESTION"
    question_speed: float = Field(default=0.86, ge=0.84, le=0.90)
    background_visual: str
    question_card_min_ms: int = Field(default=5200, ge=3000, le=10000)
    question_card_max_ms: int = Field(default=7600, ge=3000, le=12000)
    pause_after_ms: int = Field(default=750, ge=600, le=1100)
    music_duck_db: float = Field(default=8.0, ge=6.0, le=9.0)
    text_animation: Literal["slow_fade_drift"] = "slow_fade_drift"

    @model_validator(mode="after")
    def valid_card_range(self):
        if self.question_card_max_ms < self.question_card_min_ms:
            raise ValueError("question_card_max_ms must be >= question_card_min_ms")
        return self

class MotionSemantics(BaseModel):
    """A scoped, testable explanation of why a hybrid scene moves."""
    moving_element: str = Field(min_length=1)
    narrative_purpose: str = Field(min_length=1)
    start_state: str = Field(min_length=1)
    end_state: str = Field(min_length=1)
    intensity: Literal["subtle", "moderate", "strong"] = "subtle"
    alpha_required: bool = False

class CharacterCard(BaseModel):
    id: str
    name: str
    role: str
    visual_identity: str
    fixed_traits: list[str] = Field(default_factory=list)

class Shot(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    scene_id: str
    order: int
    narration_context: str
    visual_subject: str
    location: str
    action: str
    historical_props: list[str] = Field(default_factory=list)
    character_ids: list[str] = Field(default_factory=list)
    composition: str
    camera_motion: Motion = "static"
    prompt: str
    negative_prompt: str
    seed: int
    estimated_duration: float = Field(ge=3, le=10)
    start_time: float | None = None
    end_time: float | None = None
    image_path: str | None = None
    prompt_hash: str | None = None
    status: Literal["pending", "stale", "generating", "complete", "failed"] = "pending"
    visual_type: VisualType = "CHARACTER_MEDIUM"
    people_count: int = Field(default=1, ge=0, le=20)
    objects: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    background_style: str = ""
    director_override: bool = False
    visual_purpose: str = "show the concrete narration beat"
    subject_placement: SubjectPlacement = "OFF_CENTER"
    camera_angle: CameraAngle = "EYE_LEVEL"
    framing: Framing = "MEDIUM"
    foreground_elements: list[str] = Field(default_factory=list)
    midground_elements: list[str] = Field(default_factory=list)
    background_elements: list[str] = Field(default_factory=list)
    environment_context: str = "specific historically appropriate setting"
    historical_story_details: list[str] = Field(default_factory=list)
    action_description: str = "performing the concrete action described by the narration"
    negative_space_direction: str = "opposite the main subject"
    centered_justification: str = ""
    continuity_key: str = ""
    time_of_day: str = ""
    weather: str = ""
    validation_checks: dict[str, bool] = Field(default_factory=dict)
    visual_category: str | None = None
    visual_focus: str | None = None
    host_present: bool | None = None
    host_expression: str | None = None
    host_pose: str | None = None
    host_role: str | None = None
    routing_source: Literal["auto", "manual"] = "auto"
    image_versions: list[dict] = Field(default_factory=list)
    approved: bool = False
    generated_at: str | None = None
    question_beat: QuestionBeat | None = None
    engine_route: EngineRoute = "storyforge"
    motion_semantics: MotionSemantics | None = None
    mimic_contract_id: str | None = None
    base_plate_path: str | None = None
    overlay_path: str | None = None
    hybrid_status: Literal["not_applicable", "planned", "rendered", "approved", "rejected", "fallback"] = "not_applicable"

class Scene(BaseModel):
    id: str
    section_id: str
    order: int
    narration_text: str
    shot_ids: list[str]
    start_time: float | None = None
    end_time: float | None = None

class StorySection(BaseModel):
    id: str
    title: str
    purpose: str
    scene_ids: list[str]

class ProjectPlan(BaseModel):
    sections: list[StorySection]
    scenes: list[Scene]
    shots: list[Shot]
    characters: list[CharacterCard] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_links(self):
        scene_ids = {x.id for x in self.scenes}
        shot_ids = {x.id for x in self.shots}
        char_ids = {x.id for x in self.characters}
        for section in self.sections:
            if not set(section.scene_ids) <= scene_ids:
                raise ValueError(f"Unknown scene in section {section.id}")
        for scene in self.scenes:
            if not set(scene.shot_ids) <= shot_ids:
                raise ValueError(f"Unknown shot in scene {scene.id}")
        for shot in self.shots:
            if shot.scene_id not in scene_ids or not set(shot.character_ids) <= char_ids:
                raise ValueError(f"Broken shot references in {shot.id}")
        return self

class ProjectState(BaseModel):
    model_config = ConfigDict(extra="allow")
    project_id: str
    title: str
    input_mode: Literal["brief", "script"]
    language: str = "en"
    target_duration_seconds: int = 600
    style: str = "history_doodle_v1"
    voice: str = "am_michael"
    base_seed: int = 42000
    output_width: int = 1920
    output_height: int = 1080
    style_mode: str | None = None
    host_enabled: bool = False
    host_character_id: str | None = None
    semantic_visual_routing: bool = True
    full_bleed_frames: bool | None = None
    workflow_mode: Literal["guided", "advanced"] = "guided"
    auto_rebuild_after_approval: bool = True
    shot_version_limit: int = Field(default=4, ge=1, le=10)
    voice_preset: Literal["energetic_explainer", "friendly_documentary", "calm_history"] = "calm_history"
    speech_speed: float = Field(default=1.03, ge=0.75, le=1.25)
    music_profile: Literal["HISTORICAL_AMBIENCE", "BRIGHT_FACTS", "COLD_WAR_UNDERWATER_EDITORIAL"] = "HISTORICAL_AMBIENCE"
    background_music: str | None = None
    background_music_enabled: bool = False
    background_music_mode: Literal["user_file", "procedural"] = "procedural"
    background_music_gain_db: float = 0.0
    background_music_duck_db: float = 6.0
    background_music_question_duck_db: float = 8.0
    background_music_fade_in: float = 2.0
    background_music_fade_out: float = 5.0
    outro_enabled: bool = False
    outro_image_path: str | None = None
    pause_before_outro_ms: int = 1000
    outro_voice_mode: str = "OUTRO"
    outro_speed: float = 0.93
    outro_hold_after_ms: int = 1200
    outro_fade_to_black_ms: int = 700
    script_status: str = "pending"
    planning_status: str = "pending"
    voice_status: str = "pending"
    images_status: str = "pending"
    subtitles_status: str = "pending"
    render_status: str = "pending"
    hybrid_enabled: bool = False
    hybrid_style_profile: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WordStamp(BaseModel):
    word: str
    start: float
    end: float
    probability: float | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if self.start < 0 or self.end < self.start:
            raise ValueError("Invalid word timestamp range")
        return self
