from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
W, H = 576, 1024


def background(top=(34, 197, 235), bottom=(14, 66, 120)) -> Image.Image:
    image = Image.new("RGB", (W, H))
    px = image.load()
    for y in range(H):
        t = y / (H - 1)
        color = tuple(round(a * (1 - t) + b * t) for a, b in zip(top, bottom))
        for x in range(W):
            px[x, y] = color
    return image


def window(draw: ImageDraw.ImageDraw, box, rounded=True, crack=False):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=90 if rounded else 8, fill="#d9f5ff", outline="#10253f", width=28)
    draw.rounded_rectangle((x0 + 38, y0 + 38, x1 - 38, y1 - 38), radius=62 if rounded else 3, fill="#58c7f0", outline="#ffffff", width=10)
    if crack:
        draw.line([(x0 + 42, y0 + 42), (x0 + 105, y0 + 120), (x0 + 76, y0 + 210), (x0 + 145, y0 + 300)], fill="#ef3340", width=14)


def airplane(draw: ImageDraw.ImageDraw, cx=288, cy=500, scale=1.0):
    def p(x, y): return (cx + int(x * scale), cy + int(y * scale))
    body = [p(0, -300), p(45, -100), p(42, 190), p(0, 300), p(-42, 190), p(-45, -100)]
    draw.polygon(body, fill="#f7fbff", outline="#10253f", width=max(4, int(12 * scale)))
    draw.polygon([p(-40, -40), p(-250, 115), p(-245, 170), p(-32, 90)], fill="#ffcc38", outline="#10253f", width=max(4, int(10 * scale)))
    draw.polygon([p(40, -40), p(250, 115), p(245, 170), p(32, 90)], fill="#ffcc38", outline="#10253f", width=max(4, int(10 * scale)))
    draw.polygon([p(-30, 180), p(-105, 260), p(-28, 235)], fill="#ef3340", outline="#10253f", width=max(3, int(8 * scale)))
    draw.polygon([p(30, 180), p(105, 260), p(28, 235)], fill="#ef3340", outline="#10253f", width=max(3, int(8 * scale)))


def toilet(draw: ImageDraw.ImageDraw, x=110, y=310, gold=False):
    color = "#ffcc38" if gold else "#ded6c8"
    draw.rounded_rectangle((x, y, x + 355, y + 165), radius=28, fill=color, outline="#10253f", width=14)
    draw.ellipse((x + 85, y + 28, x + 270, y + 138), fill="#173a5e", outline="#10253f", width=12)
    draw.rounded_rectangle((x + 40, y + 150, x + 310, y + 470), radius=38, fill=color, outline="#10253f", width=14)
    draw.ellipse((x + 94, y + 180, x + 258, y + 338), fill="#58c7f0", outline="#10253f", width=12)


def cta(draw: ImageDraw.ImageDraw):
    draw.ellipse((78, 285, 270, 477), fill="#ef3340", outline="#10253f", width=14)
    draw.polygon([(152, 330), (152, 432), (230, 381)], fill="#ffffff", outline="#10253f")
    draw.ellipse((330, 285, 498, 453), fill="#ffcc38", outline="#10253f", width=14)
    draw.polygon([(414, 318), (458, 405), (370, 405)], fill="#ffffff", outline="#10253f")
    draw.ellipse((218, 590, 358, 730), fill="#ffffff", outline="#10253f", width=14)


