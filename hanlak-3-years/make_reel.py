#!/usr/bin/env python3
"""Hanlak XI - 3 years, 60 s beat-synced reel (9:16, 30 fps, 128 BPM).

IPL-broadcast style: a live stats ticker, cricket-ball wipes between sections,
leaderboard countdowns (#5 -> #2) that end on a flipping player card for #1
(Orange Cap, Purple Cap, Safest Hands), a squad wall and quick-fire moments,
all cut to a synthesized beat.

    pip install pillow numpy imageio-ffmpeg
    python3 make_reel.py              # -> hanlak_xi_3_years_reel.mp4
    python3 make_reel.py --preview    # -> reel_preview.png contact sheet
"""
import math
import os
import random
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
FPS = 30
BPM = 128
BEAT = 60 / BPM
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

BLACK = (12, 11, 10)
CREAM = (244, 236, 218)
GOLD = (222, 166, 52)
RED = (214, 48, 38)
GREEN = (48, 150, 84)
DIM = (34, 32, 30)
MUTED = (150, 142, 128)
ORANGE = (240, 118, 28)
PURPLE = (124, 58, 196)
TEAL = (22, 150, 140)

# ------------------------------------------------------------------ data
# Avatar crops from the CricHeroes screenshots: (file, x, y, radius).
FACES = {
    "sarath": ("partnerships.jpg", 237, 828, 56),
    "akhil": ("partnerships.jpg", 718, 833, 56),
    "mohan": ("partnerships.jpg", 235, 1068, 56),
    "vijay": ("partnerships.jpg", 712, 1072, 56),
    "ygp": ("partnerships.jpg", 234, 1300, 56),
    "kiran": ("field.jpg", 133, 814, 40),
    "surya": ("bowl.jpg", 108, 784, 40),
    "yeswanth": ("bowl.jpg", 111, 1101, 40),
    "veeru": ("bowl.jpg", 113, 1257, 40),
    "srinivas": ("bowl.jpg", 115, 1414, 40),
    "bala": ("bat.jpg", 130, 815, 40),
    "hari": ("bat.jpg", 136, 1154, 40),
    "harsh": ("bat.jpg", 140, 1314, 40),
    "chandu": ("bat.jpg", 143, 1474, 40),
}

# CricHeroes team leaderboard, Sep 2026. Rows: (face, name, value, small print)
BOARDS = [
    dict(key="runs", title="TOP RUN SCORERS", unit="RUNS", cap="ORANGE CAP", color=ORANGE, rows=[
        ("akhil", "AKHIL SAI", 1732, "56 INN · AVG 43.30"),
        ("bala", "BALA YOGESH", 1015, "47 INN · SR 106.84"),
        ("sarath", "SARATH CHANDRA", 962, "71 INN · SR 105.37"),
        ("hari", "HARIVARDHAN REDDY", 879, "26 INN · AVG 39.95"),
        ("harsh", "HARSH RAJ", 847, "43 INN · SR 113.69"),
    ], card=[("56", "INNINGS"), ("43.30", "AVERAGE"), ("137.24", "STRIKE RATE")]),
    dict(key="wickets", title="TOP WICKET TAKERS", unit="WICKETS", cap="PURPLE CAP", color=PURPLE, rows=[
        ("surya", "SURYA", 118, "86 INN · ECO 7.26"),
        ("kiran", "KIRAN TEJA", 112, "79 INN · ECO 7.17"),
        ("yeswanth", "YESWANTH", 59, "58 INN · ECO 7.18"),
        ("veeru", "VEERU BHAI", 37, "39 INN · ECO 7.88"),
        ("srinivas", "K SRINIVAS", 31, "22 INN · ECO 6.16"),
    ], card=[("86", "INNINGS"), ("7.26", "ECONOMY"), ("18.01", "AVERAGE")]),
    dict(key="catches", title="MOST CATCHES", unit="CATCHES", cap="SAFEST HANDS", color=TEAL, rows=[
        ("kiran", "KIRAN TEJA", 23, "35 DISMISSALS"),
        ("surya", "SURYA", 21, "28 DISMISSALS"),
        ("yeswanth", "YESWANTH", 18, "26 DISMISSALS"),
        ("sarath", "SARATH CHANDRA", 16, "42 DISMISSALS"),
        ("akhil", "AKHIL SAI", 15, "33 DISMISSALS"),
    ], card=[("80", "MATCHES"), ("35", "DISMISSALS"), ("10", "RUN-OUTS")]),
]

ALLROUND = [
    ("akhil", "AKHIL SAI", "1732", "RUNS", "33", "DISMISSALS", ORANGE),
    ("surya", "SURYA", "118", "WICKETS", "21", "CATCHES", PURPLE),
    ("kiran", "KIRAN TEJA", "112", "WICKETS", "23", "CATCHES", TEAL),
]

