from __future__ import annotations

import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "A_blender_gp"
(OUT / "native").mkdir(parents=True, exist_ok=True)
(OUT / "gate" / "frames").mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 540
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 150
scene.world = bpy.data.worlds.new("WW1_GATE_WORLD")
scene.world.color = (0.025, 0.04, 0.05)
scene.render.filepath = str(OUT / "gate" / "frames" / "frame_")

camera_data = bpy.data.cameras.new("WW1_GATE_CAMERA")
camera = bpy.data.objects.new("WW1_GATE_CAMERA", camera_data)
bpy.context.collection.objects.link(camera)
camera.location = (0, 0, 12)
camera_data.type = "ORTHO"
camera_data.ortho_scale = 16.0
scene.camera = camera


def rgba(hex_value: str, alpha: float = 1.0):
    h = hex_value.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) + (alpha,)


def gp_material(name: str, fill: str, stroke: str = "#18232B", width: float = 0.075):
    mat = bpy.data.materials.new(name)
    bpy.data.materials.create_gpencil_data(mat)
    gp = mat.grease_pencil
    gp.show_fill = True
    gp.show_stroke = True
    gp.fill_color = rgba(fill)
    gp.color = rgba(stroke)
    gp.mode = "LINE"
    gp.pixel_size = width * 1000
    return mat


MATS = {
    "coat": gp_material("MAT_COAT", "#465747"),
    "coat_dark": gp_material("MAT_COAT_DARK", "#33454C"),
    "skin": gp_material("MAT_SKIN", "#B1A68B"),
    "helmet": gp_material("MAT_HELMET", "#33454C"),
    "mud": gp_material("MAT_MUD", "#685342"),
    "rat": gp_material("MAT_RAT", "#8F8064"),
    "eye": gp_material("MAT_EYE", "#D0D5CC"),
    "pupil": gp_material("MAT_PUPIL", "#18232B"),
    "fire": gp_material("MAT_FIRE", "#C16C3A"),
}


def make_shape(name: str, points, material, z: float, layer_name: str | None = None):
    data = bpy.data.grease_pencils_v3.new(name + "_GP")
    layer = data.layers.new(layer_name or name, set_active=True)
    drawing = layer.frames.new(1).drawing
    drawing.add_strokes([len(points)])
    stroke = drawing.strokes[0]
    stroke.cyclic = True
    stroke.material_index = 0
    for point, co in zip(stroke.points, points):
        point.position = (float(co[0]), float(co[1]), 0.0)
        point.radius = 0.07
        point.opacity = 1.0
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.location.z = z
    return obj


def ellipse(name, rx, ry, material, z, segments=48):
    pts = [(math.cos(i * math.tau / segments) * rx, math.sin(i * math.tau / segments) * ry)
           for i in range(segments)]
    return make_shape(name, pts, material, z)


