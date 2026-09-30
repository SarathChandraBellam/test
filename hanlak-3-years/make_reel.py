#!/usr/bin/env python3
"""Hanlak XI - 3 years, fast beat-synced reel (9:16, 30 fps, 128 BPM).

Kinetic typography cut to a synthesized beat: every hit lands on a beat.
Top-5 leaderboards come from LEADERS below; a section with no rows is skipped.

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

# Top-5 leaderboards (name, value, small print). Fill from CricHeroes
# Leaderboard -> Bat / Bowl / Field. Empty list = section is left out.
LEADERS = {
    "runs": [],
    "wickets": [],
    "catches": [],
}
if os.environ.get("LEADERS_JSON"):  # e.g. a test file, same shape as LEADERS
    import json
    LEADERS.update(json.load(open(os.environ["LEADERS_JSON"])))

MOMENTS = [
    ("HIGHEST TOTAL", "231", "vs THUNDER HAWKS · 2024"),
    ("BIGGEST WIN", "145 RUNS", "vs GRACE BALL TITANS · 2026"),
    ("TOP SCORE", "104", "CHANDU BANDARU · 59 BALLS"),
    ("TWIN 99s", "99 & 99", "MOHAN KAKINATI · SUNNY NAVEEN"),
    ("STRIKE RATE", "252.9", "DHEERAJ SAI KRISHNA · 86 (34)"),
    ("BEST BOWLING", "6 WKTS", "K SRINIVAS · 3.2 OVERS"),
    ("MOST FIFTIES", "6+", "AKHIL SAI · 505+ RUNS"),
    ("THE TIE", "175 = 175", "vs UMP · 01 JUN 2024"),
]

PARTNERSHIPS = [
    ((237, 828), "SARATH CHANDRA", "55(45)", (718, 833), "AKHIL SAI", "70(45)", "138*", "88 BALLS · 2ND WKT"),
    ((235, 1068), "MOHAN KAKINATI", "99(49)", (712, 1072), "VIJAY CHINNU", "26(23)", "137*", "69 BALLS · 2ND WKT"),
    ((234, 1300), "YGPREDDY", "57(27)", (706, 1305), "AKHIL SAI", "53(21)", "122", "47 BALLS · 1ST WKT"),
]


def asset(*p):
    return os.path.join(HERE, "assets", *p)


ANTON = "Anton-Regular.ttf"
MARKER = "PermanentMarker-Regular.ttf"
_fonts, _txt = {}, {}


def font(name, size):
    if (name, size) not in _fonts:
        _fonts[(name, size)] = ImageFont.truetype(asset("fonts", name), size)
    return _fonts[(name, size)]


def fit(name, size, text, max_w):
    while size > 12 and font(name, size).getlength(text) > max_w:
        size -= 4
    return size


def txt(text, size, color, name=ANTON, stroke=0, stroke_color=BLACK):
    key = (text, size, color, name, stroke, stroke_color)
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
    a = Image.eval(lg, lambda v: 255 - v)
    img = Image.new("RGBA", lg.size, color + (255,))
    img.putalpha(a)
    return img.resize((width, round(width * lg.height / lg.width)), Image.LANCZOS)


def avatar(xy, d):
    sc = Image.open(asset("partnerships.jpg")).convert("RGB")
    x, y = xy
    ph = sc.crop((x - 58, y - 58, x + 58, y + 58)).resize((d, d), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    ph.putalpha(m.resize((d, d), Image.LANCZOS))
    ring = Image.new("RGBA", (d + 16, d + 16), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, d + 15, d + 15), fill=GOLD)
    ring.alpha_composite(ph, (8, 8))
    return ring


# ---------------------------------------------------------------- motion
def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def out_back(t):
    t = clamp(t)
    return 1 + 2.7 * (t - 1) ** 3 + 1.7 * (t - 1) ** 2


def out_cubic(t):
    return 1 - (1 - clamp(t)) ** 3


class Frame:
    """One frame's canvas plus camera shake."""

    def __init__(self, bg, shake=(0, 0)):
        self.im = Image.new("RGB", (W, H), bg)
        self.dx, self.dy = shake

    def blit(self, img, cx, cy, s=1.0, rot=0.0, alpha=1.0):
        if img is None or s <= 0.01 or alpha <= 0.01:
            return
        if abs(s - 1) > 1e-3:
            img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.BILINEAR)
        if abs(rot) > 0.05:
            img = img.rotate(rot, Image.BILINEAR, expand=True)
        if alpha < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
        self.im.paste(img, (round(cx - img.width / 2 + self.dx), round(cy - img.height / 2 + self.dy)), img)


