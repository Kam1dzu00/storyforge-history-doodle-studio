from pathlib import Path

from PIL import Image
import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "shared/art/character_master/ww1_soldier_rig_components_sheet_v1.png"
OUT = ROOT / "shared/art/character_rig_v1"
OUT.mkdir(parents=True, exist_ok=True)

# Bounds are deliberately generous. Transparent pixels remain transparent, so
# each crop retains antialiased edges and hidden joint overlap extensions.
PARTS = {
    "head_neck": (270, 0, 510, 320),
    "helmet": (515, 50, 840, 265),
    "upper_arm_l": (85, 250, 345, 525),
    "upper_arm_r": (680, 250, 940, 525),
    "torso": (320, 245, 705, 765),
    "forearm_l": (35, 500, 305, 815),
    "forearm_r": (735, 500, 995, 815),
    "hand_l": (25, 770, 185, 1030),
    "hand_r": (840, 770, 1015, 1030),
    "thigh_l": (250, 720, 520, 1115),
    "thigh_r": (505, 720, 775, 1115),
    "shin_l": (270, 1070, 485, 1370),
    "shin_r": (540, 1070, 755, 1370),
    "boot_l": (245, 1265, 505, 1535),
    "boot_r": (520, 1265, 785, 1535),
}

image = Image.open(SOURCE).convert("RGBA")
for name, bounds in PARTS.items():
    crop = image.crop(bounds)
    array = np.asarray(crop).copy()
    alpha = array[:, :, 3]
    labels, count = ndimage.label(alpha > 8)
    if count:
        sizes = ndimage.sum(alpha > 8, labels, range(1, count + 1))
        keep = int(np.argmax(sizes)) + 1
        # Dilate the selected component slightly to retain antialiased fringe.
        selected = ndimage.binary_dilation(labels == keep, iterations=2)
        array[~selected, 3] = 0
        crop = Image.fromarray(array, "RGBA")
    crop.save(OUT / f"{name}.png")

# A neutral-background inspection sheet; not an animation asset.
thumbs = []
for name in PARTS:
    part = Image.open(OUT / f"{name}.png").convert("RGBA")
    part.thumbnail((220, 250), Image.Resampling.LANCZOS)
    cell = Image.new("RGBA", (240, 280), (223, 219, 207, 255))
    cell.alpha_composite(part, ((240 - part.width) // 2, (250 - part.height) // 2))
    thumbs.append(cell.convert("RGB"))

sheet = Image.new("RGB", (240 * 5, 280 * 3), (223, 219, 207))
for idx, thumb in enumerate(thumbs):
    sheet.paste(thumb, ((idx % 5) * 240, (idx // 5) * 280))
sheet.save(OUT / "rig_parts_contact.jpg", quality=92)