def render_airplane_window(shot: int) -> Image.Image:
    image = background()
    draw = ImageDraw.Draw(image)
    if shot == 1:
        window(draw, (42, 170, 268, 820), rounded=False)
        window(draw, (308, 170, 534, 820), rounded=True)
        draw.polygon([(265, 470), (305, 440), (305, 500)], fill="#ffcc38", outline="#10253f")
    elif shot == 2:
        airplane(draw, cy=520, scale=.85)
        for r in (120, 175, 230):
            draw.arc((288-r, 520-r, 288+r, 520+r), 205, 335, fill="#ffffff", width=9)
    elif shot == 3:
        window(draw, (88, 150, 488, 850), rounded=False)
        for i in range(7):
            draw.ellipse((95+i*12, 160+i*12, 175+i*12, 240+i*12), fill="#ef3340", outline="#10253f", width=5)
    elif shot == 4:
        window(draw, (88, 150, 488, 850), rounded=False, crack=True)
        draw.polygon([(82, 160), (35, 120), (58, 195)], fill="#ffcc38")
    elif shot == 5:
        window(draw, (88, 150, 488, 850), rounded=True)
        for r in (35, 70, 105):
            draw.arc((110-r, 180-r, 110+r, 180+r), 180, 300, fill="#ffffff", width=8)
    elif shot == 6:
        airplane(draw, cy=520, scale=.9)
        for y in range(380, 690, 58):
            draw.rounded_rectangle((255, y, 321, y+38), radius=18, fill="#58c7f0", outline="#10253f", width=5)
    elif shot == 7:
        window(draw, (70, 110, 506, 900), rounded=True)
        draw.ellipse((175, 360, 400, 585), fill="#ffffff", outline="#10253f", width=14)
        draw.polygon([(220, 472), (270, 425), (360, 520), (335, 548), (270, 480), (242, 505)], fill="#42d392", outline="#10253f")
    else:
        cta(draw)
    return image


def render_roman_toilet(shot: int) -> Image.Image:
    image = background((245, 177, 68), (126, 57, 37))
    draw = ImageDraw.Draw(image)
    if shot == 1:
        for x in (55, 205, 355):
            draw.rectangle((x, 170, x + 115, 510), fill="#e9ddbd", outline="#10253f", width=12)
            draw.ellipse((x + 18, 205, x + 97, 285), fill="#173a5e", outline="#10253f", width=9)
        draw.rectangle((35, 500, 540, 565), fill="#e9ddbd", outline="#10253f", width=12)
        toilet(draw, 110, 610)
    elif shot == 2:
        for y in (175, 485):
            for x in (55, 220, 385):
                draw.rounded_rectangle((x, y, x + 135, y + 210), radius=18, fill="#d9c59d", outline="#10253f", width=11)
                draw.ellipse((x + 30, y + 35, x + 105, y + 115), fill="#173a5e", outline="#10253f", width=8)
    elif shot == 3:
        draw.ellipse((120, 300, 456, 636), fill="#ffffff", outline="#10253f", width=18)
        draw.rectangle((250, 350, 326, 570), fill="#58c7f0", outline="#10253f", width=12)
        draw.line((135, 615, 440, 320), fill="#ef3340", width=34)
    elif shot == 4:
        draw.line((180, 820, 385, 210), fill="#7a4b2d", width=32)
        draw.ellipse((285, 145, 500, 360), fill="#f5e7c6", outline="#10253f", width=14)
        for y in range(180, 325, 35):
            draw.line((315, y, 470, y + 30), fill="#58c7f0", width=8)
    elif shot == 5:
        draw.rounded_rectangle((65, 280, 510, 750), radius=45, fill="#d9c59d", outline="#10253f", width=14)
        draw.polygon([(100, 420), (450, 420), (500, 520), (450, 620), (100, 620), (55, 520)], fill="#58c7f0", outline="#10253f")
        for x in (170, 280, 390):
            draw.ellipse((x, 470, x + 45, 515), fill="#ffffff", outline="#10253f", width=5)
    elif shot == 6:
        toilet(draw, 20, 300)
        draw.line((288, 180, 288, 850), fill="#ffffff", width=12)
        draw.rounded_rectangle((315, 300, 550, 760), radius=45, fill="#ffffff", outline="#10253f", width=14)
        draw.ellipse((350, 355, 515, 525), fill="#58c7f0", outline="#10253f", width=12)
    elif shot == 7:
        toilet(draw, 110, 250, gold=True)
        for x, y in ((75, 180), (470, 240), (90, 760), (485, 720)):
            draw.ellipse((x, y, x + 38, y + 38), fill="#ffffff")
    else:
        cta(draw)
    return image


