# Hanlak XI – 3 Years (stop-motion)

`hanlak_xi_3_years.mp4` is a 1080×1080 paper cut-out stop-motion video, about 53 seconds long, with paper foley sounds. It's animated at 12 fps and delivered at 24 fps. `poster.png` is the last frame.

`hanlak_xi_3_years_whatsapp.mp4` is a smaller 720×720 copy for sharing on WhatsApp.

Scenes:
1. A cricket ball rolls in and the HL monogram assembles piece by piece. Then "HANLAK XI" appears with "Est. 18 Sep 2023 · Hyderabad".
2. A calendar flips from 18 Sep 2023 to 2026, and "3 YEARS" drops in.
3. The record: 97 matches, 56 won, 40 lost and 1 tied.
4. Big moments: 231 highest total, 145-run win, Chandu Bandaru 104 (59), twin 99s, Dheeraj 86 (34), K Srinivas 6 wickets, Akhil Sai's six 50s, and the 175 = 175 tie.
5. Top partnerships: 138\*, 137\* and 122, with player polaroids.
6. Finale: the logo, "3 YEARS STRONG", "Here's to many more!" and confetti.

The stats come from the Hanlak XI scorecard report and the CricHeroes partnership leaderboard.

## Re-render

```bash
pip install pillow numpy imageio-ffmpeg
python3 make_video.py              # full video + poster
python3 make_video.py --preview    # contact sheet of key frames (preview.png)
```

To change text or stats, edit `build()` in `make_video.py`. For example, the `moments` list sets the big-moment cards and `parts` sets the partnerships.

## 1-minute reel (9:16)

`hanlak_xi_3_years_reel.mp4` is a 1080×1920 vertical reel, about 58 seconds long, cut to a 128 BPM synthesized beat. `hanlak_xi_3_years_reel_whatsapp.mp4` is a 720p copy of it for sharing.

It's styled like an IPL broadcast: a running "LIVE" stats ticker, a cricket ball whipping across the screen at every cut, and kinetic type on every beat.

1. **Cold open:** "18 SEP 2023, ONE TEAM, ONE DREAM, 3 YEARS LATER…", then the logo drops and "3 YEARS STRONG" lands.
2. **Record:** 97 matches, 56 won, 40 lost and 1 tied.
3. **Leaderboards:** each board counts down #5 to #2, then the beat breaks with "AND THE ORANGE CAP GOES TO…". The #1 player's card flips over with a light sweep across it.
   - Runs: Akhil Sai, 1732 (Orange Cap)
   - Wickets: Surya, 118 (Purple Cap)
   - Catches: Kiran Teja, 23 (Safest Hands)
4. **All-round impact:** Akhil Sai, Surya and Kiran Teja.
5. **Partnerships:** 138\*, 137\* and 122.
6. **The squad:** a wall of 14 player photos.
7. **Big moments:** 8 quick-fire cards.
8. **Outro.**

The data sits at the top of `make_reel.py` in `BOARDS`, `ALLROUND`, `PARTNERSHIPS`, `SQUAD` and `MOMENTS`. The player photos are cropped from the CricHeroes screenshots in `assets/`. Re-render with `python3 make_reel.py`, or use `--preview` for a contact sheet.

Catches are ranked from the Field tab, which CricHeroes sorts by dismissals. Anyone below #7 there has at most 17 dismissals, so the top 5 by catches is complete.
