#!/usr/bin/env python3
"""Build numbered QA contact-sheet pages for the full B-59 episode."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT = Path("projects/the-soviet-submarine-that-almost-started-world-war-iii-clean-editorial")
IMAGES = PROJECT / "images"
OUTPUT = PROJECT / "qa_contact_sheets"
COLS, ROWS = 5, 4
CELL_W, CELL_H = 384, 246
LABEL_H = 30


def main() -> None:
    paths = [IMAGES / f"shot_{index:03d}.png" for index in range(1, 260)]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=20)
    for page_index, offset in enumerate(range(0, len(paths), COLS * ROWS), start=1):
        canvas = Image.new("RGB", (COLS * CELL_W, ROWS * (CELL_H + LABEL_H)), "#111827")
        draw = ImageDraw.Draw(canvas)
        for cell_index, path in enumerate(paths[offset : offset + COLS * ROWS]):
            row, col = divmod(cell_index, COLS)
            with Image.open(path) as image:
                frame = image.convert("RGB")
                frame.thumbnail((CELL_W, CELL_H), Image.Resampling.LANCZOS)
                x = col * CELL_W + (CELL_W - frame.width) // 2
                y = row * (CELL_H + LABEL_H) + (CELL_H - frame.height) // 2
                canvas.paste(frame, (x, y))
            label = f"shot_{offset + cell_index + 1:03d}"
            draw.text((col * CELL_W + 8, row * (CELL_H + LABEL_H) + CELL_H + 3), label, fill="white", font=font)
        canvas.save(OUTPUT / f"page_{page_index:02d}.png", optimize=True)


if __name__ == "__main__":
    main()