PARTNERSHIPS = [
    ("sarath", "SARATH CHANDRA", "55(45)", "akhil", "AKHIL SAI", "70(45)", "138*", "88 BALLS · 2ND WKT"),
    ("mohan", "MOHAN KAKINATI", "99(49)", "vijay", "VIJAY CHINNU", "26(23)", "137*", "69 BALLS · 2ND WKT"),
    ("ygp", "YGPREDDY", "57(27)", "akhil", "AKHIL SAI", "53(21)", "122", "47 BALLS · 1ST WKT"),
]

SQUAD = [("akhil", "AKHIL"), ("surya", "SURYA"), ("kiran", "KIRAN"), ("sarath", "SARATH"), ("bala", "BALA"),
         ("hari", "HARI"), ("harsh", "HARSH"), ("yeswanth", "YESWANTH"), ("veeru", "VEERU"),
         ("srinivas", "SRINIVAS"), ("chandu", "CHANDU"), ("mohan", "MOHAN"), ("vijay", "VIJAY"), ("ygp", "YGP")]

MOMENTS = [
    ("HIGHEST TOTAL", "231", "vs THUNDER HAWKS · 2024"),
    ("BIGGEST WIN", "145 RUNS", "vs GRACE BALL TITANS · 2026"),
    ("TOP SCORE", "104", "CHANDU BANDARU · 59 BALLS"),
    ("TWIN 99s", "99 & 99", "MOHAN KAKINATI · SUNNY NAVEEN"),
    ("STRIKE RATE", "252.9", "DHEERAJ SAI KRISHNA · 86 (34)"),
    ("BEST BOWLING", "6 WKTS", "K SRINIVAS · 3.2 OVERS"),
    ("MOST DISMISSALS", "42", "SARATH CHANDRA · 82 MATCHES"),
    ("THE TIE", "175 = 175", "vs UMP · 01 JUN 2024"),
]

TICKER = ("HANLAK XI  •  EST. 18 SEP 2023  •  97 MATCHES  •  56 WINS  •  AKHIL SAI 1732 RUNS  •  "
          "SURYA 118 WICKETS  •  KIRAN TEJA 23 CATCHES  •  HYDERABAD  •  ")


def asset(*p):
    return os.path.join(HERE, "assets", *p)


ANTON = "Anton-Regular.ttf"
_fonts, _txt, _faces = {}, {}, {}


def font(name, size):
    if (name, size) not in _fonts:
        _fonts[(name, size)] = ImageFont.truetype(asset("fonts", name), size)
    return _fonts[(name, size)]


def fit(size, text, max_w, name=ANTON):
    while size > 12 and font(name, size).getlength(text) > max_w:
        size -= 4
    return size