def photo(draw: ImageDraw.ImageDraw, box, broken=False, wrong=False):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=20, fill="#fffdf4", outline="#10253f", width=12)
    draw.rectangle((x0 + 28, y0 + 28, x1 - 28, y1 - 62), fill="#58c7f0", outline="#10253f", width=7)
    draw.ellipse((x0 + 55, y0 + 65, x0 + 120, y0 + 130), fill="#ffcc38")
    draw.polygon([(x0 + 28, y1 - 150), (x0 + 125, y0 + 165), (x0 + 205, y1 - 120), (x1 - 28, y0 + 145), (x1 - 28, y1 - 62), (x0 + 28, y1 - 62)], fill="#42d392")
    if wrong:
        draw.ellipse((x0 + 145, y0 + 95, x0 + 220, y0 + 170), fill="#ef3340", outline="#10253f", width=6)
    if broken:
        draw.line((x0 + 40, y0 + 55, x0 + 150, y0 + 210, x0 + 100, y0 + 330, x1 - 35, y1 - 80), fill="#ef3340", width=12)


def render_memory(shot: int) -> Image.Image:
    image = background((159, 95, 255), (29, 31, 76))
    draw = ImageDraw.Draw(image)
    if shot == 1:
        photo(draw, (90, 160, 486, 850), broken=True)
    elif shot == 2:
        for i, angle in enumerate((-18, 0, 18)):
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
            photo(ld, (150, 250, 426, 760), broken=i == 1)
            image.alpha_composite(layer.rotate(angle, center=(288, 505))) if image.mode == "RGBA" else image.paste(layer.rotate(angle, center=(288, 505)), (0, 0), layer.rotate(angle, center=(288, 505)))
    elif shot == 3:
        colors = ("#58c7f0", "#ffcc38", "#42d392", "#ef3340")
        for i, (x, y) in enumerate(((95, 230), (300, 210), (70, 500), (315, 515))):
            draw.rounded_rectangle((x, y, x + 190, y + 240), radius=28, fill=colors[i], outline="#10253f", width=12)
            draw.ellipse((x + 70, y + 90, x + 125, y + 145), fill="#ffffff")
    elif shot == 4:
        photo(draw, (45, 210, 275, 790), wrong=False)
        photo(draw, (301, 210, 531, 790), wrong=True)
    elif shot == 5:
        photo(draw, (90, 160, 486, 850))
        draw.rounded_rectangle((215, 420, 365, 610), radius=24, fill="#ef3340", outline="#10253f", width=12)
        draw.ellipse((255, 480, 325, 550), fill="#ffcc38")
    elif shot == 6:
        photo(draw, (90, 180, 486, 850), broken=True)
        draw.polygon([(75, 790), (500, 790), (500, 850), (75, 850)], fill="#173a5e", outline="#10253f")
        draw.rectangle((90, 804, 450, 836), fill="#ef3340")
    elif shot == 7:
        draw.rounded_rectangle((75, 150, 501, 880), radius=55, fill="#173a5e", outline="#ffffff", width=14)
        for i, (x, y) in enumerate(((120, 220), (310, 220), (120, 510), (310, 510))):
            photo(draw, (x, y, x + 145, y + 230), wrong=i == 3)
        draw.ellipse((245, 430, 335, 520), fill="#ffcc38", outline="#10253f", width=10)
    else:
        cta(draw)
    return image


def kernel(draw: ImageDraw.ImageDraw, cx=288, cy=500, scale=1.0, split=False):
    pts = [(cx-int(145*scale), cy+int(120*scale)), (cx-int(115*scale), cy-int(130*scale)),
           (cx, cy-int(210*scale)), (cx+int(125*scale), cy-int(110*scale)),
           (cx+int(145*scale), cy+int(120*scale)), (cx, cy+int(205*scale))]
    draw.polygon(pts, fill="#ffcc38", outline="#10253f")
    draw.line(pts + [pts[0]], fill="#10253f", width=max(8, int(16*scale)))
    if split:
        draw.line((cx, cy-int(190*scale), cx, cy+int(185*scale)), fill="#ef3340", width=max(8, int(14*scale)))


