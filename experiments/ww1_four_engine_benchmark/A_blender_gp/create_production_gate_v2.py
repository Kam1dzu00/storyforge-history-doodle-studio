from __future__ import annotations

import math
import os
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "A_blender_gp"
RIG = ROOT / "shared/art/character_rig_v1"
BG = ROOT / "shared/art/backgrounds/trench_dawn_master_v1.png"
(OUT / "native").mkdir(parents=True, exist_ok=True)
(OUT / "gate_v2" / "frames").mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 540
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 150
scene.render.filepath = str(OUT / "gate_v2" / "frames" / "frame_")
scene.world = bpy.data.worlds.new("WW1_WORLD")
scene.world.color = (0.03, 0.035, 0.04)

cam_data = bpy.data.cameras.new("CAMERA")
cam = bpy.data.objects.new("CAMERA", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (0, 0, 24)
cam_data.type = "ORTHO"
cam_data.ortho_scale = 16.0
scene.camera = cam


def image_material(name: str, path: Path):
    image = bpy.data.images.load(str(path), check_existing=True)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.surface_render_method = "DITHERED"
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    mat.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    mat.node_tree.links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    shader.inputs["Roughness"].default_value = 1.0
    shader.inputs["Specular IOR Level"].default_value = 0.0
    mat.node_tree.links.new(texture.outputs["Color"], shader.inputs["Emission Color"])
    shader.inputs["Emission Strength"].default_value = 0.75
    mat.node_tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return mat, image


def sprite(name: str, path: Path, height: float, location, z: float, pivot="center"):
    mat, image = image_material("MAT_" + name, path)
    width = height * image.size[0] / image.size[1]
    if pivot == "top":
        y0, y1 = -height, 0.0
    else:
        y0, y1 = -height / 2, height / 2
    verts = [(-width / 2, y0, 0), (width / 2, y0, 0), (width / 2, y1, 0), (-width / 2, y1, 0)]
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    for loop, co in zip(mesh.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop.index].uv = co
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj.location = (*location, z)
    return obj


def key(obj, frame, location=None, rotation=None, scale=None):
    if location is not None:
        obj.location.x, obj.location.y = location
        obj.keyframe_insert("location", frame=frame)
    if rotation is not None:
        obj.rotation_euler.z = math.radians(rotation)
        obj.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = (scale, scale, 1)
        obj.keyframe_insert("scale", frame=frame)


background = sprite("TRENCH_BACKGROUND", BG, 16.0, (0, 0), 0.0)

# Separate source art components become independently articulated native Blender
# objects. Each limb has its own pivot and keyframes; this is not a camera-only move.
torso = sprite("RIG_TORSO", RIG / "torso.png", 5.2, (0, 0.9), 4.0)
head = sprite("RIG_HEAD", RIG / "head_neck.png", 2.75, (0, 4.65), 4.6)
helmet = sprite("PROP_HELMET", RIG / "helmet.png", 1.48, (0, 6.0), 5.2)
ua_l = sprite("RIG_UPPER_ARM_L", RIG / "upper_arm_l.png", 3.0, (-1.47, 3.25), 3.8, "top")
ua_r = sprite("RIG_UPPER_ARM_R", RIG / "upper_arm_r.png", 3.0, (1.47, 3.25), 3.8, "top")
fa_l = sprite("RIG_FOREARM_L", RIG / "forearm_l.png", 3.0, (-2.35, 1.12), 4.2, "top")
fa_r = sprite("RIG_FOREARM_R", RIG / "forearm_r.png", 3.0, (2.35, 1.12), 4.2, "top")
hand_l = sprite("RIG_HAND_L", RIG / "hand_l.png", 1.45, (-2.72, -1.38), 4.5, "top")
hand_r = sprite("RIG_HAND_R", RIG / "hand_r.png", 1.45, (2.72, -1.38), 4.5, "top")
thigh_l = sprite("RIG_THIGH_L", RIG / "thigh_l.png", 3.3, (-0.72, -0.28), 3.7, "top")
thigh_r = sprite("RIG_THIGH_R", RIG / "thigh_r.png", 3.3, (0.72, -0.28), 3.7, "top")
shin_l = sprite("RIG_SHIN_L", RIG / "shin_l.png", 2.85, (-0.77, -2.96), 3.9, "top")
shin_r = sprite("RIG_SHIN_R", RIG / "shin_r.png", 2.85, (0.77, -2.96), 3.9, "top")
boot_l = sprite("RIG_BOOT_L", RIG / "boot_l.png", 1.52, (-0.82, -5.08), 4.1, "top")
boot_r = sprite("RIG_BOOT_R", RIG / "boot_r.png", 1.52, (0.82, -5.08), 4.1, "top")

body = [torso, head, helmet, ua_l, ua_r, fa_l, fa_r, hand_l, hand_r, thigh_l, thigh_r, shin_l, shin_r, boot_l, boot_r]

# Exhale / exhausted idle, then shell shock and a real defensive arm/helmet action.
for f, dy, s in [(1, 0.00, 1.00), (34, -0.10, 0.995), (58, 0.03, 1.00), (72, -0.42, 0.985), (92, -0.18, 0.995), (120, 0.02, 1.0), (150, 0.00, 1.0)]:
    for obj in body:
        base_y = obj.location.y if f == 1 else None
    key(torso, f, (0, 0.9 + dy), -1 if f in (34, 92) else 0, s)
    key(head, f, (0, 4.65 + dy), -3 if f == 34 else (7 if f == 72 else 0), s)

arm_keys = [
    (1, -7, 7, -4, 4),
    (48, -10, 10, -7, 7),
    (70, -20, 20, -11, 11),
    (88, -14, 14, -8, 8),
    (118, -12, 12, -8, 8),
    (150, -7, 7, -4, 4),
]
for f, a, b, c, d in arm_keys:
    key(ua_l, f, rotation=a)
    key(ua_r, f, rotation=b)
    key(fa_l, f, rotation=c)
    key(fa_r, f, rotation=d)
    key(hand_l, f, rotation=c * 0.5)
    key(hand_r, f, rotation=d * 0.5)

# Keep the elbow and wrist chains connected while the arms shield the head.
for obj, frames in {
    fa_l: [(1, -2.35, 1.12), (48, -2.35, 1.12), (70, -2.53, 1.42), (88, -2.46, 1.28), (118, -2.35, 1.2), (150, -2.35, 1.12)],
    fa_r: [(1, 2.35, 1.12), (48, 2.35, 1.12), (70, 2.53, 1.42), (88, 2.46, 1.28), (118, 2.35, 1.2), (150, 2.35, 1.12)],
    hand_l: [(1, -2.72, -1.38), (48, -2.72, -1.38), (70, -2.95, -0.92), (88, -2.86, -1.10), (118, -2.65, -1.2), (150, -2.72, -1.38)],
    hand_r: [(1, 2.72, -1.38), (48, 2.72, -1.38), (70, 2.95, -0.92), (88, 2.86, -1.10), (118, 2.65, -1.2), (150, 2.72, -1.38)],
}.items():
    for f, x, y in frames:
        key(obj, f, (x, y))

for f, y, r, s in [(1, 6.0, 0, 1), (52, 6.0, 0, 1), (70, 7.35, 18, 1.07), (84, 6.42, -9, 1.02), (100, 6.0, 0, 1), (150, 6.0, 0, 1)]:
    key(helmet, f, (0, y), r, s)

for obj, sign in ((thigh_l, -1), (thigh_r, 1), (shin_l, -1), (shin_r, 1), (boot_l, -1), (boot_r, 1)):
    x, y = obj.location.x, obj.location.y
    for f, shift, rot in [(1, 0, 0), (55, 0, 0), (72, -0.28, sign * 7), (92, -0.12, sign * 3), (120, 0, 0), (150, 0, 0)]:
        key(obj, f, (x, y + shift), rot)

for obj, sign in ((hand_l, 1), (hand_r, -1)):
    for f, rot in [(1, 0), (48, 0), (70, 9 * sign), (88, 5 * sign), (118, 2 * sign), (150, 0)]:
        key(obj, f, rotation=rot)

# Genuine Grease Pencil smoke wisps, sparks and shell-shock accent arcs.
def gp_stroke(name, pts, color, radius=0.08, z=1.5):
    gp = bpy.data.grease_pencils_v3.new(name + "_GP")
    layer = gp.layers.new(name + "_LAYER", set_active=True)
    drawing = layer.frames.new(1).drawing
    drawing.add_strokes([len(pts)])
    stroke = drawing.strokes[0]
    for point, co in zip(stroke.points, pts):
        point.position = (*co, 0)
        point.radius = radius
        point.opacity = 1
    mat = bpy.data.materials.new(name + "_MAT")
    bpy.data.materials.create_gpencil_data(mat)
    mat.grease_pencil.color = color
    mat.grease_pencil.show_stroke = True
    mat.grease_pencil.show_fill = False
    obj = bpy.data.objects.new(name, gp)
    bpy.context.collection.objects.link(obj)
    gp.materials.append(mat)
    obj.location.z = z
    return obj

smoke1 = gp_stroke("GP_SMOKE_1", [(-1.1, -0.5), (-1.4, 0.2), (-1.0, 0.9), (-1.3, 1.6)], (0.72, 0.74, 0.72, 0.7), 0.12)
smoke2 = gp_stroke("GP_SMOKE_2", [(0.5, -0.4), (0.8, 0.3), (0.5, 1.0), (0.9, 1.8)], (0.68, 0.70, 0.68, 0.6), 0.10)
for smoke, x in ((smoke1, -1.15), (smoke2, 0.7)):
    for f, y, s in [(1, -4.2, 0.8), (75, -1.8, 1.15), (150, 0.7, 1.5)]:
        key(smoke, f, (x, y), rotation=(-4 if smoke is smoke1 else 5), scale=s)

for obj in scene.objects:
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for p in fc.keyframe_points:
                p.interpolation = "BEZIER"
                p.handle_left_type = "AUTO_CLAMPED"
                p.handle_right_type = "AUTO_CLAMPED"

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "native" / "blender_gp_production_gate_v2.blend"))
if os.environ.get("GATE_KEYS_ONLY") == "1":
    key_dir = OUT / "gate_v2" / "keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    for frame in (1, 38, 70, 86, 118, 150):
        scene.frame_set(frame)
        scene.render.filepath = str(key_dir / f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
