# Engine-specific contract and evidence

## A — Blender Grease Pencil
- Audit installed Blender version first; 4.5/5.x APIs differ, so probe `bpy` and feature availability dynamically.
- Save .blend with grease-pencil layers and nontrivial animation (drawn cels, armature-driven controls, material/FX where applicable). Verify with a headless open and scene inspection.
- Prove active rig pose keys / character expression changes in native Blender file, not rendered PNG animated in another program.
- Export PNG sequence via actual Blender rendering. Native evidence: blender version, render command, open/save and frame screenshots/metadata.

## B — Synfig Studio
- Use valid native `.sif` or `.sifz` with animated waypoints/link hierarchy; bones if supported for used layer types.
- Check real CLI renderer (`synfig` binaries/version); do not assume any one command layout. Validate sample one frame and multiple animated frames first.
- Re-open scene in Synfig to confirm geometry and animation work.

## C — Tahoma2D
- Inspect installed version, supported macOS build, tcomposer or any real CLI/render export available. Confirm capabilities rather than assuming OpenToonz binary compatibility.
- Save native scene with xsheet levels, drawings, keys, and meaningful motion, and render using Tahoma2D native application/binary.
- If GUI-only process blocks noninteractive Codex use, mark as honest blocker. A Remotion recreation is not Tahoma.

## D — OpenToonz
- Verify OpenToonz native .tnz scene, level/drawing assets and xsheet, stage-object animation or plastic rig when legitimately supported, and native tcomposer or other verified renderer.
- Re-open native scene; verify frame sequences actually differ with character motion.

## Cross-engine proof bundle
For each branch save `NATIVE_PROOF.md` including application path, version/build, SHA256 of native project, documented invocation, logs, evidence frame filenames (frames 1, 75, 150, 360, 450, 750, 1080, 1350, 1799), any limitations. All render attempts must be independently reproducible.

Use common character bible but permit engine-specific rigging, native scene mechanics and compositing. Report engine-native rendering time separately from common FFmpeg finishing time.