def popcorn(draw: ImageDraw.ImageDraw, cx=288, cy=500, scale=1.0):
    circles = [(-90, 10), (-55, -80), (10, -105), (75, -55), (95, 25), (35, 85), (-50, 90)]
    for dx, dy in circles:
        r = int(72*scale)
        draw.ellipse((cx+int(dx*scale)-r, cy+int(dy*scale)-r, cx+int(dx*scale)+r, cy+int(dy*scale)+r), fill="#fffdf4", outline="#10253f", width=max(6, int(10*scale)))
    draw.ellipse((cx-45*scale, cy-30*scale, cx+45*scale, cy+60*scale), fill="#ffcc38", outline="#10253f", width=max(5, int(8*scale)))


def render_popcorn(shot: int) -> Image.Image:
    image = background((255, 108, 94), (121, 36, 78))
    draw = ImageDraw.Draw(image)
    if shot == 1:
        kernel(draw)
        for r in (190, 240): draw.arc((288-r, 500-r, 288+r, 500+r), 210, 330, fill="#ffffff", width=10)
    elif shot == 2:
        kernel(draw, split=True)
        draw.ellipse((245, 350, 330, 440), fill="#58c7f0", outline="#10253f", width=8)
        for x, y in ((235, 525), (310, 570), (275, 650)): draw.ellipse((x, y, x+55, y+55), fill="#fffdf4", outline="#10253f", width=6)
    elif shot == 3:
        kernel(draw, cy=600, scale=.8)
        for y in (450, 350, 250):
            draw.ellipse((250, y, 326, y+76), fill="#58c7f0", outline="#10253f", width=7)
        for x in (150, 288, 426): draw.polygon([(x, 810), (x-35, 865), (x+35, 865)], fill="#ffcc38")
    elif shot == 4:
        kernel(draw, cy=560, scale=.9)
        for r in (35, 70, 105, 140):
            draw.arc((288-r, 560-r, 288+r, 560+r), 190, 350, fill="#ffffff", width=8)
    elif shot == 5:
        kernel(draw, cx=220, cy=560, scale=.75, split=True)
        popcorn(draw, cx=410, cy=500, scale=.55)
        draw.polygon([(285, 470), (350, 515), (285, 560)], fill="#42d392", outline="#10253f")
    elif shot == 6:
        popcorn(draw, scale=1.25)
        for r in (225, 270): draw.arc((288-r, 500-r, 288+r, 500+r), 25, 155, fill="#ffffff", width=9)
    elif shot == 7:
        draw.polygon([(60, 600), (516, 600), (450, 900), (126, 900)], fill="#ef3340", outline="#10253f")
        for x, y in ((140, 520), (250, 480), (365, 525), (205, 650), (330, 675)):
            popcorn(draw, x, y, .34)
    else:
        cta(draw)
    return image


def submarine(draw: ImageDraw.ImageDraw, cx=288, cy=620, scale=1.0, broken=False):
    draw.ellipse((cx-210*scale, cy-85*scale, cx+210*scale, cy+85*scale), fill="#2c4058", outline="#08192e", width=max(8, int(14*scale)))
    draw.rectangle((cx-25*scale, cy-150*scale, cx+45*scale, cy-70*scale), fill="#2c4058", outline="#08192e", width=max(6, int(10*scale)))
    draw.polygon([(cx-210*scale, cy), (cx-280*scale, cy-85*scale), (cx-280*scale, cy+85*scale)], fill="#2c4058", outline="#08192e")
    for x in (-115, -45, 25, 95):
        draw.ellipse((cx+x*scale-15, cy-15*scale, cx+x*scale+15, cy+15*scale), fill="#58c7f0")
    if broken: draw.line((cx-15*scale, cy-80*scale, cx+20*scale, cy+80*scale), fill="#ef3340", width=max(8, int(14*scale)))


def claw(draw: ImageDraw.ImageDraw, cx=288, top=120, bottom=590, closed=False):
    draw.rectangle((cx-28, top, cx+28, bottom-120), fill="#aeb9c7", outline="#08192e", width=10)
    draw.ellipse((cx-85, bottom-180, cx+85, bottom-10), fill="#aeb9c7", outline="#08192e", width=12)
    spread = 65 if closed else 135
    draw.line((cx-55, bottom-70, cx-spread, bottom+120), fill="#ffcc38", width=34)
    draw.line((cx+55, bottom-70, cx+spread, bottom+120), fill="#ffcc38", width=34)
    draw.ellipse((cx-spread-25, bottom+95, cx-spread+25, bottom+145), fill="#ef3340", outline="#08192e", width=6)
    draw.ellipse((cx+spread-25, bottom+95, cx+spread+25, bottom+145), fill="#ef3340", outline="#08192e", width=6)


