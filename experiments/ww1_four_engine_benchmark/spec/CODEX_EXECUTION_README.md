# START HERE — execution order

**Machine:** Apple Silicon M1 Pro / 16 GB. **Target:** vertical 60 seconds (1800 frames, 30 fps). **Input:** WW1 soldier / trench / rat / food / explosions / letter / climb / emotional ending. **Output:** four REAL engine outputs where feasible.

## Do immediately
1. In existing StoryForge create NEW `experiments/ww1_four_engine_benchmark/` without mutating old working files. Copy this pack there. Record git status first; never delete/archive prior assets without consent.
2. Read `CODEX_MASTER_PROMPT.md`, `MASTER_STORYBOARD.json`, `SHOTS_AND_BEATS.md`, `ENGINE_ADAPTER_CONTRACT.md`; run `python3 validate_pack.py`.
3. Detect true installed tools and file formats before installation: OS, arch, Blender, Synfig, Tahoma, OpenToonz, ffmpeg/ffprobe, TTS, subtitle tools.
4. Limit CPU/RAM contention: preparation tasks can parallelize; hardware-heavy renders execute one at a time with genuine RAM/time telemetry.
5. Render 3–5 sec gate tests for **all available** engines. Only those that pass native animation QA proceed to 60 sec.
6. Ensure every result uses ONE shared original asset bible and master voice WAV + mix; avoid one engine receiving superior artwork unless differences are an intentional metric disclosed in report.
7. Complete final export/QA as specified. Nothing is called finished until it exists and passes probes.

## Hard-stop vs salvage
- A native engine cannot save or reliably render a genuine native animation: BLOCKED, document dependency/version and screenshots/log; do not fake result.
- Audio TTS missing: video-only `PREVIEW_...` is allowed but not a finished voiceover MP4; note gap.
- Quality below threshold: improve faces/rigs/acting, don't flood the result with fake placeholders.
- Installed hardware cannot handle full scene: render per shot sequentially and composite with common finishing, retain native evidence.

## After review
Write `ENGINE_SELECTION_PENDING.md` with viable candidates and costs. Do not replace StoryForge default until the USER chooses the final artistic winner. Then integrate adapter with config switch and rollback.