def slam(fr, img, cx, cy, t, t0, dur=0.16, frm=1.8, rot=0.0):
    """Punch in from big to 1:1 on the beat."""
    if t < t0:
        return
    k = out_back((t - t0) / dur)
    fr.blit(img, cx, cy, frm + (1 - frm) * k, rot * (1 - k), clamp((t - t0) / (dur * 0.5)))


def slide(fr, img, cx, cy, t, t0, dx=0, dy=0, dur=0.2):
    if t < t0:
        return
    k = out_cubic((t - t0) / dur)
    fr.blit(img, cx + dx * (1 - k), cy + dy * (1 - k), 1, 0, clamp((t - t0) / (dur * 0.4)))


# ---------------------------------------------------------------- scenes
MARQUEE = {}


def marquee(fr, t, color=DIM, text="HANLAK XI  •  3 YEARS  •  "):
    if color not in MARQUEE:
        row = txt(text * 4, 300, (0, 0, 0, 0), stroke=3, stroke_color=color)
        MARQUEE[color] = row
    row = MARQUEE[color]
    period = row.width / 4
    for i, y in enumerate((230, 620, 1010, 1400, 1790)):
        speed = 160 if i % 2 else -160
        x = (t * speed) % period - period
        fr.im.paste(row, (round(x + fr.dx), y - 150), row)


def scene_intro(fr, t, L):
    marquee(fr, t)
    lg = L["logo_cream"]
    if t < BEAT * 4:
        slam(fr, lg, 540, 900, t, 0, 0.2, 2.4)
        if t > BEAT * 2:
            slam(fr, txt("HANLAK XI", 150, GOLD), 540, 1400, t, BEAT * 2)
        return
    fr.blit(L["logo_gold_small"], 540, 330)
    slam(fr, txt("3", 900, GOLD), 280, 930, t, BEAT * 4, 0.18, 2.2, rot=-12)
    slam(fr, txt("YEARS", 220, CREAM), 770, 790, t, BEAT * 5)
    slam(fr, txt("STRONG", 200, RED), 770, 1070, t, BEAT * 6)
    if t > BEAT * 8:
        slide(fr, block(760, 110, CREAM, 30), 540, 1440, t, BEAT * 8, dx=-900)
        slide(fr, txt("18.09.2023  →  18.09.2026", 70, BLACK), 540, 1440, t, BEAT * 8.25, dx=900)
    if t > BEAT * 10:
        slam(fr, txt("HYDERABAD · TELANGANA", 64, GOLD), 540, 1580, t, BEAT * 10)
    if t > BEAT * 12:
        i = min(3, int(t / BEAT) - 12)
        word = ("97 MATCHES", "3 SEASONS", "1 FAMILY", "1 FAMILY")[i]
        slam(fr, txt(word, 80, CREAM), 540, 1730, t, BEAT * (12 + min(i, 2)), 0.1, 1.5)


def scene_record(fr, t, L):
    marquee(fr, t)
    n = int(97 * out_cubic(t / BEAT))
    fr.blit(txt(str(n), 520, GOLD), 540, 520, 1 + 0.08 * max(0, 1 - t / 0.2))
    slam(fr, txt("MATCHES", 150, CREAM), 540, 880, t, BEAT * 0.5)
    rows = [("56", "WON", GREEN), ("40", "LOST", CREAM), ("1", "TIED", GOLD)]
    for i, (num, lab, col) in enumerate(rows):
        t0 = BEAT * (2 + i)
        y = 1110 + i * 190
        slide(fr, block(820, 160, col, 40), 540, y, t, t0, dx=-1200 if i % 2 == 0 else 1200)
        tc = BLACK
        slide(fr, txt(num, 130, tc), 330, y, t, t0 + 0.06, dx=-1200 if i % 2 == 0 else 1200)
        slide(fr, txt(lab, 110, tc), 680, y, t, t0 + 0.06, dx=-1200 if i % 2 == 0 else 1200)
    if t > BEAT * 5:
        slam(fr, L["stamp"], 800, 1700, t, BEAT * 5, 0.12, 2.5, rot=30)