def render_submarine(shot: int) -> Image.Image:
    image = background((13, 107, 140), (3, 19, 49))
    draw = ImageDraw.Draw(image)
    if shot == 1:
        draw.rectangle((0, 0, W, 250), fill="#58c7f0")
        claw(draw, bottom=620)
    elif shot == 2:
        submarine(draw, cy=660, scale=.85, broken=True)
        for x, y in ((90, 190), (460, 270), (120, 780)): draw.ellipse((x, y, x+18, y+18), fill="#58c7f0")
    elif shot == 3:
        draw.polygon([(70, 190), (505, 190), (450, 350), (120, 350)], fill="#dbe4ec", outline="#08192e")
        draw.rectangle((0, 350, W, 410), fill="#58c7f0")
        claw(draw, top=315, bottom=690)
    elif shot == 4:
        draw.polygon([(60, 100), (516, 100), (470, 250), (105, 250)], fill="#dbe4ec", outline="#08192e")
        claw(draw, top=230, bottom=690)
        submarine(draw, cy=825, scale=.58)
    elif shot == 5:
        submarine(draw, cy=700, scale=.72, broken=True)
        claw(draw, bottom=560, closed=True)
    elif shot == 6:
        submarine(draw, cy=470, scale=.62, broken=True)
        submarine(draw, cx=420, cy=790, scale=.35, broken=True)
        draw.polygon([(250, 720), (310, 760), (250, 800)], fill="#ef3340")
    elif shot == 7:
        draw.rounded_rectangle((55, 110, 521, 900), radius=30, fill="#14395d", outline="#ffffff", width=13)
        submarine(draw, cy=610, scale=.65, broken=True)
        claw(draw, top=180, bottom=470, closed=True)
        for x, y in ((95, 190), (470, 190), (95, 830), (470, 830)): draw.ellipse((x, y, x+28, y+28), fill="#ef3340")
    else:
        cta(draw)
    return image


def arrow(draw, a, b, color="#ffffff", width=18):
    draw.line((a, b), fill=color, width=width)
    x, y = b
    draw.polygon([(x, y), (x-30, y-45), (x+30, y-45)], fill=color)


def virus(draw, cx, cy, r=100, color="#ef3340"):
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=color, outline="#10253f", width=12)
    for dx, dy in ((0,-1),(0,1),(-1,0),(1,0),(-.7,-.7),(.7,-.7),(-.7,.7),(.7,.7)):
        x, y = cx+dx*r*1.35, cy+dy*r*1.35
        draw.line((cx+dx*r*.75, cy+dy*r*.75, x, y), fill="#10253f", width=12)
        draw.ellipse((x-18, y-18, x+18, y+18), fill="#ffcc38", outline="#10253f", width=5)


def cat(draw, cx=288, cy=530, scale=1.0, upside=False):
    layer = Image.new("RGBA", (W, H), (0,0,0,0)); d = ImageDraw.Draw(layer)
    d.ellipse((cx-150*scale, cy-90*scale, cx+115*scale, cy+95*scale), fill="#17233b", outline="#ffffff", width=10)
    d.ellipse((cx+75*scale, cy-145*scale, cx+205*scale, cy-15*scale), fill="#17233b", outline="#ffffff", width=10)
    d.polygon([(cx+90*scale,cy-125*scale),(cx+115*scale,cy-210*scale),(cx+145*scale,cy-135*scale)], fill="#17233b", outline="#ffffff")
    d.polygon([(cx+145*scale,cy-135*scale),(cx+185*scale,cy-205*scale),(cx+190*scale,cy-115*scale)], fill="#17233b", outline="#ffffff")
    for x in (cx-100*scale, cx-25*scale, cx+40*scale, cx+90*scale):
        d.rounded_rectangle((x,cy+55*scale,x+34*scale,cy+190*scale), radius=15, fill="#17233b", outline="#ffffff", width=7)
    d.arc((cx-260*scale,cy-210*scale,cx-90*scale,cy+90*scale), 75, 280, fill="#ffffff", width=24)
    if upside: layer = layer.rotate(180)
    draw._image.paste(layer, (0,0), layer)