def txt(text, size, color, stroke=0, stroke_color=BLACK, name=ANTON):
    key = (text, size, color, stroke, stroke_color, name)
    if key not in _txt:
        f = font(name, size)
        bb = f.getbbox(text, stroke_width=stroke)
        img = Image.new("RGBA", (bb[2] - bb[0] + 4, bb[3] - bb[1] + 4), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((2 - bb[0], 2 - bb[1]), text, font=f, fill=color,
                                 stroke_width=stroke, stroke_fill=stroke_color)
        _txt[key] = img
    return _txt[key]


def block(w, h, color, skew=0):
    img = Image.new("RGBA", (w + abs(skew), h), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon([(max(skew, 0), 0), (w + max(skew, 0), 0),
                                 (w + max(-skew, 0), h), (max(-skew, 0), h)], fill=color)
    return img


def logo(color, width):
    lg = Image.open(asset("logo.png")).convert("L").crop((451, 507, 1455, 1413))
    img = Image.new("RGBA", lg.size, color + (255,))
    img.putalpha(Image.eval(lg, lambda v: 255 - v))
    return img.resize((width, round(width * lg.height / lg.width)), Image.LANCZOS)


def face(key, d, ring=GOLD):
    if (key, d, ring) not in _faces:
        f, x, y, r = FACES[key]
        ph = Image.open(asset(f)).convert("RGB").crop((x - r, y - r, x + r, y + r))
        ph = ph.resize((d, d), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 80, 2)).convert("RGBA")
        m = Image.new("L", (d * 4, d * 4), 0)
        ImageDraw.Draw(m).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
        ph.putalpha(m.resize((d, d), Image.LANCZOS))
        rw = max(6, d // 22)
        out = Image.new("RGBA", (d + 2 * rw, d + 2 * rw), (0, 0, 0, 0))
        ImageDraw.Draw(out).ellipse((0, 0, d + 2 * rw - 1, d + 2 * rw - 1), fill=ring)
        out.alpha_composite(ph, (rw, rw))
        _faces[(key, d, ring)] = out
    return _faces[(key, d, ring)]


# ------------------------------------------------------------------ motion
def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def out_back(t):
    t = clamp(t)
    return 1 + 2.7 * (t - 1) ** 3 + 1.7 * (t - 1) ** 2


def out_cubic(t):
    return 1 - (1 - clamp(t)) ** 3


def in_cubic(t):
    return clamp(t) ** 3


class Frame:
    def __init__(self, bg, shake=(0, 0)):
        self.im = Image.new("RGB", (W, H), bg)
        self.dx, self.dy = shake

    def blit(self, img, cx, cy, s=1.0, rot=0.0, alpha=1.0, sx=1.0):
        if img is None or s <= 0.01 or alpha <= 0.01 or sx <= 0.01:
            return
        if abs(s - 1) > 1e-3 or abs(sx - 1) > 1e-3:
            img = img.resize((max(1, round(img.width * s * sx)), max(1, round(img.height * s))), Image.BILINEAR)
        if abs(rot) > 0.05:
            img = img.rotate(rot, Image.BILINEAR, expand=True)
        if alpha < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
        self.im.paste(img, (round(cx - img.width / 2 + self.dx), round(cy - img.height / 2 + self.dy)), img)

    def left(self, img, x, cy, **kw):
        self.blit(img, x + img.width / 2, cy, **kw)


def slam(fr, img, cx, cy, t, t0, dur=0.16, frm=1.8, rot=0.0):
    if t < t0:
        return
    k = out_back((t - t0) / dur)
    fr.blit(img, cx, cy, frm + (1 - frm) * k, rot * (1 - k), clamp((t - t0) / (dur * 0.5)))


def slide(fr, img, cx, cy, t, t0, dx=0, dy=0, dur=0.2):
    if t < t0:
        return
    k = out_cubic((t - t0) / dur)
    fr.blit(img, cx + dx * (1 - k), cy + dy * (1 - k), 1, 0, clamp((t - t0) / (dur * 0.4)))


def leave(t, t_out, dur=0.18):
    """Horizontal offset for things exiting to the left at t_out."""
    return -1300 * in_cubic((t - t_out) / dur) if t > t_out else 0


# ------------------------------------------------------------------ backgrounds
_marquee = {}


def marquee(fr, t, text="HANLAK XI  •  3 YEARS  •  ", color=DIM):
    key = (text, color)
    if key not in _marquee:
        _marquee[key] = txt(text * 4, 300, (0, 0, 0, 0), stroke=3, stroke_color=color)
    row = _marquee[key]
    period = row.width / 4
    for i, y in enumerate((230, 620, 1010, 1400, 1790)):
        x = (t * (160 if i % 2 else -160)) % period - period
        fr.im.paste(row, (round(x + fr.dx), y - 150), row)


_rays = {}


def rays(fr, t, color):
    if color not in _rays:
        s = 2300
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for k in range(18):
            a0, a1 = k * 20, k * 20 + 10
            pts = [(s / 2, s / 2)] + [(s / 2 + s * math.cos(math.radians(a)), s / 2 + s * math.sin(math.radians(a)))
                                      for a in (a0, a1)]
            d.polygon(pts, fill=color + (60,))
        glow = Image.new("L", (s, s), 0)
        ImageDraw.Draw(glow).ellipse((s / 2 - 700, s / 2 - 700, s / 2 + 700, s / 2 + 700), fill=255)
        glow = glow.filter(ImageFilter.GaussianBlur(260))
        img.putalpha(Image.fromarray((np.asarray(img.getchannel("A")).astype(np.float32)
                                      * np.asarray(glow) / 255).astype(np.uint8)))
        _rays[color] = img
    img = _rays[color].rotate(t * 12, Image.BILINEAR)
    fr.im.paste(img, (round(W / 2 - img.width / 2), round(H / 2 - 80 - img.height / 2)), img)


_ticker = {}


def ticker(fr, t):
    if "row" not in _ticker:
        _ticker["row"] = txt(TICKER * 3, 40, CREAM)
        tag = block(150, 74, RED)
        tag.alpha_composite(txt("● LIVE", 40, CREAM), (22, 16))
        _ticker["tag"] = tag
    row = _ticker["row"]
    period = row.width / 3
    y = H - 74
    fr.im.paste((20, 18, 16), (0, y, W, H))
    fr.im.paste(GOLD, (0, y, W, y + 4))
    x = -((t * 190) % period)
    fr.im.paste(row, (round(x) + 160, y + 16), row)
    fr.im.paste(_ticker["tag"], (0, y), _ticker["tag"])


# ------------------------------------------------------------------ player card
_card = {}


def card_images(b):
    """Front and back of the #1 player's card for board b."""
    if b["key"] in _card:
        return _card[b["key"]]
    cw, ch = 740, 1080
    c = b["color"]
    grad = np.zeros((ch, cw, 4), np.uint8)
    k = np.linspace(0, 1, ch)[:, None]
    dark = np.array(c) * 0.28
    for i in range(3):
        grad[..., i] = (c[i] * (1 - k) * 0.95 + dark[i] * k).astype(np.uint8)
    yy, xx = np.mgrid[0:ch, 0:cw]
    stripes = ((xx + yy) // 26) % 2 == 0
    grad[..., :3] = np.where(stripes[..., None], np.clip(grad[..., :3] * 1.06, 0, 255), grad[..., :3])
    grad[..., 3] = 255
    front = Image.fromarray(grad, "RGBA")
    m = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, cw - 1, ch - 1), 46, fill=255)
    front.putalpha(m)
    d = ImageDraw.Draw(front)
    d.rounded_rectangle((16, 16, cw - 17, ch - 17), 34, outline=GOLD, width=6)
    fk, name, val, _ = b["rows"][0]
    chip = block(380, 78, BLACK, 20)
    front.alpha_composite(chip, ((cw - chip.width) // 2, 50))
    capt = txt(b["cap"], 50, GOLD)
    front.alpha_composite(capt, ((cw - capt.width) // 2, 50 + (78 - capt.height) // 2))
    ph = face(fk, 300, GOLD)
    front.alpha_composite(ph, ((cw - ph.width) // 2, 160))
    n = txt(name, fit(92, name, cw - 80), CREAM)
    front.alpha_composite(n, ((cw - n.width) // 2, 500))
    vv = txt(str(val), 220, CREAM, stroke=6, stroke_color=BLACK)
    front.alpha_composite(vv, ((cw - vv.width) // 2, 610))
    u = txt(b["unit"], 58, GOLD)
    front.alpha_composite(u, ((cw - u.width) // 2, 860))
    for i, (sv, sl) in enumerate(b["card"]):
        cx = 130 + i * 240
        a = txt(sv, 58, CREAM)
        l2 = txt(sl, 28, GOLD)
        front.alpha_composite(a, (int(cx - a.width / 2), 940))
        front.alpha_composite(l2, (int(cx - l2.width / 2), 1010))
    back = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(back).rounded_rectangle((0, 0, cw - 1, ch - 1), 46, fill=BLACK, outline=GOLD, width=10)
    lg = logo(GOLD, 420)
    back.alpha_composite(lg, ((cw - lg.width) // 2, (ch - lg.height) // 2))
    _card[b["key"]] = (front, back)
    return front, back


def shine(img, p):
    """Diagonal light sweep across img at progress p (0..1)."""
    w, h = img.size
    pos = -400 + p * (w + h + 800)
    yy, xx = np.mgrid[0:h:4, 0:w:4]
    band = np.clip(1 - np.abs((xx + yy * 0.6) - pos) / 90, 0, 1)
    band = Image.fromarray((band * 150).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    a = np.minimum(np.asarray(band), np.asarray(img.getchannel("A")))
    hl = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    hl.putalpha(Image.fromarray(a))
    out = img.copy()
    out.alpha_composite(hl)
    return out


# ------------------------------------------------------------------ scenes (t is local seconds)
def scene_intro(fr, t):
    marquee(fr, t)
    if t < BEAT * 4:
        words = ["18 SEP 2023", "ONE TEAM", "ONE DREAM", "3 YEARS LATER..."]
        i = min(3, int(t / BEAT))
        slam(fr, txt(words[i], fit(150, words[i], 960), CREAM if i < 3 else GOLD), 540, 900, t, i * BEAT,
             0.12, 1.4)
        return
    t -= BEAT * 4
    if t < BEAT * 4:
        slam(fr, _big_logo(), 540, 880, t, 0, 0.2, 2.4)
        if t > BEAT * 2:
            slam(fr, txt("HANLAK XI", 160, GOLD), 540, 1400, t, BEAT * 2)
        return
    fr.blit(_small_logo(), 540, 330)
    slam(fr, txt("3", 900, GOLD), 280, 930, t, BEAT * 4, 0.18, 2.2, rot=-12)
    slam(fr, txt("YEARS", 220, CREAM), 770, 790, t, BEAT * 5)
    slam(fr, txt("STRONG", 200, RED), 770, 1070, t, BEAT * 6)
    if t > BEAT * 8:
        slide(fr, block(760, 110, CREAM, 30), 540, 1440, t, BEAT * 8, dx=-900)
        slide(fr, txt("18.09.2023  →  18.09.2026", 70, BLACK), 540, 1440, t, BEAT * 8.25, dx=900)
    if t > BEAT * 10:
        slam(fr, txt("HYDERABAD · TELANGANA", 64, GOLD), 540, 1590, t, BEAT * 10)


_logos = {}


def _small_logo():
    if "s" not in _logos:
        _logos["s"] = logo(GOLD, 300)
    return _logos["s"]


def _big_logo():
    if "b" not in _logos:
        _logos["b"] = logo(CREAM, 820)
    return _logos["b"]


def scene_record(fr, t):
    marquee(fr, t)
    n = int(97 * out_cubic(t / BEAT))
    fr.blit(txt(str(n), 520, GOLD), 540, 500, 1 + 0.08 * max(0, 1 - t / 0.2))
    slam(fr, txt("MATCHES", 150, CREAM), 540, 860, t, BEAT * 0.5)
    for i, (num, lab, col) in enumerate([("56", "WON", GREEN), ("40", "LOST", CREAM), ("1", "TIED", GOLD)]):
        t0 = BEAT * (2 + i)
        y = 1090 + i * 190
        dx = -1200 if i % 2 == 0 else 1200
        slide(fr, block(820, 160, col, 40), 540, y, t, t0, dx=dx)
        slide(fr, txt(num, 130, BLACK), 330, y, t, t0 + 0.06, dx=dx)
        slide(fr, txt(lab, 110, BLACK), 680, y, t, t0 + 0.06, dx=dx)
    if t > BEAT * 5:
        slam(fr, _stamp(), 800, 1690, t, BEAT * 5, 0.12, 2.5, rot=30)


def _stamp():
    if "stamp" not in _logos:
        st = Image.new("RGBA", (440, 190), (0, 0, 0, 0))
        d = ImageDraw.Draw(st)
        d.rounded_rectangle((6, 6, 433, 183), 18, outline=RED, width=10)
        d.text((220, 72), "58% WINS", font=font(ANTON, 90), fill=RED, anchor="mm")
        d.text((220, 148), "56 OF 97", font=font(ANTON, 44), fill=RED, anchor="mm")
        _logos["stamp"] = st.rotate(-10, Image.BICUBIC, expand=True)
    return _logos["stamp"]


def make_board(b):
    rows = b["rows"]
    top = rows[0][2]

    def scene(fr, t):
        c = b["color"]
        if t < BEAT * 5:
            # countdown #5 -> #2
            marquee(fr, t, text=f"{b['unit']}  •  ")
            off = leave(t, BEAT * 4.75)
            fr.blit(block(260, 62, c, 18), 540 + off, 200)
            fr.blit(txt(b["cap"] + " RACE", 40, CREAM), 540 + off, 200)
            slam(fr, txt(b["title"], fit(150, b["title"], 980), CREAM), 540 + off, 330, t, 0)
            for rank in range(5, 1, -1):
                fk, name, val, sub = rows[rank - 1]
                t0 = BEAT * (5 - rank + 1)
                if t < t0:
                    continue
                y = 540 + (rank - 2) * 300
                k = out_cubic((t - t0) / 0.4)
                x0 = off
                slam(fr, txt(f"#{rank}", 90, c), 75 + x0, y, t, t0, 0.12, 1.6)
                slide(fr, face(fk, 150), 230 + x0, y, t, t0, dx=-400, dur=0.15)
                nm = txt(name, fit(62, name, 700), CREAM)
                slide(fr, nm, 330 + x0 + nm.width / 2, y - 55, t, t0, dx=500, dur=0.15)
                bar_w = int(40 + 470 * (val / top) * k)
                bar = block(bar_w, 50, c, 14)
                fr.left(bar, 330 + x0, y + 15)
                v = txt(str(int(round(val * k))), 64, CREAM)
                fr.left(v, 330 + x0 + bar.width + 18, y + 15)
                s = txt(sub, 34, MUTED)
                fr.left(s, 330 + x0, y + 75, alpha=clamp((t - t0) / 0.3))
            return
        # #1 player card
        tc = t - BEAT * 5
        rays(fr, t, c)
        front, back = card_images(b)
        if tc < BEAT:
            slam(fr, txt("AND THE", 90, CREAM), 540, 760, tc, 0, 0.12, 1.5)
            if tc > BEAT * 0.5:
                slide(fr, block(980, 230, BLACK, 40), 540, 960, tc, BEAT * 0.5, dx=-1200, dur=0.1)
            slam(fr, txt(b["cap"], fit(180, b["cap"], 900), c), 540, 960, tc, BEAT * 0.5, 0.14, 2.0)
            slam(fr, txt("GOES TO...", 90, CREAM), 540, 1160, tc, BEAT * 0.75, 0.12, 1.5)
            return
        tf = tc - BEAT
        p = clamp(tf / (BEAT * 0.9))
        sx = abs(math.cos(math.pi * p))
        img = back if p < 0.5 else front
        if p >= 1 and BEAT * 1.2 < tf < BEAT * 2.4:
            img = shine(front, (tf - BEAT * 1.2) / (BEAT * 1.2))
        elif p >= 1 and BEAT * 5 < tf < BEAT * 6.2:
            img = shine(front, (tf - BEAT * 5) / (BEAT * 1.2))
        s = 0.62 + 0.38 * out_back(tf / (BEAT * 0.5)) if tf < BEAT * 0.5 else 1.0
        s *= 1 + 0.015 * math.sin(tf * 2 * math.pi / BEAT)
        fr.blit(img, 540, 900 + 30 * math.sin(tf * 1.3), s, 0, 1, max(0.02, sx))
        if tf > BEAT * 2:
            label = f"#1 {b['unit']} · 3 YEARS"
            slam(fr, txt(label, 56, GOLD), 540, 1560, tf, BEAT * 2, 0.12, 1.4)
        if b["key"] == "wickets" and tf > BEAT * 3:
            slam(fr, txt("KIRAN TEJA ONLY 6 BEHIND (112)", 44, CREAM), 540, 1650, tf, BEAT * 3, 0.12, 1.3)
        if b["key"] == "runs" and tf > BEAT * 3:
            slam(fr, txt("717 CLEAR OF #2", 44, CREAM), 540, 1650, tf, BEAT * 3, 0.12, 1.3)
        if b["key"] == "catches" and tf > BEAT * 3:
            slam(fr, txt("MOST DISMISSALS: SARATH CHANDRA (42)", 44, CREAM), 540, 1650, tf, BEAT * 3, 0.12, 1.3)
    return scene


def scene_allround(fr, t):
    marquee(fr, t, text="ALL-ROUND IMPACT  •  ")
    slam(fr, txt("ALL-ROUND", 150, GOLD), 540, 250, t, 0)
    slam(fr, txt("IMPACT", 150, CREAM), 540, 420, t, BEAT * 0.5)
    for i, (fk, name, v1, l1, v2, l2, c) in enumerate(ALLROUND):
        t0 = BEAT * (1.5 + i * 1.5)
        y = 700 + i * 360
        dx = -1200 if i % 2 == 0 else 1200
        slide(fr, block(980, 300, (26, 24, 22), 30), 540, y, t, t0, dx=dx)
        slide(fr, block(18, 300, c), 60, y, t, t0, dx=dx)
        slide(fr, face(fk, 190, c), 200, y, t, t0, dx=dx)
        if t > t0 + 0.15:
            nm = txt(name, 62, CREAM)
            fr.left(nm, 330, y - 90)
            slam(fr, txt(v1, 110, c), 420, y + 20, t, t0 + 0.2, 0.12, 1.6)
            fr.blit(txt(l1, 34, MUTED), 420, y + 100, alpha=clamp((t - t0 - 0.2) / 0.2))
            slam(fr, txt("+", 90, CREAM), 590, y + 20, t, t0 + 0.3, 0.1, 1.4)
            slam(fr, txt(v2, 110, GOLD), 760, y + 20, t, t0 + BEAT, 0.12, 1.6)
            fr.blit(txt(l2, 34, MUTED), 760, y + 100, alpha=clamp((t - t0 - BEAT) / 0.2))


def scene_partnerships(fr, t):
    marquee(fr, t, text="PARTNERSHIPS  •  ")
    slam(fr, txt("PARTNERSHIPS", 140, GOLD), 540, 240, t, 0)
    for i, (fa, na, sa, fb, nb, sb, runs, sub) in enumerate(PARTNERSHIPS):
        t0 = BEAT * (1 + i * 2)
        y = 600 + i * 440
        slide(fr, face(fa, 220), 170, y, t, t0, dx=-700)
        slide(fr, face(fb, 220), 910, y, t, t0, dx=700)
        slam(fr, txt(runs, 200, CREAM), 540, y - 30, t, t0 + BEAT * 0.5, 0.14, 2.0)
        slam(fr, txt(sub, 40, GOLD), 540, y + 110, t, t0 + BEAT * 0.75, 0.1, 1.3)
        if t > t0:
            for x, nm in ((270, f"{na} {sa}"), (810, f"{nb} {sb}")):
                fr.blit(txt(nm, fit(40, nm, 440), CREAM), x, y + 180, alpha=clamp((t - t0) / 0.3))


def scene_squad(fr, t):
    marquee(fr, t, text="THE SQUAD  •  ")
    slam(fr, txt("THE SQUAD", 150, GOLD), 540, 230, t, 0)
    cols = 3
    for i, (fk, nm) in enumerate(SQUAD):
        t0 = BEAT * (0.5 + i * 0.5)
        r, cidx = divmod(i, cols)
        x = 200 + cidx * 340
        y = 440 + r * 260
        slam(fr, face(fk, 170), x, y, t, t0, 0.12, 1.8, rot=(-1) ** i * 10)
        if t > t0:
            fr.blit(txt(nm, 36, CREAM), x, y + 110, alpha=clamp((t - t0) / 0.2))
    if t > BEAT * 8:
        slam(fr, txt("1 TEAM · 1 FAMILY", 90, CREAM, stroke=8, stroke_color=RED), 540, 1720, t, BEAT * 8,
             0.14, 2.0)


def scene_moments(fr, t):
    i = min(len(MOMENTS) - 1, int(t / (BEAT * 2)))
    tl = t - i * BEAT * 2
    gold = i % 2 == 1
    if gold:
        fr.im.paste(GOLD, (0, 0, W, H))
    marquee(fr, t, text="BIG MOMENTS  •  ", color=(200, 148, 44) if gold else DIM)
    label, big, sub = MOMENTS[i]
    fg = BLACK if gold else CREAM
    slide(fr, block(700, 110, BLACK if gold else GOLD, 30), 540, 640, tl, 0, dx=-1000, dur=0.14)
    slide(fr, txt(label, fit(76, label, 640), GOLD if gold else BLACK), 540, 640, tl, 0.04, dx=-1000, dur=0.14)
    slam(fr, txt(big, fit(360, big, 1000), fg), 540, 930, tl, BEAT * 0.5, 0.14, 2.0)
    slam(fr, txt(sub, fit(64, sub, 980), RED if gold else GOLD), 540, 1230, tl, BEAT, 0.12, 1.3)


def scene_outro(fr, t):
    marquee(fr, t)
    slam(fr, _big_logo(), 540, 620, t, 0, 0.2, 2.2)
    slam(fr, txt("3 YEARS", 220, GOLD), 540, 1130, t, BEAT)
    slam(fr, txt("STRONG", 150, CREAM), 540, 1340, t, BEAT * 2)
    if t > BEAT * 3:
        slide(fr, block(820, 120, RED, 30), 540, 1540, t, BEAT * 3, dx=1000)
        slide(fr, txt("HERE'S TO MANY MORE!", 76, CREAM), 540, 1540, t, BEAT * 3.2, dx=1000)
    if t > BEAT * 4:
        slam(fr, txt("#HANLAKXI  ·  2023–2026", 54, GOLD), 540, 1700, t, BEAT * 4)


# ------------------------------------------------------------------ timeline + render
def timeline():
    seq = [("intro", scene_intro, 20), ("record", scene_record, 8)]
    seq += [(b["key"], make_board(b), 14) for b in BOARDS]
    seq += [("allround", scene_allround, 8), ("partnerships", scene_partnerships, 8),
            ("squad", scene_squad, 10), ("moments", scene_moments, 2 * len(MOMENTS)),
            ("outro", scene_outro, 12)]
    out, b = [], 0
    for name, fn, beats in seq:
        out.append((name, fn, b, beats))
        b += beats
    return out, b


_ball = {}


def ball_wipe(fr, dt):
    """A cricket ball whips diagonally across the frame around a section cut (dt = t - cut)."""
    if "img" not in _ball:
        s = 220
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((0, 0, s - 1, s - 1), fill=(186, 28, 22))
        d.ellipse((34, 26, 96, 72), fill=(226, 92, 72))
        for off in (-12, 12):
            d.arc((-100 + off, 12, 130 + off, s - 12), -60, 60, fill=CREAM, width=5)
        _ball["img"] = img
    p = (dt + 0.2) / 0.4
    if not 0 <= p <= 1:
        return
    x0, y0, x1, y1 = -200, 1500, W + 200, 300
    for k in range(7, -1, -1):
        q = p - k * 0.035
        if q < 0:
            continue
        x, y = x0 + (x1 - x0) * q, y0 + (y1 - y0) * q
        a = 1.0 if k == 0 else 0.35 * (1 - k / 8)
        fr.blit(_ball["img"], x, y, 1 - k * 0.06, -q * 720, a)


def render(f, seq, grain):
    t = f / FPS
    beat = t / BEAT
    name, fn, b0, nb = next((s for s in seq if s[2] <= beat < s[2] + s[3]), seq[-1])
    tl = t - b0 * BEAT
    since = (beat % 1) * BEAT
    amp = (22 if int(beat) == b0 else 9) * math.exp(-since * 18)
    r = random.Random(int(beat))
    fr = Frame(BLACK, (r.uniform(-1, 1) * amp, r.uniform(-1, 1) * amp))
    fn(fr, tl)
    for s in seq[1:]:
        ball_wipe(fr, t - s[2] * BEAT)
    if name != "outro":
        ticker(fr, t)
    arr = np.asarray(fr.im).astype(np.int16) + grain
    if tl < 0.1 and b0 > 0:
        arr = arr + (255 - arr) * (0.45 * (1 - tl / 0.1))
    return np.clip(arr, 0, 255).astype(np.uint8)


SR = 44100


def synth(total_beats, sections, path):
    n = int(SR * (total_beats * BEAT + 1.5))
    out = np.zeros(n)
    rng = np.random.default_rng(1)

    def add(sig, t, gain=1.0):
        i = int(t * SR)
        if 0 <= i < n:
            seg = sig[: n - i]
            out[i:i + seg.size] += seg * gain

    tk = np.arange(int(SR * 0.35)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-tk * 35)) / SR) * np.exp(-tk * 9)
    kick += 0.3 * rng.standard_normal(tk.size) * np.exp(-tk * 300)
    ts = np.arange(int(SR * 0.22)) / SR
    noise = rng.standard_normal(ts.size)
    snare = (noise - np.convolve(noise, np.ones(6) / 6, "same")) * np.exp(-ts * 22) * 0.8
    snare += 0.4 * np.sin(2 * np.pi * 190 * ts) * np.exp(-ts * 30)
    th = np.arange(int(SR * 0.05)) / SR
    hn = rng.standard_normal(th.size)
    hat = (hn - np.convolve(hn, np.ones(3) / 3, "same")) * np.exp(-th * 90) * 0.35
    ti = np.arange(int(SR * 1.2)) / SR
    impact = (np.sin(2 * np.pi * np.cumsum(30 + 90 * np.exp(-ti * 8)) / SR) * np.exp(-ti * 3)
              + 0.5 * np.convolve(rng.standard_normal(ti.size), np.ones(12) / 12, "same") * np.exp(-ti * 5))
    tw = np.arange(int(SR * 0.4)) / SR
    wn = rng.standard_normal(tw.size)
    whoosh = (wn - np.convolve(wn, np.ones(10) / 10, "same")) * np.sin(np.pi * tw / 0.4) ** 3 * 0.5

    roots = [55.0, 43.65, 65.41, 49.0]
    chords = [(220, 261.6, 329.6), (174.6, 220, 261.6), (261.6, 329.6, 392), (196, 246.9, 293.7)]
    starts = {s[2] for s in sections}
    outro = sections[-1][2]
    # breakdowns: the "AND THE ... GOES TO" beat before each card drops the kick
    breaks = {s[2] + 5 for s in sections if s[0] in ("runs", "wickets", "catches")}
    tb = np.arange(int(SR * BEAT / 2)) / SR
    tp = np.arange(int(SR * BEAT / 4)) / SR
    for b in range(total_beats):
        t = b * BEAT
        bar = (b // 4) % 4
        if b in starts and b > 0:
            add(impact, t, 0.8)
            add(whoosh, t - 0.2, 0.7)
        if b >= outro + 5:
            continue
        cold = b < 4
        if not cold and b not in breaks:
            add(kick, t, 0.9)
        if not cold and b % 2 == 1 and b not in breaks:
            add(snare, t, 0.55)
        if b in breaks:
            for k in range(4):
                add(snare, t + k * BEAT / 4, 0.25 + 0.1 * k)
        add(hat, t + BEAT / 2, 0.6)
        add(hat, t + BEAT * 0.75, 0.3)
        if not cold:
            f0 = roots[bar]
            saw = 2 * ((tb * f0) % 1) - 1
            saw = np.convolve(saw, np.ones(20) / 20, "same") * np.exp(-tb * 6)
            add(saw, t + BEAT / 2, 0.55)
        for s in range(4):
            fq = chords[bar][(b * 4 + s) % 3] * 2
            pl = (2 * np.abs(2 * ((tp * fq) % 1) - 1) - 1) * np.exp(-tp * 30)
            add(pl, t + s * BEAT / 4, 0.12 if not cold else 0.18)
    # riser into the drop at beat 4
    dur = BEAT * 4
    tr = np.arange(int(SR * dur)) / SR
    rn = rng.standard_normal(tr.size)
    add((rn - np.convolve(rn, np.ones(8) / 8, "same")) * (tr / dur) ** 2.5 * 0.35, 0)
    add(impact, BEAT * 4, 1.0)
    out = np.tanh(out * 1.2)
    out = out / np.abs(out).max() * 0.9
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def main():
    seq, beats = timeline()
    total = int(beats * BEAT * FPS)
    grain = np.random.default_rng(0).integers(-6, 7, (H, W, 1)).astype(np.int16)
    print("sections:", [(s[0], s[2], s[3]) for s in seq], f"{beats * BEAT:.1f}s")
    if "--preview" in sys.argv:
        args = [float(a) for a in sys.argv[sys.argv.index("--preview") + 1:]]
        picks = [int(x * FPS) for x in args] or [int((s[2] + s[3] * k) * BEAT * FPS)
                                                 for s in seq for k in (0.55, 0.95)]
        cols = 6
        th = [Image.fromarray(render(f, seq, grain)).resize((270, 480)) for f in picks]
        sheet = Image.new("RGB", (270 * cols, 480 * math.ceil(len(th) / cols)), "white")
        for i, im in enumerate(th):
            sheet.paste(im, ((i % cols) * 270, (i // cols) * 480))
        sheet.save(os.path.join(HERE, "reel_preview.png"))
        return
    silent, audio = os.path.join(HERE, "_reel.mp4"), os.path.join(HERE, "_reel.wav")
    out = os.path.join(HERE, "hanlak_xi_3_years_reel.mp4")
    enc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "23", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    for f in range(total):
        enc.stdin.write(render(f, seq, grain).tobytes())
        if f % 300 == 0:
            print(f"frame {f}/{total}", flush=True)
    enc.stdin.close()
    enc.wait()
    synth(beats, seq, audio)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", silent, "-i", audio, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(silent)
    os.remove(audio)
    print("wrote", out)


if __name__ == "__main__":
    main()