def make_board(title, unit, rows):
    def scene(fr, t, L):
        marquee(fr, t, text=f"{title}  •  ")
        slam(fr, txt(title, fit(ANTON, 150, title, 980), GOLD), 540, 300, t, 0)
        slam(fr, txt(f"TOP 5 · {unit}", 60, CREAM), 540, 450, t, BEAT * 0.5)
        top = max(r[1] for r in rows)
        # count down: #5 lands first, #1 last
        for rank in range(len(rows), 0, -1):
            name, val, sub = rows[rank - 1]
            t0 = BEAT * (1 + (len(rows) - rank))
            if t < t0:
                continue
            y = 640 + (rank - 1) * 250
            one = rank == 1
            k = out_cubic((t - t0) / 0.45)
            bar_w = int(60 + 560 * (val / top) * k)
            slam(fr, txt(f"#{rank}", 120, RED if one else GOLD), 105, y + 10, t, t0, 0.12, 1.6)
            nm = txt(name, fit(ANTON, 70, name, 560 if sub else 820), CREAM)
            slide(fr, nm, 200 + nm.width / 2, y - 40, t, t0, dx=-300, dur=0.15)
            if sub:
                sb = txt(sub, 44, (150, 142, 128))
                fr.blit(sb, 1000 - sb.width / 2, y - 36, alpha=clamp((t - t0) / 0.3))
            bar = block(bar_w, 70, GOLD if one else (72, 67, 62), 18)
            fr.blit(bar, 200 + bar.width / 2, y + 60)
            v = txt(str(int(round(val * k))), 84, GOLD if one else CREAM)
            fr.blit(v, 200 + bar.width + 24 + v.width / 2, y + 60)
    return scene


def scene_partnerships(fr, t, L):
    marquee(fr, t, text="PARTNERSHIPS  •  ")
    slam(fr, txt("PARTNERSHIPS", 140, GOLD), 540, 250, t, 0)
    for i, (pa, na, sa, pb, nb, sb, runs, sub) in enumerate(PARTNERSHIPS):
        t0 = BEAT * (1 + i * 2)
        y = 620 + i * 460
        slide(fr, L["av"][i][0], 170, y, t, t0, dx=-700)
        slide(fr, L["av"][i][1], 910, y, t, t0, dx=700)
        slam(fr, txt(runs, 200, CREAM), 540, y - 30, t, t0 + BEAT * 0.5, 0.14, 2.0)
        slam(fr, txt(sub, 40, GOLD), 540, y + 110, t, t0 + BEAT * 0.75, 0.1, 1.3)
        if t > t0:
            fr.blit(txt(f"{na} {sa}", fit(ANTON, 40, f"{na} {sa}", 440), CREAM), 270, y + 190,
                    alpha=clamp((t - t0) / 0.3))
            fr.blit(txt(f"{nb} {sb}", fit(ANTON, 40, f"{nb} {sb}", 440), CREAM), 810, y + 190,
                    alpha=clamp((t - t0) / 0.3))


def scene_moments(fr, t, L):
    i = min(len(MOMENTS) - 1, int(t / (BEAT * 2)))
    tl = t - i * BEAT * 2
    gold = i % 2 == 1
    if gold:
        fr.im.paste(GOLD, (0, 0, W, H))
    marquee(fr, t, color=(200, 148, 44) if gold else DIM, text="BIG MOMENTS  •  ")
    label, big, sub = MOMENTS[i]
    fg = BLACK if gold else CREAM
    acc = RED if gold else GOLD
    slide(fr, block(700, 110, BLACK if gold else GOLD, 30), 540, 640, tl, 0, dx=-1000, dur=0.14)
    slide(fr, txt(label, fit(ANTON, 76, label, 640), GOLD if gold else BLACK), 540, 640, tl, 0.04, dx=-1000,
          dur=0.14)
    slam(fr, txt(big, fit(ANTON, 360, big, 1000), fg), 540, 930, tl, BEAT * 0.5, 0.14, 2.0)
    slam(fr, txt(sub, fit(ANTON, 64, sub, 980), acc), 540, 1230, tl, BEAT, 0.12, 1.3)


def scene_outro(fr, t, L):
    marquee(fr, t)
    slam(fr, L["logo_cream"], 540, 640, t, 0, 0.2, 2.2)
    slam(fr, txt("3 YEARS", 220, GOLD), 540, 1150, t, BEAT)
    slam(fr, txt("STRONG", 150, CREAM), 540, 1360, t, BEAT * 2)
    if t > BEAT * 3:
        slide(fr, block(820, 120, RED, 30), 540, 1560, t, BEAT * 3, dx=1000)
        slide(fr, txt("HERE'S TO MANY MORE!", 76, CREAM), 540, 1560, t, BEAT * 3.2, dx=1000)
    if t > BEAT * 4:
        slam(fr, txt("#HANLAKXI  ·  2023–2026", 54, GOLD), 540, 1720, t, BEAT * 4)


# ---------------------------------------------------------------- timeline + render
def timeline():
    seq = [("intro", scene_intro, 16), ("record", scene_record, 8)]
    for key, title, unit in (("runs", "TOP RUN SCORERS", "RUNS"), ("wickets", "TOP WICKET TAKERS", "WICKETS"),
                             ("catches", "SAFEST HANDS", "CATCHES")):
        rows = LEADERS[key][:5]
        if rows:
            seq.append((key, make_board(title, unit, rows), len(rows) + 5))
    seq += [("partnerships", scene_partnerships, 8), ("moments", scene_moments, 2 * len(MOMENTS)),
            ("outro", scene_outro, 12)]
    out, b = [], 0
    for name, fn, beats in seq:
        out.append((name, fn, b, beats))
        b += beats
    return out, b


