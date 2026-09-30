#!/usr/bin/env python3
"""Hanlak XI - 3rd anniversary stop-motion video.

Paper cut-outs, 12 fps, per-frame "boil" jitter, light flicker and paper
foley sounds. Everything is drawn in code; run:

    pip install pillow numpy imageio-ffmpeg
    python3 make_video.py            # -> hanlak_xi_3_years.mp4
    python3 make_video.py --preview  # -> contact sheet of key frames only
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
W = H = 1080
FPS = 12
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

CREAM = (238, 228, 207)
INK = (24, 22, 20)
GOLD = (204, 150, 44)
RED = (178, 40, 32)
GREEN = (44, 104, 58)
PAPER = (251, 247, 238)
GREY = (110, 104, 96)


def asset(*p):
    return os.path.join(HERE, "assets", *p)


_fonts = {}


def font(name, size):
    key = (name, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(asset("fonts", name), size)
    return _fonts[key]


ANTON = "Anton-Regular.ttf"
MARKER = "PermanentMarker-Regular.ttf"
BRUSH = "CaveatBrush-Regular.ttf"


# ---------------------------------------------------------------- textures
def lowfreq(w, h, cell, seed):
    r = np.random.default_rng(seed)
    small = r.random((max(2, h // cell + 2), max(2, w // cell + 2)))
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(img).astype(np.float32) / 255


def paper_tex(w, h, seed, strength=1.0):
    r = np.random.default_rng(seed + 99)
    t = (1 - 0.05 * lowfreq(w, h, 70, seed) - 0.035 * lowfreq(w, h, 9, seed + 1)
         - 0.045 * r.random((h, w)).astype(np.float32))
    return 1 - (1 - t) * strength


def cutout_img(img, seed, rough=True, texture=True, pad=14):
    """Give an RGBA drawing hand-cut paper edges and a paper grain."""
    w0, h0 = img.size
    canvas = Image.new("RGBA", (w0 + 2 * pad, h0 + 2 * pad), (0, 0, 0, 0))
    canvas.paste(img, (pad, pad))
    arr = np.asarray(canvas).astype(np.float32)
    h, w = arr.shape[:2]
    if rough:
        a = Image.fromarray(arr[..., 3].astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5))
        a = np.asarray(a).astype(np.float32)
        n = (lowfreq(w, h, 5, seed) - 0.5) * 80 + (lowfreq(w, h, 24, seed + 3) - 0.5) * 90
        a = np.where(a + n > 128, 255, 0).astype(np.uint8)
        a = np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32)
        arr[..., 3] = a
    if texture:
        arr[..., :3] *= paper_tex(w, h, seed + 5)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


class Sprite:
    def __init__(self, img, shadow=True, sh_off=(6, 8), sh_alpha=0.42):
        self.img = img
        self.sh = None
        self.sh_off = sh_off
        if shadow:
            w, h = img.size
            a = Image.new("L", (w + 40, h + 40), 0)
            a.paste(img.getchannel("A"), (20, 20))
            a = a.filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * sh_alpha))
            sh = Image.new("RGBA", a.size, (20, 14, 8, 0))
            sh.putalpha(a)
            self.sh = sh


def draw_center(d, text, fnt, cx, cy, fill, **kw):
    bb = d.textbbox((0, 0), text, font=fnt, **kw)
    d.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), text, font=fnt, fill=fill, **kw)


def fit_font(name, size, text, max_w):
    while size > 10:
        f = font(name, size)
        bb = f.getbbox(text)
        if bb[2] - bb[0] <= max_w:
            return f
        size -= 2
    return font(name, size)


def text_img(text, fname, size, fill, stroke=0, stroke_fill=PAPER):
    f = font(fname, size)
    bb = f.getbbox(text, stroke_width=stroke)
    img = Image.new("RGBA", (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((4 - bb[0], 4 - bb[1]), text, font=f, fill=fill,
                             stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def sticker(text, fname, size, fill, seed, stroke=10, stroke_fill=PAPER):
    return Sprite(cutout_img(text_img(text, fname, size, fill, stroke, stroke_fill), seed))


def ink(text, fname, size, fill, seed):
    """Hand-written ink straight on the table: no cut edge, no shadow."""
    return Sprite(cutout_img(text_img(text, fname, size, fill), seed, rough=False), shadow=False)


def card(w, h, fill, seed, drawfn=None, radius=6):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=fill)
    if drawfn:
        drawfn(d, w, h)
    return cutout_img(img, seed)


def strip(text, w, h, fill, color, seed, size=64):
    return Sprite(card(w, h, fill, seed,
                       lambda d, w, h: draw_center(d, text, fit_font(ANTON, size, text, w - 60),
                                                   w / 2, h / 2, color)))


def stamp(lines, seed, color=RED):
    w, h = 330, 150
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 6, w - 7, h - 7), 14, outline=color, width=8)
    draw_center(d, lines[0], font(ANTON, 64), w / 2, 60, color)
    draw_center(d, lines[1], font(ANTON, 34), w / 2, 112, color)
    arr = np.asarray(img).astype(np.float32)
    grunge = lowfreq(w, h, 3, seed) * 0.6 + lowfreq(w, h, 14, seed + 1) * 0.6
    arr[..., 3] *= np.clip(grunge * 1.3, 0, 1)
    return Sprite(Image.fromarray(arr.astype(np.uint8), "RGBA"), shadow=False)


# ---------------------------------------------------------------- props
def ball_sprite():
    s = 150
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, s - 1, s - 1), fill=RED)
    d.ellipse((22, 16, 62, 46), fill=(214, 90, 70))
    for off in (-9, 9):
        d.arc((-70 + off, 8, 90 + off, s - 8), -62, 62, fill=PAPER, width=3)
        for k in range(-50, 51, 12):
            a = math.radians(k)
            cx, cy = 10 + off + 80 * math.cos(a), s / 2 + 67 * math.sin(a)
            d.line((cx - 5, cy - 2, cx + 5, cy + 2), fill=PAPER, width=2)
    return Sprite(cutout_img(img, 11))


def logo_pieces(scale):
    """Slice the HL monogram into the five paper pieces it's made of."""
    lg = Image.open(asset("logo.png")).convert("L")
    a = (255 - np.asarray(lg)).astype(np.uint8)
    x0, x1, y0, y1 = 451, 1455, 507, 1413
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    regions = {
        "arc_top": (0, 880, 0, 907),
        "arc_bot": (0, 880, 1026, 1920),
        "bar": (0, 880, 907, 1026),
        "stem": (880, 1053, 0, 1920),
        "curve": (1053, 1920, 0, 1920),
    }
    pieces = {}
    for i, (name, (rx0, rx1, ry0, ry1)) in enumerate(regions.items()):
        m = np.zeros_like(a)
        m[ry0:ry1, rx0:rx1] = a[ry0:ry1, rx0:rx1]
        ys, xs = np.where(m > 20)
        bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        rgba = np.zeros((by1 - by0, bx1 - bx0, 4), np.uint8)
        rgba[..., :3] = INK
        rgba[..., 3] = m[by0:by1, bx0:bx1]
        img = Image.fromarray(rgba, "RGBA")
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
        off = (((bx0 + bx1) / 2 - cx) * scale, ((by0 + by1) / 2 - cy) * scale)
        pieces[name] = (Sprite(cutout_img(img, 30 + i)), off)
    return pieces


