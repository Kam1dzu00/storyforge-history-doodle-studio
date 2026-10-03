from __future__ import annotations

from .schemas import ProjectPlan

def allocate_timeline(plan: ProjectPlan, duration: float) -> ProjectPlan:
    scenes = sorted(plan.scenes, key=lambda x: x.order)
    shots_by_id = {x.id: x for x in plan.shots}
    weights = [max(1, len(s.narration_text.split())) for s in scenes]
    cursor = 0.0
    for idx, scene in enumerate(scenes):
        scene_duration = duration * weights[idx] / sum(weights)
        scene.start_time = cursor; scene.end_time = duration if idx == len(scenes)-1 else cursor + scene_duration
        shots = [shots_by_id[x] for x in scene.shot_ids]
        if not shots: raise ValueError(f"Scene {scene.id} has no shots")
        share = (scene.end_time - scene.start_time) / len(shots)
        if share < 3 or share > 10: raise ValueError(f"Scene {scene.id} needs a different shot count; calculated shot duration {share:.2f}s")
        for j, shot in enumerate(shots):
            shot.start_time = scene.start_time + share*j
            shot.end_time = scene.end_time if j == len(shots)-1 else scene.start_time + share*(j+1)
            shot.estimated_duration = shot.end_time - shot.start_time
        cursor = scene.end_time
    return plan

def validate_word_timestamps(words, audio_duration: float) -> list[str]:
    warnings = []
    previous = 0.0
    for index, word in enumerate(words):
        if word.start < previous - .001: raise ValueError(f"Word timestamp {index} is not monotonic")
        if word.end > audio_duration + .25: raise ValueError(f"Word timestamp {index} exceeds audio duration")
        gap = word.start - previous
        if gap > .7: warnings.append(f"Long silence {gap:.2f}s before word {index + 1}")
        previous = word.end
    return warnings