def load_assets():
    L = {"logo_cream": logo(CREAM, 820), "logo_gold_small": logo(GOLD, 300)}
    st = Image.new("RGBA", (440, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(st)
    d.rounded_rectangle((6, 6, 433, 183), 18, outline=RED, width=10)
    d.text((220, 72), "58% WINS", font=font(ANTON, 90), fill=RED, anchor="mm")
    d.text((220, 148), "56 OF 97", font=font(ANTON, 44), fill=RED, anchor="mm")
    L["stamp"] = st.rotate(-10, Image.BICUBIC, expand=True)
    L["av"] = [(avatar(p[0], 240), avatar(p[3], 240)) for p in PARTNERSHIPS]
    return L


def render(f, seq, L, grain):
    t = f / FPS
    beat = t / BEAT
    name, fn, b0, nb = next((s for s in seq if s[2] <= beat < s[2] + s[3]), seq[-1])
    tl = t - b0 * BEAT
    # camera kick on every beat, bigger on section starts
    since = (beat % 1) * BEAT
    amp = (22 if int(beat) == b0 else 9) * math.exp(-since * 18)
    r = random.Random(int(beat))
    fr = Frame(BLACK, (r.uniform(-1, 1) * amp, r.uniform(-1, 1) * amp))
    fn(fr, tl, L)
    arr = np.asarray(fr.im).astype(np.int16)
    arr += grain[f % len(grain)]
    # white flash on section starts
    if tl < 0.1:
        k = 1 - tl / 0.1
        arr = arr + (255 - arr) * (0.55 * k)
    return np.clip(arr, 0, 255).astype(np.uint8)


SR = 44100


def synth(total_beats, sections, path):
    n = int(SR * (total_beats * BEAT + 1.5))
    out = np.zeros(n)
    rng = np.random.default_rng(1)

    def add(sig, t, gain=1.0):
        i = int(t * SR)
        if i < n:
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

    roots = [55.0, 43.65, 65.41, 49.0]  # A F C G
    chords = [(220, 261.6, 329.6), (174.6, 220, 261.6), (261.6, 329.6, 392), (196, 246.9, 293.7)]
    last = sections[-1][2] + 4  # groove stops a bar into the outro
    starts = {s[2] for s in sections}
    for b in range(total_beats):
        t = b * BEAT
        bar = (b // 4) % 4
        if b in starts:
            add(impact, t, 0.8)
        if b >= last:
            continue
        add(kick, t, 0.9)
        if b % 2 == 1:
            add(snare, t, 0.55)
        add(hat, t + BEAT / 2, 0.6)
        add(hat, t + BEAT * 0.75, 0.3)
        # bass: off-beat 8ths
        tb = np.arange(int(SR * BEAT / 2)) / SR
        f0 = roots[bar]
        saw = 2 * ((tb * f0) % 1) - 1
        saw = np.convolve(saw, np.ones(20) / 20, "same") * np.exp(-tb * 6)
        add(saw, t + BEAT / 2, 0.55)
        # pluck arp: 16ths
        tp = np.arange(int(SR * BEAT / 4)) / SR
        for s in range(4):
            fq = chords[bar][(b * 4 + s) % 3] * 2
            pl = (2 * np.abs(2 * ((tp * fq) % 1) - 1) - 1) * np.exp(-tp * 30)
            add(pl, t + s * BEAT / 4, 0.12)
    # risers into each section
    for s in sections[1:]:
        dur = BEAT * 2
        tr = np.arange(int(SR * dur)) / SR
        rn = rng.standard_normal(tr.size)
        rn = rn - np.convolve(rn, np.ones(8) / 8, "same")
        add(rn * (tr / dur) ** 2 * 0.25, s[2] * BEAT - dur)
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
    L = load_assets()
    grain = [np.random.default_rng(0).integers(-6, 7, (H, W, 1)).astype(np.int16)]
    print("sections:", [(s[0], s[2], s[3]) for s in seq], f"{beats * BEAT:.1f}s")
    if "--preview" in sys.argv:
        picks = [int(x * FPS) for x in [0.3, 1.2, 2.6, 4.6, 7.2, 8.4, 10.5] +
                 [s[2] * BEAT + BEAT * (s[3] - 1) for s in seq[1:]]]
        cols = 5
        th = [Image.fromarray(render(f, seq, L, grain)).resize((270, 480)) for f in picks]
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
        enc.stdin.write(render(f, seq, L, grain).tobytes())
        if f % 150 == 0:
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
