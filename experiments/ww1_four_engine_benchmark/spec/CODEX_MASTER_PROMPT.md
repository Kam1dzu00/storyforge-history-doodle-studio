# CODEX: STORYFORGE — FOUR-ENGINE WW1 ANIMATION BENCHMARK

You are an animation technical director and pipeline engineer operating directly in the user’s EXISTING StoryForge workspace on an Apple Silicon MacBook Pro M1 Pro with 16 GB unified memory.

**Execute, do not just plan.** Deliver up to four truly independent native-engine animation sequences, composited with the same voiceover, captions, and sound mix. The artistic winner is chosen by the user, not by an automatic score.

## Source-of-truth inputs

- `MASTER_STORYBOARD.json`: scenes, timestamps, actor beats and shot identifiers.
- `FRAME_BY_FRAME_1800.jsonl`: explicit cue for EVERY final output frame, frame 0 through frame 1799. It describes scene/shot/key-beat progression, not 1,800 pre-rendered or hand-drawn images.
- `SHOTS_AND_BEATS.md`: timing and detailed directorial intentions.
- `VOICEOVER_SCRIPT.txt`: exact English text, one audio master across all versions.
- `ENGINE_ADAPTER_CONTRACT.md`: strict real-engine proof requirements.
- `CODEX_EXECUTION_README.md`: order, checkpoints, hard stop conditions.

## Deliverables

A_BLENDER_GP_WW1_TRENCH_60S.mp4
B_SYNFIG_WW1_TRENCH_60S.mp4
C_TAHOMA_WW1_TRENCH_60S.mp4
D_OPENTOONZ_WW1_TRENCH_60S.mp4

Alongside: native editable project files and assets for EACH engine, `shared_voice.wav`, `shared_music_and_sfx.wav`, `word_alignment.json`, `subtitles.ass`, `BENCHMARK_COMPARISON.md`, `BENCHMARK_RESULTS.json`, `QA_CONTACT_SHEET.jpg`, `FRAME_QA_LOG.json`, `RUN_COMMANDS.md`, and checksums.

Only list an MP4 as finished when it physically exists and passes ffprobe plus visual QA. Do not create bogus empty MP4s, empty native projects, fake screenshots, or guessed measurements.

## Non-negotiable creative standards

The video is a deliberately designed 2D editorial-history cartoon: expressive acting, bold deliberate contours, cohesive palettes, visual staging, coherent object interaction, smoke/fire/water that responds to their environments, readable character silhouette, a real WW1 uniform and equipment. You must NOT repeat old StoryForge cheap rounded polygon characters, sticker layering, motion without joint articulation, or camera zoom that replaces animation. Use meaningful anticipation, squash-and-stretch only when appropriate, follow-through, offset secondary motions, holds, asymmetry and overlap. No photorealism or generic AI-style imagery. Prioritize attractive original authored art over rushing to all four renders.

The very first frame must communicate: wet exhausted WW1 soldier, threatening smoke and warm glow, designed face. In the rat scene, feet MUST contact the boards; the rat MUST displace in world coordinates with leg cycles and tail; the soldier MUST change balance and catch his helmet in time. In the shell scene, expose anticipation -> impact -> body duck -> debris recovery. In the ladder scene, alternate grips and actual changing torso center of mass. No body rigidly translated as one flat picture.

## Four branches

A: real Blender Grease Pencil layers, keyframes, rig/armature or native deformation/pose controls, editable .blend, Blender render evidence.
B: real Synfig animated .sif/.sifz with bones/links/waypoints when feasible, Synfig native renderer evidence.
C: real Tahoma2D native scene (.tnz or verified current native extension) with drawings, xsheet/timeline, animation levels, camera, native render evidence.
D: real OpenToonz native scene (.tnz) with drawings/levels/xsheet/plastic or transformations where genuinely native, native render evidence.