def topic_icon(draw, topic: str, shot: int):
    if topic == "sleep":
        if shot in (1,2):
            draw.ellipse((125,230,451,556), fill="#fffdf4", outline="#10253f", width=16)
            draw.polygon([(288,280),(288,395),(370,470)], fill="#ef3340", outline="#10253f")
            for r in (180,230): draw.arc((288-r,393-r,288+r,393+r), 205,335,fill="#58c7f0",width=10)
        elif shot in (3,4):
            for i,(x,y) in enumerate(((80,230),(300,200),(110,520),(325,550))): draw.rounded_rectangle((x,y,x+170,y+220),radius=22,fill=("#58c7f0" if i%2 else "#ffcc38"),outline="#10253f",width=12)
        elif shot == 5:
            draw.polygon([(170,900),(260,200),(316,200),(406,900)], fill="#26364c", outline="#ffffff")
            for y in (420,620,820): draw.rectangle((270,y,306,y+80),fill="#ffcc38")
        else:
            draw.ellipse((110,230,466,700), fill="#ef7f82", outline="#10253f", width=16)
            for x,y in ((180,350),(300,310),(230,500),(340,520)): draw.ellipse((x,y,x+70,y+70),fill="#ffcc38",outline="#10253f",width=8)
    elif topic == "lightning":
        draw.ellipse((90,140,486,470), fill="#26364c", outline="#10253f", width=14)
        draw.ellipse((130,95,320,310), fill="#26364c", outline="#10253f", width=14)
        draw.polygon([(300,360),(230,610),(310,590),(230,880),(430,520),(335,545)], fill="#ffcc38", outline="#ffffff")
        for r in (90,160,230): draw.arc((288-r,650-r,288+r,650+r), 20,160,fill="#58c7f0",width=10)
    elif topic == "onion":
        draw.ellipse((130,270,446,780), fill="#a462d3", outline="#10253f", width=16)
        draw.polygon([(288,130),(235,310),(340,310)], fill="#42d392", outline="#10253f")
        for x in (200,250,300,350): draw.arc((x-70,330,x+70,720),90,270,fill="#fffdf4",width=8)
        if shot in (2,3,4): draw.line((80,250,500,830),fill="#dbe4ec",width=26)
        if shot in (5,6):
            draw.ellipse((80,120,220,260),fill="#ffffff",outline="#10253f",width=10); draw.ellipse((130,165,170,215),fill="#58c7f0")
    elif topic == "sky":
        draw.ellipse((210, 180, 366, 336), fill="#ffcc38", outline="#10253f", width=12)
        for angx in (90, 180, 288, 396, 486): draw.line((288,336,angx,820), fill=("#58c7f0" if shot < 6 else "#ef7f32"), width=20)
    elif topic == "fire":
        for x in (80,230,380):
            draw.rectangle((x,540,x+120,790), fill="#d79a58", outline="#10253f", width=10); draw.polygon([(x-15,540),(x+60,430),(x+135,540)], fill="#6b3925", outline="#10253f")
        draw.polygon([(245,650),(285,430),(330,650),(300,760)], fill="#ffcc38", outline="#ef3340")
    elif topic == "cat":
        cat(draw, upside=shot in (1,3));
        if shot in (2,3,4,5):
            draw.arc((70,180,506,850), 210, 520, fill="#ffcc38", width=18)
    elif topic == "material":
        draw.rectangle((55,360,265,760), fill="#aeb9c7", outline="#10253f", width=14)
        draw.rectangle((315,360,525,760), fill="#a66b3f", outline="#10253f", width=14)
        for x in range(85,240,45): arrow(draw,(x,650),(x,420),"#ef3340",10)
        for x in range(350,500,60): arrow(draw,(x,650),(x,520),"#ffcc38",10)
    elif topic == "breath":
        for i, (x,y,r) in enumerate(((180,560,95),(290,480,120),(410,560,90))): draw.ellipse((x-r,y-r,x+r,y+r), fill="#fffdf4", outline="#10253f", width=10)
        for x in (120,240,360,480): draw.ellipse((x,760,x+24,784), fill="#58c7f0")
    elif topic == "stomach":
        draw.ellipse((140,220,450,780), fill="#ef7f82", outline="#10253f", width=16)
        draw.ellipse((205,300,405,700), fill="#ffcc38" if shot in (1,2,6) else "#42d392", outline="#10253f", width=12)
        if shot in (3,4,7): draw.arc((165,250,425,750), 80, 280, fill="#ffffff", width=28)
    elif topic == "soda":
        draw.rounded_rectangle((155,190,421,850), radius=45, fill="#ef3340", outline="#10253f", width=16)
        draw.ellipse((175,180,401,260), fill="#dbe4ec", outline="#10253f", width=12)
        for x,y in ((210,540),(300,620),(340,450),(245,700)): draw.ellipse((x,y,x+45,y+45), fill="#ffffff", outline="#10253f", width=5)
        if shot in (1,6,7):
            for r in (90,145,200): draw.arc((288-r,190-r,288+r,190+r), 190,350,fill="#ffffff",width=10)
    else:
        virus(draw, 288, 520, 120)
        if topic == "antibiotic":
            draw.rounded_rectangle((90,720,486,850), radius=65, fill="#ffffff", outline="#10253f", width=12)
            draw.rectangle((288,725,480,845), fill="#58c7f0")
        elif topic == "fever":
            draw.rounded_rectangle((80,190,180,820), radius=50, fill="#ffffff", outline="#10253f", width=14)
            draw.ellipse((45,720,215,890), fill="#ef3340", outline="#10253f", width=14); draw.rectangle((115,300,145,760), fill="#ef3340")