def polaroid(photo_xy, name, score, seed, tilt_tape=-6):
    sc = Image.open(asset("partnerships.jpg")).convert("RGB")
    x, y = photo_xy
    r = 58
    ph = sc.crop((x - r, y - r, x + r, y + r)).resize((168, 168), Image.LANCZOS)
    mask = Image.new("L", (168 * 4, 168 * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 168 * 4 - 1, 168 * 4 - 1), fill=255)
    mask = mask.resize((168, 168), Image.LANCZOS)
    pw, phh = 210, 262
    base = Image.new("RGBA", (pw, phh), PAPER + (255,))
    d = ImageDraw.Draw(base)
    d.rectangle((12, 12, pw - 13, 190), fill=(226, 218, 200))
    base.paste(ph, ((pw - 168) // 2, 17), mask)
    draw_center(d, name, fit_font(MARKER, 26, name, pw - 20), pw / 2, 212, INK)
    draw_center(d, score, font(ANTON, 30), pw / 2, 243, RED)
    pol = cutout_img(base, seed)
    out = Image.new("RGBA", (pol.width, pol.height + 20), (0, 0, 0, 0))
    out.paste(pol, (0, 20))
    tape = Image.new("RGBA", (100, 34), (236, 222, 170, 170))
    tape = tape.rotate(tilt_tape, expand=True, resample=Image.BICUBIC)
    out.alpha_composite(tape, ((out.width - tape.width) // 2, 8))
    return Sprite(out)


# ---------------------------------------------------------------- timeline
ACTORS = []
EVENTS = []  # (frame, kind, length_in_frames)


def K(f, x, y, r=0.0, s=1.0, e="out", sfx=None):
    return dict(f=f, x=x, y=y, r=r, s=s, e=e, sfx=sfx)


def actor(sp, keys, z=0, end=None, jitter=1.0):
    for k in keys:
        if k["sfx"]:
            EVENTS.append((k["f"], k["sfx"], 1))
    ACTORS.append(dict(sp=sp, keys=keys, z=z, end=end if end is not None else keys[-1]["f"],
                       j=jitter, id=len(ACTORS)))


def placed(sp, frm, to, f0, dur, hold, out, out_dur=7, r0=0.0, r1=0.0, s0=1.0, s1=1.0,
           z=0, sfx="thud", e="back", r_out=None, jitter=1.0):
    """Fly in from `frm`, sit at `to` until `hold`, then leave towards `out`."""
    keys = [K(f0, *frm, r0, s0), K(f0 + dur, *to, r1, s1, e, sfx), K(hold, *to, r1, s1, "lin")]
    if out is not None:
        keys.append(K(hold + out_dur, *out, r1 if r_out is None else r_out, s1, "in"))
    actor(sp, keys, z=z, jitter=jitter)


def reveal(sp, f0, dur, steps=None):
    """Hand-written 'write-on': sprite uncovers left to right over `dur` frames."""
    steps = steps or dur
    cache = {}

    def get(f):
        t = min(1.0, max(0.0, (f - f0) / dur))
        k = math.ceil(t * steps)
        if k not in cache:
            frac = k / steps
            img = sp.img.copy()
            a = np.asarray(img.getchannel("A")).copy()
            a[:, int(img.width * frac):] = 0
            img.putalpha(Image.fromarray(a))
            cache[k] = Sprite(img, shadow=False)
        return cache[k]

    EVENTS.append((f0, "scribble", dur))
    return get


def counter(make, values, f0, step=1):
    cache = {}

    def get(f):
        i = min(len(values) - 1, max(0, (f - f0) // step))
        v = values[i]
        if v not in cache:
            cache[v] = make(v)
        return cache[v]

    for i in range(1, len(values)):
        EVENTS.append((f0 + i * step, "tick", 1))
    return get


def ramp(n, count):
    return sorted(set([round(n * (i / count) ** 0.7) for i in range(count + 1)]))


OFF_L, OFF_R, OFF_T, OFF_B = -500, W + 500, -500, H + 500


def build():
    # ------------------------------------------------ 1. ball + logo assembles
    ball = ball_sprite()
    actor(ball, [K(0, -120, 610, 0), K(5, 150, 520, -200, e="lin", sfx="tock"),
                 K(9, 300, 660, -380, e="lin", sfx="tock"), K(13, 430, 560, -560, e="lin"),
                 K(17, 540, 450, -700, e="out", sfx="tock"), K(20, 540, 450, -700, 1.15),
                 K(23, 540, 450, -700, 0.05, e="in", sfx="pop")], z=5)

    L = logo_pieces(0.56)
    lx, ly = 540, 420
    starts = {"stem": ((540, OFF_T), 90), "bar": ((OFF_L, 470), -60), "arc_top": ((OFF_L, 60), -120),
              "arc_bot": ((OFF_L, 1000), 140), "curve": ((OFF_R, 900), 80)}
    exits = {"stem": (540, OFF_B), "bar": (OFF_L, 470), "arc_top": (OFF_L, -200),
             "arc_bot": (-200, OFF_B), "curve": (OFF_R, 700)}
    for i, name in enumerate(["stem", "bar", "arc_top", "arc_bot", "curve"]):
        sp, (ox, oy) = L[name]
        frm, r0 = starts[name]
        placed(sp, frm, (lx + ox, ly + oy), 22 + i * 4, 8, 86 + i, exits[name], r0=r0, z=3)

    placed(strip("HANLAK XI", 470, 128, INK, CREAM, 51, 98), (540, OFF_B), (540, 790), 44, 7, 88,
           (540, OFF_B), r1=-1.5)
    cap = ink("Est. 18 Sep 2023  ·  Hyderabad", MARKER, 42, RED, 52)
    actor(reveal(cap, 54, 12), [K(54, 540, 905), K(88, 540, 905, e="lin"), K(95, 540, OFF_B, e="in")],
          jitter=0.5)
    EVENTS.append((86, "swoosh", 1))

    # ------------------------------------------------ 2. calendar flips to 3 years
    def cal(year):
        def dr(d, w, h):
            d.rectangle((0, 0, w, 110), fill=GOLD)
            for hx in (90, w - 90):
                d.ellipse((hx - 12, 18, hx + 12, 42), fill=CREAM)
            draw_center(d, "SEPTEMBER", font(ANTON, 58), w / 2, 72, PAPER)
            draw_center(d, "18", font(ANTON, 190), w / 2, 225, INK)
            draw_center(d, str(year), font(ANTON, 70), w / 2, 350, RED)
        return Sprite(card(380, 410, PAPER, 60, dr))

    cal_sp = {y: cal(y) for y in (2023, 2024, 2025, 2026)}
    flips = [(100, 2023), (112, 2024), (121, 2025), (130, 2026)]

    def cal_get(f):
        yr = 2023
        for ff, y in flips:
            if f >= ff:
                yr = y
        return cal_sp[yr]

    for ff, _ in flips[1:]:
        EVENTS.append((ff, "flip", 1))
    actor(cal_get, [K(98, 540, OFF_B, 20), K(106, 540, 500, -3, e="back", sfx="thud"),
                    K(112, 540, 490, 2), K(114, 540, 500, -2), K(121, 540, 488, 3), K(123, 540, 500, -1),
                    K(130, 540, 486, 2), K(132, 540, 500, 0), K(140, 540, 500, 0, e="lin"),
                    K(148, 245, 330, -9, 0.62, e="out", sfx="shuffle"), K(184, 245, 330, -9, 0.62, e="lin"),
                    K(191, OFF_L, 330, -30, 0.62, e="in")], z=1)

    placed(sticker("3", ANTON, 560, GOLD, 70, stroke=14), (600, OFF_T), (640, 450), 146, 8, 184,
           (OFF_R, 450), r0=25, r1=4, z=2, sfx="stamp")
    placed(strip("YEARS", 400, 130, INK, CREAM, 71, 104), (OFF_R, 810), (640, 810), 154, 7, 185,
           (OFF_R, 810), r1=-2, z=3)
    t = ink("of Hanlak XI", MARKER, 58, RED, 72)
    actor(reveal(t, 162, 10), [K(162, 640, 925), K(186, 640, 925, e="lin"), K(192, 640, OFF_B, e="in")],
          jitter=0.5)
    EVENTS.append((184, "swoosh", 1))

    # ------------------------------------------------ 3. the record
    placed(strip("THE RECORD", 560, 108, INK, GOLD, 80, 72), (540, OFF_T), (540, 140), 194, 7, 272,
           (540, OFF_T), r1=-2)

    def matches(v):
        def dr(d, w, h):
            draw_center(d, str(v), font(ANTON, 180), 205, h / 2 + 4, INK)
            draw_center(d, "MATCHES", font(ANTON, 86), 480, h / 2 + 4, GOLD)
        return Sprite(card(680, 230, PAPER, 81, dr))

    placed(counter(matches, ramp(97, 16), 206), (OFF_L, 320), (540, 320), 199, 7, 272, (OFF_R, 320),
           r1=1.5, z=1)

    def result_card(label, fill, color, seed):
        def make(v):
            def dr(d, w, h):
                draw_center(d, str(v), font(ANTON, 170), w / 2, 128, color)
                draw_center(d, label, font(ANTON, 60), w / 2, 262, color)
            return Sprite(card(280, 320, fill, seed, dr))
        return make

    for i, (label, n, fill, color) in enumerate([("WON", 56, GREEN, PAPER), ("LOST", 40, INK, PAPER),
                                                  ("TIED", 1, GOLD, INK)]):
        f0 = 222 + i * 5
        x = 200 + i * 340
        vals = ramp(n, 10) if n > 1 else [0, 1]
        placed(counter(result_card(label, fill, color, 82 + i), vals, f0 + 7), (x, OFF_T), (x, 620), f0, 7,
               273 + i, (x, OFF_B), r0=(i - 1) * 30, r1=(i - 1) * 3, z=2)

    placed(stamp(["58% WINS", "56 OF 97 MATCHES"], 90), (540, 885), (540, 885), 250, 3, 274, (OFF_R, 885),
           s0=1.8, r0=-7, r1=-7, z=4, e="in", sfx="stamp")
    t = ink("24 Sep 2023  –  26 Sep 2026", MARKER, 44, INK, 91)
    actor(reveal(t, 240, 10), [K(240, 540, 1010), K(274, 540, 1010, e="lin"), K(280, 540, OFF_B, e="in")],
          jitter=0.5)
    EVENTS.append((272, "swoosh", 1))

    # ------------------------------------------------ 4. big moments
    moments = [
        ("HIGHEST TOTAL", "231", "vs THUNDER HAWKS", "231 all out in 36 overs · 02 Oct 2024"),
        ("BIGGEST WIN", "145 RUNS", "vs GRACE BALL TITANS", "219/10 on the board · 09 May 2026"),
        ("TOP SCORE", "104 (59)", "CHANDU BANDARU", "12 fours, 4 sixes vs Thunder Hawks"),
        ("TWIN 99s", "99 & 99", "MOHAN KAKINATI · SUNNY NAVEEN", "both off 49 balls vs Knights XI · 03 Dec 2023"),
        ("STRIKE RATE 252.9", "86 (34)", "DHEERAJ SAI KRISHNA", "7 sixes vs Nexgen CC · 06 Dec 2025"),
        ("BEST BOWLING", "6 WKTS", "K SRINIVAS", "in 3.2 overs vs Thunder Hawks · 07 Oct 2023"),
        ("MR. CONSISTENT", "6 × 50s", "AKHIL SAI", "505 runs in 9 recorded knocks, best 86"),
        ("THE TIE", "175 = 175", "HANLAK XI vs UMP", "both finished 175/8 · 01 Jun 2024"),
    ]
    m0 = 286
    placed(strip("BIG MOMENTS", 580, 108, RED, PAPER, 100, 72), (540, OFF_T), (540, 130), 280, 7,
           m0 + 19 * len(moments) + 2, (540, OFF_T), r1=1.5, z=5)
    for i, (label, big, name, sub) in enumerate(moments):
        def dr(d, w, h, label=label, big=big, name=name, sub=sub):
            d.rectangle((0, 0, w, 104), fill=GOLD)
            draw_center(d, label, fit_font(ANTON, 62, label, w - 80), w / 2, 54, INK)
            draw_center(d, big, fit_font(ANTON, 200, big, w - 90), w / 2, 258, INK)
            draw_center(d, name, fit_font(ANTON, 60, name, w - 80), w / 2, 410, RED)
            draw_center(d, sub, fit_font(BRUSH, 44, sub, w - 70), w / 2, 480, GREY)
        sp = Sprite(card(860, 540, PAPER, 110 + i, dr))
        s = m0 + i * 19
        side = OFF_L if i % 2 == 0 else OFF_R
        other = OFF_R if i % 2 == 0 else OFF_L
        tilt = -2.2 if i % 2 == 0 else 2.2
        placed(sp, (side, 620), (540, 620), s, 6, s + 14, (other, 640), out_dur=6,
               r0=-tilt * 6, r1=tilt, r_out=tilt * 4, z=1 + (i % 2), sfx="thud")
        EVENTS.append((s + 15, "swoosh", 1))

    # ------------------------------------------------ 5. partnerships
    p0 = m0 + 19 * len(moments) + 8
    placed(strip("TOP PARTNERSHIPS", 640, 104, INK, GOLD, 120, 68), (540, OFF_T), (540, 100), p0, 7,
           p0 + 96, (540, OFF_T), r1=-1.5, z=5)
    parts = [
        ((237, 828), "SARATH CHANDRA", "55 (45)", (718, 833), "AKHIL SAI", "70 (45)", "138*", "(88)", "2ND WICKET"),
        ((235, 1068), "MOHAN KAKINATI", "99 (49)", (712, 1072), "VIJAY CHINNU", "26 (23)", "137*", "(69)",
         "2ND WICKET"),
        ((234, 1300), "YGPREDDY", "57 (27)", (706, 1305), "AKHIL SAI", "53 (21)", "122", "(47)", "1ST WICKET"),
    ]
    for i, (pa, na, sa, pb, nb, sb, runs, balls, wk) in enumerate(parts):
        y = 300 + i * 270
        r = p0 + 8 + i * 20
        end = p0 + 96 + i
        placed(polaroid(pa, na, sa, 130 + i, -8), (OFF_L, y), (175, y), r, 6, end, (OFF_L, y),
               r0=-30, r1=-4 + i * 2, s1=0.98, z=2)
        placed(polaroid(pb, nb, sb, 140 + i, 7), (OFF_R, y), (905, y), r + 3, 6, end, (OFF_R, y),
               r0=30, r1=4 - i * 2, s1=0.98, z=2)

        def num(runs=runs, balls=balls):
            a = text_img(runs, ANTON, 150, INK, 10)
            b = text_img(balls, ANTON, 64, GREY, 8)
            img = Image.new("RGBA", (a.width + b.width + 6, a.height), (0, 0, 0, 0))
            img.paste(a, (0, 0))
            img.paste(b, (a.width + 6, a.height - b.height - 12))
            return Sprite(cutout_img(img, 150))
        placed(num(), (545, y - 20), (545, y - 20), r + 9, 3, end, (540, OFF_B), s0=1.9, r0=-8,
               r1=(i - 1) * 2, e="in", sfx="stamp", z=3)
        placed(strip(wk, 250, 62, GOLD, INK, 160 + i, 40), (545, OFF_B), (545, y + 80), r + 12, 5, end,
               (540, OFF_B), r1=(1 - i) * 2, z=4, sfx="tick")
    EVENTS.append((p0 + 95, "swoosh", 1))

    # ------------------------------------------------ 6. finale
    f0 = p0 + 106
    L2 = logo_pieces(0.5)
    lx, ly = 540, 395
    for i, name in enumerate(["curve", "arc_bot", "arc_top", "bar", "stem"]):
        sp, (ox, oy) = L2[name]
        frm, r0 = starts[name]
        placed(sp, frm, (lx + ox, ly + oy), f0 + i * 3, 7, 10_000, None, r0=-r0, z=3)
    fz = f0 + 20
    placed(strip("3 YEARS STRONG", 520, 124, GOLD, INK, 170, 88), (OFF_L, 700), (540, 700), fz, 7, 10_000,
           None, r1=-2, z=4)
    placed(strip("HANLAK XI  ·  HYDERABAD", 560, 92, INK, CREAM, 171, 58), (OFF_R, 812), (540, 812),
           fz + 5, 7, 10_000, None, r1=1.5, z=4)
    t = ink("Here's to many more!", MARKER, 60, RED, 172)
    actor(reveal(t, fz + 13, 12), [K(fz + 13, 540, 925), K(10_000, 540, 925, e="lin")], jitter=0.5)
    t = ink("18.09.2023  —  18.09.2026", BRUSH, 44, GREY, 173)
    actor(reveal(t, fz + 26, 8), [K(fz + 26, 540, 1000), K(10_000, 540, 1000, e="lin")], jitter=0.5)

    # confetti: paper scraps dropped onto the table, one or two per frame
    r = random.Random(5)
    colours = [GOLD, RED, GREEN, INK, PAPER, GOLD]
    for i in range(46):
        w, h = r.randint(16, 34), r.randint(8, 18)
        img = Image.new("RGBA", (w, h), colours[i % len(colours)] + (255,))
        sp = Sprite(cutout_img(img, 200 + i), sh_off=(3, 4))
        while True:
            x, y = r.randint(30, W - 30), r.randint(30, H - 30)
            if not (150 < x < 930 and 150 < y < 1040):
                break
        s = fz + 8 + i // 2
        actor(sp, [K(s, x + r.randint(-80, 80), -60, r.uniform(-180, 180)),
                   K(s + 5, x, y, r.uniform(-90, 90), e="out"), K(10_000, x, y, 0, e="lin")], z=0,
              jitter=0.6)
    return fz + 60  # total frames


# ---------------------------------------------------------------- render
EASE = {
    "lin": lambda t: t,
    "out": lambda t: 1 - (1 - t) ** 3,
    "in": lambda t: t ** 3,
    "back": lambda t: 1 + 2.4 * (t - 1) ** 3 + 1.4 * (t - 1) ** 2,
}


def pose(a, f):
    ks = a["keys"]
    if f < ks[0]["f"] or f > a["end"]:
        return None
    for k0, k1 in zip(ks, ks[1:]):
        if k0["f"] <= f <= k1["f"]:
            t = (f - k0["f"]) / max(1, k1["f"] - k0["f"])
            e = EASE[k1["e"]](t)
            return {c: k0[c] + (k1[c] - k0[c]) * e for c in ("x", "y", "r", "s")}
    return {c: ks[-1][c] for c in ("x", "y", "r", "s")}


def paste(canvas, sp, x, y, r, s):
    img, sh = sp.img, sp.sh
    if abs(s - 1) > 1e-3:
        img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.BICUBIC)
        if sh:
            sh = sh.resize((max(1, round(sh.width * s)), max(1, round(sh.height * s))), Image.BICUBIC)
    if abs(r) > 0.05:
        img = img.rotate(r, Image.BICUBIC, expand=True)
        if sh:
            sh = sh.rotate(r, Image.BICUBIC, expand=True)
    if sh:
        canvas.paste(sh, (round(x - sh.width / 2 + sp.sh_off[0]), round(y - sh.height / 2 + sp.sh_off[1])), sh)
    canvas.paste(img, (round(x - img.width / 2), round(y - img.height / 2)), img)


def make_backgrounds():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = 1 - 0.22 * np.clip(d - 0.45, 0, None) ** 1.6
    bgs = []
    for i in range(3):
        t = paper_tex(W, H, 900 + i, 1.2) * vig
        bgs.append(np.clip(np.array(CREAM, np.float32)[None, None] * t[..., None], 0, 255).astype(np.uint8))
    return bgs


def render_frame(f, bgs):
    canvas = Image.fromarray(bgs[(f // 2) % len(bgs)])
    live = [(a, p) for a in ACTORS if (p := pose(a, f))]
    live.sort(key=lambda ap: ap[0]["z"])
    for a, p in live:
        sp = a["sp"](f) if callable(a["sp"]) else a["sp"]
        rnd = random.Random(a["id"] * 100003 + f)
        j = a["j"]
        paste(canvas, sp, p["x"] + rnd.uniform(-1.6, 1.6) * j, p["y"] + rnd.uniform(-1.6, 1.6) * j,
              p["r"] + rnd.uniform(-0.5, 0.5) * j, p["s"])
    arr = np.asarray(canvas).astype(np.float32)
    flicker = 1 + random.Random(f * 7 + 1).uniform(-0.025, 0.025)
    return np.clip(arr * flicker, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- sound
SR = 44100


def lp(x, n):
    return np.convolve(x, np.ones(n) / n, mode="same")


def sfx(kind, frames):
    r = np.random.default_rng(abs(hash(kind)) % 1000)
    if kind in ("thud", "stamp", "tock"):
        dur = 0.3
        t = np.arange(int(SR * dur)) / SR
        f = (70 if kind != "tock" else 160) + 70 * np.exp(-t * 30)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (16 if kind != "tock" else 28))
        slap = lp(r.standard_normal(t.size), 6 if kind != "tock" else 3) * np.exp(-t * 70)
        return 0.55 * body + (0.5 if kind == "stamp" else 0.3) * slap
    if kind == "tick":
        t = np.arange(int(SR * 0.05)) / SR
        return 0.25 * (r.standard_normal(t.size) - lp(r.standard_normal(t.size), 8)) * np.exp(-t * 160)
    if kind == "flip":
        t = np.arange(int(SR * 0.12)) / SR
        n = r.standard_normal(t.size)
        return 0.3 * (n - lp(n, 4)) * np.exp(-t * 40) * (1 - np.exp(-t * 400))
    if kind == "pop":
        t = np.arange(int(SR * 0.15)) / SR
        return 0.45 * np.sin(2 * np.pi * np.cumsum(220 + 600 * np.exp(-t * 25)) / SR) * np.exp(-t * 25)
    if kind in ("swoosh", "shuffle"):
        dur = 0.32
        t = np.arange(int(SR * dur)) / SR
        n = lp(r.standard_normal(t.size), 5)
        n = n - lp(n, 60)
        return 0.5 * n * np.sin(np.pi * t / dur) ** 2
    if kind == "scribble":
        dur = frames / FPS
        t = np.arange(int(SR * dur)) / SR
        n = r.standard_normal(t.size)
        n = n - lp(n, 3)
        strokes = 0.5 + 0.5 * np.sin(2 * np.pi * 7 * t + 3 * np.sin(2 * np.pi * 2.3 * t))
        return 0.07 * n * strokes * np.minimum(1, t * 20) * np.minimum(1, (dur - t) * 20)
    return np.zeros(1)


def make_audio(total_frames, path):
    out = np.zeros(int(SR * (total_frames / FPS + 1)))
    for f, kind, n in EVENTS:
        s = sfx(kind, n)
        i = int(SR * f / FPS)
        if 0 <= i < out.size:
            seg = s[: out.size - i]
            out[i:i + seg.size] += seg
    # a quiet room tone keeps the silence from sounding dead
    out += 0.004 * lp(np.random.default_rng(3).standard_normal(out.size), 30)
    out = out / max(1e-6, np.abs(out).max()) * 0.8
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def main():
    total = build()
    bgs = make_backgrounds()
    if "--preview" in sys.argv:
        picks = [int(a) for a in sys.argv[sys.argv.index("--preview") + 1:]] or list(range(0, total, total // 12))
        thumbs = [Image.fromarray(render_frame(f, bgs)).resize((360, 360)) for f in picks]
        cols = 4
        sheet = Image.new("RGB", (360 * cols, 360 * math.ceil(len(thumbs) / cols)), "white")
        for i, t in enumerate(thumbs):
            ImageDraw.Draw(t).text((8, 8), str(picks[i]), fill=RED)
            sheet.paste(t, ((i % cols) * 360, (i // cols) * 360))
        sheet.save(os.path.join(HERE, "preview.png"))
        print("frames:", total, "->", os.path.join(HERE, "preview.png"))
        return

    silent = os.path.join(HERE, "_video.mp4")
    audio = os.path.join(HERE, "_audio.wav")
    out = os.path.join(HERE, "hanlak_xi_3_years.mp4")
    enc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-vf", "fps=24",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", silent],
                           stdin=subprocess.PIPE)
    for f in range(total):
        enc.stdin.write(render_frame(f, bgs).tobytes())
        if f % 60 == 0:
            print(f"frame {f}/{total}", flush=True)
    enc.stdin.close()
    enc.wait()
    Image.fromarray(render_frame(total - 1, bgs)).save(os.path.join(HERE, "poster.png"))
    make_audio(total, audio)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", silent, "-i", audio, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(silent)
    os.remove(audio)
    print("wrote", out, f"({total / FPS:.1f}s)")


if __name__ == "__main__":
    main()
