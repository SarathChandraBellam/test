# Hanlak XI – 3 Years (stop-motion)

`hanlak_xi_3_years.mp4` is a 1080×1080 paper cut-out stop-motion video, about 53 seconds long, with paper foley sounds. It's animated at 12 fps and delivered at 24 fps. `poster.png` is the last frame.

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
