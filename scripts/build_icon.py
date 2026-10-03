from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
assets = root / "assets"
assets.mkdir(exist_ok=True)
size = 1024
im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((44, 44, 980, 980), radius=210, fill="#121820", outline="#D79847", width=24)
d.rounded_rectangle((150, 160, 874, 864), radius=92, fill="#E8D7B7")
d.line((250, 300, 770, 300), fill="#1A2028", width=34)
d.line((250, 430, 660, 430), fill="#1A2028", width=34)
d.line((250, 560, 720, 560), fill="#1A2028", width=34)
d.line((250, 690, 590, 690), fill="#1A2028", width=34)
d.ellipse((720, 625, 846, 751), fill="#D79847", outline="#1A2028", width=22)
d.line((783, 655, 783, 721), fill="#1A2028", width=18)
d.line((750, 688, 816, 688), fill="#1A2028", width=18)
png = assets / "app_icon.png"
im.save(png)

iconset = assets / "app_icon.iconset"
iconset.mkdir(exist_ok=True)
for points in (16, 32, 128, 256, 512):
    for scale in (1, 2):
        px = points * scale
        name = f"icon_{points}x{points}" + ("@2x" if scale == 2 else "") + ".png"
        im.resize((px, px), Image.Resampling.LANCZOS).save(iconset / name)