def key(obj, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        obj.location.x, obj.location.y = loc
        obj.keyframe_insert("location", frame=frame)
    if rot is not None:
        obj.rotation_euler.z = rot
        obj.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = (scale[0], scale[1], 1)
        obj.keyframe_insert("scale", frame=frame)


# Layered trench background: each plane is genuine Grease Pencil geometry.
make_shape("SKY", [(-4.5, -8), (4.5, -8), (4.5, 8), (-4.5, 8)], MATS["coat_dark"], -1.0, "BG_SKY")
make_shape("TRENCH_WALL_LEFT", [(-4.5, -8), (-0.7, -8), (-1.3, 8), (-4.5, 8)], MATS["mud"], 0.0, "BG_MUD_LEFT")
make_shape("TRENCH_WALL_RIGHT", [(0.9, -8), (4.5, -8), (4.5, 8), (1.6, 8)], MATS["mud"], 0.1, "BG_MUD_RIGHT")

# Articulated soldier built from independent native Grease Pencil objects.
torso = make_shape("SOLDIER_TORSO", [(-1.65, -4.1), (1.55, -4.0), (1.25, 2.2), (-1.2, 2.4)], MATS["coat"], 2.0, "CHAR_TORSO")
neck = make_shape("SOLDIER_NECK", [(-0.55, 1.7), (0.55, 1.7), (0.48, 2.9), (-0.48, 2.9)], MATS["skin"], 2.1, "CHAR_NECK")
head = ellipse("SOLDIER_HEAD", 1.25, 1.55, MATS["skin"], 2.3)
head.location.y = 3.75
helmet = make_shape("HELMET_PROP", [(-1.7, -0.1), (-1.3, 0.72), (-0.55, 1.12), (0.55, 1.12), (1.35, 0.65), (1.75, -0.05), (1.25, -0.30), (-1.25, -0.30)], MATS["helmet"], 3.0, "PROP_HELMET")
helmet.location.y = 5.0
left_arm = make_shape("ARM_LEFT", [(-0.45, -2.2), (0.45, -2.2), (0.35, 2.2), (-0.35, 2.2)], MATS["coat"], 2.2, "RIG_ARM_L")
left_arm.location = (-1.65, -0.4, 2.2)
left_arm.rotation_euler.z = -0.30
right_arm = make_shape("ARM_RIGHT", [(-0.45, -2.2), (0.45, -2.2), (0.35, 2.2), (-0.35, 2.2)], MATS["coat"], 2.2, "RIG_ARM_R")
right_arm.location = (1.65, -0.4, 2.2)
right_arm.rotation_euler.z = 0.30
left_hand = ellipse("HAND_LEFT", 0.48, 0.58, MATS["skin"], 2.5)
right_hand = ellipse("HAND_RIGHT", 0.48, 0.58, MATS["skin"], 2.5)
left_hand.location = (-2.8, -2.0, 2.5)
right_hand.location = (2.8, -2.0, 2.5)
eye_l = ellipse("EYE_LEFT", 0.28, 0.13, MATS["eye"], 3.0, 32)
eye_r = ellipse("EYE_RIGHT", 0.28, 0.13, MATS["eye"], 3.0, 32)
pupil_l = ellipse("PUPIL_LEFT", 0.09, 0.1, MATS["pupil"], 3.2, 24)
pupil_r = ellipse("PUPIL_RIGHT", 0.09, 0.1, MATS["pupil"], 3.2, 24)
for obj, x in ((eye_l, -0.46), (pupil_l, -0.46), (eye_r, 0.46), (pupil_r, 0.46)):
    obj.location = (x, 4.0, obj.location.z)

rat = make_shape("RAT_BODY", [(-1.3, -0.35), (-0.75, -0.75), (0.35, -0.72), (1.2, -0.2), (1.0, 0.35), (0.1, 0.68), (-0.9, 0.52)], MATS["rat"], 4.0, "PROP_RAT")
rat.location = (-5.5, -5.6, 4.0)

# Native transform animation: body recoil, independent arms/hands, flying helmet,
# facial blink and a crossing rat. This is deliberately more than camera motion.
for f, y, r in [(1, 0.0, 0.0), (45, 0.15, -0.02), (72, -0.45, 0.06), (92, 0.1, -0.03), (150, 0.0, 0.0)]:
    key(torso, f, (0, y), r)
    key(neck, f, (0, y), r)
    key(head, f, (0, 3.75 + y), r)

for f, r in [(1, -0.30), (55, -0.25), (74, -1.25), (92, -0.55), (150, -0.30)]:
    key(left_arm, f, (-1.65, -0.4), r)
for f, r in [(1, 0.30), (55, 0.25), (74, 1.25), (92, 0.55), (150, 0.30)]:
    key(right_arm, f, (1.65, -0.4), r)
for f, loc in [(1, (-2.8, -2.0)), (55, (-2.6, -1.8)), (74, (-1.4, 4.85)), (92, (-1.0, 4.8)), (150, (-2.8, -2.0))]:
    key(left_hand, f, loc, -0.1)
for f, loc in [(1, (2.8, -2.0)), (55, (2.6, -1.8)), (74, (1.4, 4.85)), (92, (1.0, 4.8)), (150, (2.8, -2.0))]:
    key(right_hand, f, loc, 0.1)
for f, loc, rot in [(1, (0, 5.0), 0), (48, (0, 5.0), 0), (70, (0.2, 7.5), 0.35), (88, (0, 5.15), -0.1), (150, (0, 5.0), 0)]:
    key(helmet, f, loc, rot)
for eye in (eye_l, eye_r, pupil_l, pupil_r):
    x = eye.location.x
    for f, sy in [(1, 1.0), (38, 1.0), (42, 0.08), (46, 1.0), (112, 1.0), (116, 0.08), (120, 1.0), (150, 1.0)]:
        key(eye, f, (x, 4.0), 0, (1.0, sy))
for f, x, y, rot in [(1, -5.5, -5.6, 0), (25, -3.2, -5.2, 0.04), (55, 0.0, -5.5, -0.08), (85, 3.2, -5.1, 0.05), (110, 5.5, -5.4, 0)]:
    key(rat, f, (x, y), rot)

# Smooth Bézier interpolation where supported.
for obj in bpy.context.scene.objects:
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "native" / "blender_gp_native_gate.blend"))
bpy.ops.render.render(animation=True)
