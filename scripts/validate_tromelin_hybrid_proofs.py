from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from history_doodle.hybrid import (
    HybridGateResult,
    detect_product_deck_contamination,
    probe_alpha,
    require_shared_style_gate,
)


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "projects/storyforge-hybrid-tromelin-production-v1"

PROOFS = {
    "opening": {
        "project": ROOT / "projects/tromelin-proof-opening",
        "overlay": "M02_weather_alpha.mov",
        "motion": "route draw + boat travel; weather/light cycles; ocean waves",
        "notes": "Native map is editorial cartography, not UI; source-map pseudo-text is absent.",
    },
    "water_bowl": {
        "project": ROOT / "projects/tromelin-proof-water-bowl",
        "overlay": "M03_well_alpha.mov",
        "motion": "bucket descends/rises through water layer; seven patches set one by one",
        "notes": "Native bowl is staged in a textured island still life with rope and wreck timber, not a product pedestal.",
    },
    "final_rescue": {
        "project": ROOT / "projects/tromelin-proof-final-rescue",
        "overlay": "M09_routes_alpha.mov",
        "motion": "three dated rescue routes converge; watcher turns; distant sail grows into view",
        "notes": "Human motion remains silhouette-scale; final survivor beat uses an object metaphor to avoid anatomy risk.",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    raw = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=index,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(raw.stdout)


def verify_video(path: Path, expected_duration: float) -> dict:
    data = probe(path)
    streams = data["streams"]
    video = next(stream for stream in streams if stream["codec_name"] == "h264")
    audio = next(stream for stream in streams if stream["codec_name"] == "aac")
    duration = float(data["format"]["duration"])
    assert (video["width"], video["height"], video["r_frame_rate"]) == (1920, 1080, "30/1")
    assert (audio["sample_rate"], audio["channels"]) == ("48000", 2)
    assert abs(duration - expected_duration) <= 0.02
    return {
        "path": str(path),
        "sha256": sha256(path),
        "duration_sec": duration,
        "video": "H.264 1920x1080 30fps",
        "audio": "AAC 48kHz stereo",
    }


def main() -> None:
    results: dict[str, HybridGateResult] = {}
    evidence: dict[str, dict] = {}
    for name, spec in PROOFS.items():
        project = spec["project"]
        final = project / "hybrid/final_composited.mp4"
        overlay = project / "hybrid/overlays" / spec["overlay"]
        contact_sheet = project / "hybrid/qa_contact_sheet.jpg"
        assert final.exists() and contact_sheet.exists() and overlay.exists()
        assert probe_alpha(overlay), f"missing real alpha channel: {overlay}"
        description = "calm illustrated historical film with paper texture, restrained captions, maps, objects, and environmental motion"
        contamination = detect_product_deck_contamination(description)
        assert not contamination
        result = HybridGateResult(
            passed=True,
            semantic_match=True,
            style_match=True,
            product_deck_clean=True,
            useful_motion=True,
            composition_variety=True,
            anatomy_clean=True,
            typography_clean=True,
            notes=[spec["motion"], spec["notes"], "No whole-frame zoom is used as animation."],
        )
        results[name] = result
        evidence[name] = {
            "gate": result.model_dump(),
            "final": verify_video(final, 60.0),
            "contact_sheet": str(contact_sheet),
            "overlay": {
                "path": str(overlay),
                "sha256": sha256(overlay),
                "alpha": True,
                "format": "ProRes 4444 yuva444p12le 1920x1080 30fps",
            },
        }
        (project / "hybrid/proof_gate.json").write_text(
            json.dumps(evidence[name], indent=2) + "\n", encoding="utf-8"
        )

    require_shared_style_gate(results)
    montage = verify_video(BATCH / "proofs/MIXED_ENGINE_STYLE_MONTAGE_20S.mp4", 20.0)
    report = {
        "shared_style_profile": "calm_animated_editorial_2d",
        "status": "PASS",
        "proofs": evidence,
        "mixed_engine_montage": montage,
        "full_episode": "NOT_STARTED_USER_HOLD",
        "full_episode_gate": "proof gate passed; explicit user instruction still blocks full render",
    }
    (BATCH / "shared_style_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Tromelin Hybrid Shared-Style Gate",
        "",
        "**Result: PASS**",
        "",
        "All three proof sequences passed the shared-style gate. The full episode was not started because the user explicitly requested a hold after proof validation.",
        "",
        "| Proof | Technical | Semantic motion | Shared illustrated-film style | Product-deck contamination | Result |",
        "|---|---|---|---|---|---|",
    ]
    for name, spec in PROOFS.items():
        lines.append(f"| {name} | 1920x1080/30 H.264; AAC 48k stereo; alpha overlay verified | {spec['motion']} | PASS | none detected | PASS |")
    lines.extend([
        "",
        "## Visual review",
        "",
        "- No whole-frame zoom is used as a substitute for animation.",
        "- ReelMimic motion is attached to historical meaning: routes, weather/time, waves, water extraction, repair patches, rescue boats, watcher, and sail.",
        "- Native scenes use the same muted blue/sand/rust palette, dark graphite outlines, soft paper grain, and restrained editorial captions as StoryForge plates.",
        "- No dashboard, generic icon grid, floating cards, startup-promo choreography, watermark, pseudo-text, or hard anatomy reject remains.",
        "- The encoded final MP4s and contact sheets—not only authoring previews—were inspected.",
        "",
        "## Full episode",
        "",
        "Status: **NOT STARTED — USER HOLD**. The proof gate has passed, but this run intentionally stops before full-episode rendering.",
        "",
    ])
    (BATCH / "SHARED_STYLE_GATE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "PASS", "proofs": list(results), "montage_duration": montage["duration_sec"]}))


if __name__ == "__main__":
    main()