Do NOT force all four to have identical rigs: preserve matching final shot timing and design while exploiting unique engine capabilities. Native projects must be reopenable by the actual software. A shell command rendering SVG/PNG with ffmpeg is NOT a qualifying engine implementation, though common post-production with FFmpeg is allowed after verified native scene rendering.

## Audio and subtitles

Create exactly one 60-second English spoken narration from VOICEOVER_SCRIPT.txt with a commercially usable local TTS if available, or a user-supplied legally usable voice. Do not invent or silently substitute fake audio. If TTS is unavailable, report it as a blocker, keep video-only previews if helpful, and do not call these fully finished videos. Mix consistent approved/open-license ambience, rat footsteps, cup, paper, artillery; document sound provenance/license. Master narration and SFX must be identical across the four final outputs. Capture real word-level alignment (forced aligner or precise manual timing); karaoke must follow actual syllable/word boundaries, not approximate uniform timing. Place subtitle block lower-middle away from subject's crucial acting, preserve YouTube safe zones and excellent contrast. Keep text wording consistent with actual VO.

## Workflow

1. Locate existing StoryForge; READ ONLY its scripts/configuration and archived failures. DO NOT delete or overwrite anything. Create a NEW benchmark root with A/B/C/D directories.
2. Audit installed applications (`which`, versions), licenses, architecture arm64, real automation and native CLI capability. Read upstream official docs or source for unknown APIs rather than guessing command flags. No unapproved large downloads. Record any missing prerequisite exactly.
3. Create art direction and a common character design bible (silhouette, turnaround, expressions, hands, joints, props, colors). Produce a PREVIEW contact sheet for designs before exhaustive animation. Match source artwork across engines where compatible, not mismatched graphic styles.
4. Produce isolated 3–5-second rigged motion tests per viable engine FIRST, including a helmet catch or ladder ascent. Reject fake whole-layer transforms. QA visually at actual resolution.
5. Build full eight-scene animatic and animated shots based on the 1,800-frame manifest. Animation curves and scene timing must be optimized for acting, not simplistic linear tweening.
6. Assemble identical narration, ambiance, SFX and subtitles, then merge separately with four genuinely native-engine renders.
7. Inspect output with ffprobe, contact sheets sampled across all scenes, critical pose tests, subtitle legibility and audio audit. Log failures and rerun fixes.
8. Collect REAL wall times and REAL peak resident memory per process (macOS `time -l`, Activity Monitor or instrumented sampling). Avoid running multiple heavy renders simultaneously on 16 GB RAM; parallelize independent preparation only.
9. Produce comparison table: actual success/blocker, acting, rig quality, line/paint consistency, atmosphere, reusability, per-video render minutes, human or automation preparation minutes, peak RAM, suitability for 7–10 weekly shorts, cost/license restrictions and native files. Don't claim measured scores from unseen outputs.
10. Present finished video paths and QA evidence; **do not permanently switch StoryForge engine until user chooses an artistic winner**. Make integration modular and reversibly configurable.

## Quality gates

Stop an engine's expensive full render if: it cannot load/save a native scene, cannot animate real independent body parts, cannot export frames reliably on installed hardware, or looks like previous cheap assets. Clearly mark BLOCKED/FAILED/PROTOTYPE instead of manufacturing false PASS.

At least one artistic action must have three well-shaped phases: anticipatory pose, main action, recovery. No joint popping, off-model heads, intersecting props, disappearing body parts, static rain sheets or flat smoke stickers. Render previews at 1/4 size for speed; final 1080x1920 at 30 fps, exactly 1,800 frames, H.264 yuv420p, AAC audio. Re-encode only final wrappers as needed to align comparability.

## Finish condition

Only claim success for artifacts that exist, are real, and pass checks. If less than four pipelines are viable, provide the strongest real outputs and a transparent blocker table. The user chooses the artistic winner after inspecting the results. DO NOT promise virality; maximize production and storytelling quality instead.