def render_generic(project_name: str, shot: int) -> Image.Image:
    image = background((48, 210, 180), (32, 52, 104))
    draw = ImageDraw.Draw(image)
    if shot == 8:
        cta(draw); return image
    if "dont-sleep" in project_name: topic = "sleep"
    elif "lightning" in project_name: topic = "lightning"
    elif "onions" in project_name: topic = "onion"
    elif "sky-blue" in project_name: topic = "sky"
    elif "medieval" in project_name: topic = "fire"
    elif "cats-twist" in project_name or "cat-into-a-spy" in project_name: topic = "cat"
    elif "metal-feels" in project_name: topic = "material"
    elif "breath" in project_name: topic = "breath"
    elif "stomach" in project_name: topic = "stomach"
    elif "soda" in project_name: topic = "soda"
    elif "antibiotics" in project_name or "mucus" in project_name: topic = "antibiotic"
    elif "fever" in project_name: topic = "fever"
    else: topic = "virus"
    topic_icon(draw, topic, shot)
    if shot % 3 == 0: draw.ellipse((55,110,155,210), fill="#ffcc38", outline="#10253f", width=9)
    if shot % 2 == 0: arrow(draw, (110,900), (465,900), "#ffffff", 14)
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("shots", nargs="+", type=int)
    args = parser.parse_args()
    project = Path(args.project)
    if not project.is_absolute():
        project = ROOT / "projects" / project
    if "airplane-windows" in project.name:
        renderer = render_airplane_window
    elif "roman-toilets" in project.name:
        renderer = render_roman_toilet
    elif "memory-is-lying" in project.name:
        renderer = render_memory
    elif "popcorn" in project.name:
        renderer = render_popcorn
    elif "giant-claw" in project.name:
        renderer = render_submarine
    else:
        renderer = lambda shot: render_generic(project.name, shot)
    log = []
    for shot in args.shots:
        target = project / "images" / f"shot_{shot:03d}.png"
        renderer(shot).save(target)
        log.append({"shot_id": f"shot_{shot:03d}", "reason": "semantic_model_failure", "method": "deterministic_vector"})
    (project / "logs/regenerated_shots.json").write_text(json.dumps(log, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
