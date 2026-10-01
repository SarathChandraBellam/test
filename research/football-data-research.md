# American Football (NFL) & European Football Data Research
### For building an "ask the agent" analytics site like the existing IPL one

_Research date: 1 Oct 2026. Prices and terms change often, so check each provider's page before you commit. This is not legal advice._

---

## 1. TL;DR

| Question | Answer |
|---|---|
| **Is there solid, free NFL data I can build on?** | **Yes, and it's better than what most sports have.** **nflverse** (`nflreadpy` for Python, `nflreadr` for R) gives play-by-play for every NFL play since **1999** with EPA, win probability, CPOE, Vegas lines, rosters, snap counts, injuries, depth charts, Next Gen Stats aggregates and fantasy opportunity data. Most of it is **CC-BY 4.0** (commercial use OK with attribution). FTN charting data is **CC-BY-SA 4.0**. |
| **Best paid NFL upgrade?** | **SportsDataIO** for a real-time, fantasy- and betting-friendly API at indie budgets (Discovery Lab is roughly $99–149/mo, but data is next-day). Enterprise options are **Sportradar** (around $10k+/mo) and **Genius Sports**, the NFL's *exclusive* official betting data distributor through the 2029 season. |
| **Odds data?** | **The Odds API**: free 500 credits/mo, then $30–$249/mo. It covers US, UK, EU and AU books, player props, and historical odds back to mid-2020. |
| **Fantasy data?** | The **Sleeper API** is free, read-only and needs no auth, so it's the best way to sync user leagues. The **Yahoo Fantasy API** requires an application and approval. The **ESPN** fantasy API is unofficial. nflverse also ships `load_ff_opportunity`, `load_ff_rankings` and `load_ff_playerids`. |
| **Can it extend to European football (soccer)?** | **Yes, but the free, commercially usable data is weaker than nflverse.** There is no current, open, event-level soccer dataset licensed for commercial use. A workable stack is **football-data.co.uk** (results plus closing odds since 1993, CSV), **API-Football** (free 100 req/day, then $19–39/mo), the **FPL API** (fantasy), and **ClubElo**. **StatsBomb Open Data is NON-COMMERCIAL and cannot be redistributed.** You can use it to build demos, but not a monetised public product. |
| **Biggest risks** | (1) Terms of service. Scraping sites like PFR, FBref, Understat and Transfermarkt is a legal and stability risk. (2) **Gambling law.** US betting is legal in 39 states plus DC (31 with online betting), and pick'em DFS is under active crackdown. **India's Online Gaming Act 2025 bans real-money gaming and its promotion**, so don't run sportsbook or DFS affiliate monetisation aimed at Indian users. (3) **Spurious "patterns".** Trend-mining invites data-dredging, so the agent must report sample sizes and significance. |

**Recommendation:** build the NFL version on **nflverse → Parquet → DuckDB**, with an LLM agent that has SQL and "pattern/similarity" tools, plus **Sleeper** for fantasy leagues and **The Odds API** for live lines. That combination costs $0–$59/mo for an MVP. Later, port the same architecture to soccer using football-data.co.uk + API-Football + FPL.

---

## 2. Licensing basics

- **Raw sports facts** (scores, who caught a pass) are generally **not copyrightable in the US** (*NBA v. Motorola*, 2d Cir. 1997). Fantasy operators' right to use player names and stats was upheld in *C.B.C. Distribution v. MLB Advanced Media* (8th Cir. 2007).
- **What actually binds you is contracts and terms of service.** These are the API terms, site ToS and dataset user agreements. Most "you can't do that" restrictions come from these, not from copyright.
- **In the EU and UK there is also a *sui generis* database right** protecting substantial investment in *obtaining* data. Fixture lists were held **not** copyright-protected in *Football Dataco v Yahoo* (CJEU C-604/10, 2012), but database right and contracts still apply. This is one reason European data vendors are protective.
- **"Official data"** for betting comes from leagues licensing exclusive feeds: NFL → Genius Sports, FIFA → Stats Perform (Opta), plus various leagues → Sportradar. Sportsbooks in some US states must use official data for in-play settlement. **A stats and insights site does *not* need official data.**
- **Practical rule:** prefer sources with an explicit open license (CC-BY, CC0) or a paid API whose plan explicitly allows display in a public or commercial app. Treat scraping as prototype-only.

---

## 3. American football (NFL + college) data sources

### 3.1 Free / open

| Source | What you get | Access | License / terms | Verdict |
|---|---|---|---|---|
| **nflverse** (`nflreadpy` Py, `nflreadr` R, `nflfastR`) | Play-by-play **1999–present** (≈370+ columns: EPA, WPA, win prob, CPOE from 2006, `spread_line`, `total_line`, `vegas_wp`, air yards, personnel); player & team stats; schedules + results + betting lines; rosters (weekly), snap counts, depth charts, injuries, officials, participation; **Next Gen Stats** weekly aggregates; **FTN charting** (play-action, blitz, etc.); draft picks, combine, contracts, trades; fantasy IDs/rankings/opportunity (expected fantasy points) | GitHub releases (Parquet/CSV), Python/R loaders; updated nightly in season | Packages MIT. **Data mostly CC-BY 4.0; FTN data CC-BY-SA 4.0.** | ⭐ **Core source. Commercial use OK with attribution.** If you redistribute FTN-derived data it must stay share-alike. |
| **NFL Big Data Bowl** (Kaggle, 2019–2026) | Raw **player tracking** (x, y, speed, accel at 10 Hz) for selected weeks/play types, plus plays and players tables | Kaggle download | Kaggle competition rules. Competition data is normally limited to **competition, non-commercial and academic use**. Check each year's "Data Access and Use" clause. | Great for research and demo features (route charts, separation). **Not for a commercial product.** |
| **ESPN "hidden" API** (`site.api.espn.com/apis/site/v2/sports/football/nfl/...`) | Live scoreboard, game summaries, box scores, news, standings, team/athlete info; also college football | Unauthenticated JSON | **Undocumented, unofficial.** No license grant; can change or break without notice. | OK for live scores in a prototype. Don't make it a hard dependency. |
| **CollegeFootballData.com (CFBD)** | College football PBP, drives, recruiting, betting lines, advanced stats, ratings | REST API v2 + GraphQL | Free 1,000 calls/mo. Patreon $1/$5/$10 gives 5k/30k/75k calls. Its ToS **prohibits redistributing raw data as a bulk/substitute feed**. | ⭐ Best route if you add NCAA. Display derived insights, not raw dumps. |
| **Pro-Football-Reference** (Sports Reference) | Deep historical box scores and splits back to 1920 | Website only | ToS restricts automated scraping and reuse. Bots are rate-limited and temporarily banned. | ❌ Don't build on it. nflverse covers almost everything you'd want. |

### 3.2 Paid / commercial APIs

| Provider | Positioning | Price signal | Notes |
|---|---|---|---|
| **SportsDataIO** | US sports, strong on fantasy projections, DFS salaries, odds, injuries, news | Free trial (all endpoints, **scrambled data**). Discovery Lab ~$99–149/mo with real but **next-day-delayed** data. Real-time/production is quote-based (~$500–1,000+/mo). | Most practical paid upgrade for a startup. Clear commercial licensing tiers. |
| **Sportradar** | Largest B2B sports data company; NFL stats, live PBP, odds, images | Enterprise only, est. **$10k+/mo**. Free **trial keys** on its developer marketplace (real data, low rate limits). | Use the trial to prototype. Production cost only makes sense once you have revenue. |
| **Genius Sports** | **NFL's exclusive official data distributor** (real-time PBP + Next Gen Stats) to media & sportsbooks, extended **through 2029 season** | Enterprise | Only relevant if you become a sportsbook or a large media partner. |
| **MySportsFeeds** | NFL/NBA/MLB/NHL feeds | **Free for non-commercial use**; commercial paid tiers | Good for hobby → small commercial transition. |
| **API-Sports (American Football API)**, **Goalserve**, **BALLDONTLIE** (multi-sport, $9.99–159.99/mo) | Budget aggregators | $0–$40/mo typical | Cheap, but data depth and accuracy vary; test before relying on them. |
| **PFF**, **FTN**, **Next Gen Stats (full)** | Premium grades, charting, tracking | Subscription / enterprise | nflverse already exposes the open parts (FTN charting, NGS aggregates). |

### 3.3 Fantasy platform APIs (league sync)

| Platform | Access | Notes |
|---|---|---|
| **Sleeper** | `api.sleeper.app/v1/...`, **no auth, read-only, free**. Stay under ~1,000 req/min. | Users, leagues, rosters, matchups, transactions, drafts, traded picks, trending adds/drops, full player DB. ⭐ **Best for "connect your league" features.** |
| **Yahoo Fantasy Sports API** | OAuth. **Access now requires an application and Yahoo approval** plus agreeing to the API Access & Use Agreement. Read-only by default. | Large user base; plan for review lead time. |
| **ESPN Fantasy** | Unofficial endpoints. Private leagues need the user's `espn_s2`/`SWID` cookies. | Popular but fragile. Handle cookies carefully (they're credentials). |

### 3.4 Odds APIs

| Provider | Price | Coverage |
|---|---|---|
| **The Odds API** | Free 500 credits/mo; $30 (20k), $59 (100k), $119 (5M), $249 (15M). 1 credit = 1 market × 1 region per call. | NFL, NCAAF + soccer leagues; US (DraftKings, FanDuel, BetMGM, Caesars…), UK, EU (incl. **Pinnacle**), AU books; player props via event-odds endpoint; **historical odds** (featured markets from mid-2020, other markets from May 2023) on paid plans. ⭐ |
| **SportsGameOdds**, **OddsPapi** | Free tiers + paid | Alternatives with broad book/prop coverage; compare if props volume is high. |
| **nflverse schedules** | Free | Closing spread/total/moneyline per game for historical ATS/O-U analysis, so you don't need to pay for history just to backtest game lines. |

### 3.5 Recommended NFL stack

```
nflreadpy (nightly) ──► Parquet ──► DuckDB  ◄── LLM agent (SQL + pattern tools)
Sleeper API (on demand, per user league) ─┘          │
The Odds API (polled pre-game, cached) ───────────────┘
ESPN scoreboard (live scores, best-effort)
```
- **Cost:** $0 to start; $30–59/mo once you show live odds and props.
- **Attribution:** "Data: nflverse (CC-BY 4.0), FTN Data via nflverse (CC-BY-SA 4.0)" in the footer and in API responses.

---

## 4. Mapping IPL-style agent features to the NFL

| IPL feature | NFL equivalent | Data needed |
|---|---|---|
| "Has this happened before?" / duplicate scorecards | "Has a team ever come back from 21+ down in the 4th quarter on the road in the playoffs?", "games with the exact same final score", "QB with 400 yds + 0 TD + a win" | PBP + schedules |
| Patterns / streaks | Team ATS / over-under streaks, player 100-yd streaks, 4th-down aggressiveness by coach, scoring by quarter | Schedules (lines), PBP |
| Matchups (batter vs bowler) | WR vs CB / coverage type (FTN), RB vs defensive front, QB vs blitz | FTN charting, participation, PBP |
| Situational splits | 3rd & long, red zone, 2-minute drill, score/time/WP buckets, weather/dome, rest days, primetime | PBP (`down`, `ydstogo`, `yardline_100`, `wp`, `roof`, `temp`, `wind`) |
| Similar games / players | Embed game-state or season stat vectors to find nearest neighbours ("most similar rookie seasons to X") | Player stats, NGS |
| Venue analysis | Stadium/surface/roof splits, altitude (Denver), travel/time zones | Schedules (`stadium`, `roof`, `surface`) |

**Agent tool design (works for any sport):**
1. `describe_schema()` gives curated table and column docs. nflverse has field descriptions you can load into the prompt.
2. `run_sql(query)` is read-only DuckDB with row and time limits.
3. `find_precedents(conditions)` returns all matching historical cases plus the count.
4. `trend_check(filter, outcome)` returns the hit rate **with sample size, a confidence interval, and the base rate**, and flags results as "likely noise" when n is small. This is your credibility moat, since most betting "trends" are data-dredged.
5. `similar(entity, k)` does nearest-neighbour search over stat vectors.
6. `live_odds(game)` and `league(user)` handle external calls, cached.

---

## 5. Helping bettors and fantasy players (responsibly)

### 5.1 Betting-oriented features
- **ATS / totals history** for any filter (e.g., "home underdogs of 3+ off a bye since 2010"), with sample size and ROI at −110.
- **Line context:** current line vs model/market history, line movement (polling The Odds API), **best price across books** (line shopping), and a **closing-line-value (CLV) tracker** for users' logged bets. CLV is the honest measure of skill.
- **Player-prop hit rates:** last N games vs today's line, split by opponent defence, home/away, game script (spread), weather, snap share. Pull lines from the Odds API and history from nflverse.
- **Injury impact:** on/off splits (team EPA with and without player X), depth-chart replacement.
- **Explainable models:** simple, transparent projections such as an EPA-based team rating or a usage-based prop projection, with backtests shown. Never "locks".

### 5.2 Fantasy features
- **League sync** via Sleeper (and Yahoo once approved): roster-aware start/sit, waiver suggestions (Sleeper trending + nflverse opportunity), trade analyzer (rest-of-season value), playoff schedule strength.
- **Usage metrics:** target share, air-yards share, WOPR, red-zone touches, route participation (participation/FTN), expected fantasy points vs actual from `ffopportunity` for buy-low/sell-high calls.
- **Matchup:** fantasy points allowed by position (DvP), coverage-scheme tendencies.
- **DFS:** lineup optimiser and ownership leverage, only if you have salary data (SportsDataIO provides DFS salaries).

### 5.3 Guardrails & compliance (important)
- **Positioning:** stay an **information and analytics tool**. Don't take bets, hold funds or run paid contests. That keeps you out of gaming licensing.
- **United States:** sports betting is legal in **39 states + DC** (31 + DC online; 8 retail-only; 11 none, including CA and TX). **Sportsbook affiliate links require affiliate or vendor registration in many states** and age gating (21+ in most) plus geo-targeting. Pick'em DFS (PrizePicks, Underdog) has faced cease-and-desist orders in Florida, Arkansas and elsewhere, so be careful promoting them.
- **India (likely relevant given your IPL site):** the **Promotion and Regulation of Online Gaming Act, 2025** bans all real-money online games, *including fantasy sports*, and their advertising/promotion. Dream11 shut paid contests. **Don't monetise Indian traffic with betting or DFS affiliates or ads.** Free-to-play fantasy tools and pure stats are the safe zone. Get local legal advice before any monetisation.
- **UK/EU:** gambling advertising is regulated (UKGC, country-specific rules). Same principle: affiliates need compliance.
- **Product hygiene:** a responsible-gambling notice and helpline links (e.g., 1-800-GAMBLER in the US, BeGambleAware in the UK). Show **sample size and uncertainty** on every "trend". Never claim guaranteed wins. Add disclaimers that projections are not advice.

---

## 6. European football (soccer)

### 6.1 Free / open

| Source | What you get | License / terms | Commercial? |
|---|---|---|---|
| **football-data.co.uk** | Results (FT/HT), shots, corners, cards, referee + **closing odds from many books (B365, Pinnacle, max/avg…)** for **20+ European leagues back to 1993**; CSV, updated weekly | Free download, no API key; terms not explicit, attribution expected | ⚠️ Widely used; credit them and ask the owner before heavy commercial use. ⭐ Best free betting-history source. |
| **openfootball** (GitHub) | Fixtures and results for many leagues in plain text/JSON | **CC0 / public domain** | ✅ Yes |
| **football-data.org** API | Fixtures, results, tables, scorers; **free tier: 12 competitions** (PL, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira, Championship, UCL, Brasileirão, WC, Euros), 10 calls/min, delayed scores, no player match stats | Free + paid (€12–199/mo) | ✅ per plan |
| **StatsBomb Open Data** | Very rich event data (+ 360 freeze-frames for selected matches): Messi's career, World Cups, Euros, women's competitions, some full league seasons | **StatsBomb Public Data User Agreement:** research and analysis only. **May not "distribute, reproduce, sell or in any way provide the data to any third party" or "commercially exploit the data or any analysis derived from it."** Must show the StatsBomb logo on published analysis. | ❌ **Non-commercial only.** Fine for a free research or demo mode; don't monetise it. |
| **Wyscout public dataset** (Pappalardo et al., *Scientific Data* 2019) | ~1,941 matches, 3.2M events: 2017/18 top-5 leagues + WC 2018 + Euro 2016 | **CC BY 4.0** | ✅ Yes (with attribution), but static and old |
| **SkillCorner Open Data**, **Metrica sample data**, **PFF FC World Cup 2022** | Broadcast tracking + events (A-League matches; 2 Metrica games; all 64 WC 2022 matches from PFF) | Repo-specific licenses, mostly research-oriented | ⚠️ Check each; good for tracking-data demos |
| **Fantasy Premier League API** (`fantasy.premierleague.com/api/bootstrap-static/` etc.) | All players, prices, ownership, gameweek points, fixtures difficulty, user teams/leagues | Unofficial, no auth; PL owns the data/ToS | ⚠️ Widely used by FPL tools; don't resell raw data |
| **ClubElo** (`api.clubelo.com`) | Daily Elo ratings for European clubs (long history) | Free CSV API | ✅ Generally OK with credit; great for strength-of-schedule and model baselines |
| **FBref** | Basic stats only. **Advanced Opta stats (xG, progressive passes, etc.) were removed on 20 Jan 2026** after Stats Perform terminated access. | Sports Reference ToS (anti-scraping) | ❌ Much weaker now and not a reliable source |
| **Understat**, **Transfermarkt** | xG/shots (top-6 leagues); market values, transfers, injuries | Scrape-only, no license | ❌ Prototype only; ToS / database-right risk |

### 6.2 Paid soccer APIs

| Provider | Price signal | Notes |
|---|---|---|
| **API-Football (API-Sports)** | **Free 100 req/day** (all ~1,200 leagues, all endpoints incl. odds, lineups, player stats); Pro $19, Ultra $29, Mega $39/mo | ⭐ Best value for an MVP |
| **Sportmonks** | €29 (5 leagues) / €99 (30) / €249 (120)/mo; 14-day trial; small free tier | Includes **xG, pressure index, predictions**; odds are an add-on |
| **Stats Perform (Opta)** | Enterprise | Gold-standard event data; **FIFA's exclusive official betting data distributor (2026–2029)** incl. World Cup 2026 |
| **Sportradar** | Enterprise ($10k+/mo) | Official data for UEFA and many leagues; trial keys available |
| **StatsBomb (Hudl) / Wyscout (Hudl)** | Enterprise | Commercial event/360 data |

### 6.3 Verdict on European football
- **Feasible, and the betting angle is actually stronger in soccer.** Global betting volume is huge, and football-data.co.uk gives 30 years of free closing odds for backtesting (home/draw/away, O/U 2.5, Asian handicap).
- **The analytics depth is weaker for free.** There's no nflverse-equivalent with current, licensed, event-level data and xG. For xG and player events in a commercial product you'll need **API-Football or Sportmonks** (cheap) or Opta/StatsBomb (expensive).
- **Fantasy:** the **FPL API** is the obvious hook (11M+ managers), with features like transfer planner, captaincy, and fixture difficulty using ClubElo.
- **Suggested soccer stack:** football-data.co.uk (history + odds) + openfootball (fixtures) + API-Football (live, lineups, player stats) + ClubElo (ratings) + FPL API (fantasy) + The Odds API (live odds). StatsBomb Open Data stays in a **non-commercial "research mode"** only.

---

## 7. Side-by-side summary

| Dimension | NFL | European football |
|---|---|---|
| Best free, commercially usable historical data | **nflverse (CC-BY), excellent** | football-data.co.uk + openfootball + Wyscout 2017/18 (CC BY), **moderate** |
| Advanced metrics free | EPA, WP, CPOE, NGS aggregates, FTN charting | xG mostly paid/scraped (FBref lost Opta in 2026) |
| Tracking data | Big Data Bowl (non-commercial) | SkillCorner/Metrica/PFF samples (research) |
| Cheap live API | SportsDataIO (~$99+), ESPN unofficial | API-Football ($0–39), football-data.org (€0–49) |
| Fantasy API | Sleeper (free), Yahoo (approval), ESPN (unofficial) | FPL (free, unofficial) |
| Odds | The Odds API; nflverse closing lines | The Odds API; football-data.co.uk closing odds |
| Official betting data owner | Genius Sports (through 2029) | Stats Perform (FIFA), Sportradar/Genius (various leagues) |
| Season shape | 18 weeks + playoffs, 272 games; weekly cadence suits agents and content | ~380 games/league/season, many leagues; daily cadence |

---

## 8. Suggested roadmap

1. **Week 1–2: NFL data layer.** Nightly job: `nflreadpy` → Parquet → DuckDB (pbp 1999–now, schedules, player stats, rosters, injuries, FTN, NGS, ff_opportunity). Write curated schema docs for the agent.
2. **Week 3–4: Agent v1.** Port the IPL agent tools: SQL, precedents/"has this happened", streaks, splits, similarity. Add `trend_check` with sample size and confidence intervals.
3. **Week 5–6: Fantasy.** Sleeper league connect, start/sit, waivers, trade analyzer. Apply for Yahoo API access early (it takes time).
4. **Week 7–8: Betting insights.** Add The Odds API ($30–59 plan): line shopping, props vs history, ATS/O-U explorer, CLV tracker. Add responsible-gambling UX, age and geo notices, and no Indian betting monetisation.
5. **Later: Soccer.** Reuse the architecture with football-data.co.uk + API-Football + FPL + ClubElo. Use StatsBomb in research-only mode.
6. **Later: College football** via CFBD ($5–10/mo Patreon tier).

---

## 9. Sources

**NFL / American football**
- nflreadpy (data functions, license: CC-BY 4.0, FTN CC-BY-SA 4.0): https://github.com/nflverse/nflreadpy
- nfl_data_py (deprecated in favour of nflreadpy): https://github.com/nflverse/nfl_data_py
- nflfastR README (PBP since 1999, EPA/WP/CPOE): https://cran.r-project.org/web/packages/nflfastR/readme/README.html
- NFL Big Data Bowl: https://operations.nfl.com/gameday/analytics/big-data-bowl , https://operations.nfl.com/updates/football-ops/nfl-announces-eighth-annual-big-data-bowl-powered-by-aws
- ESPN hidden API guide: https://zuplo.com/learning-center/espn-hidden-api-guide
- CollegeFootballData API v2 tiers: https://blog.collegefootballdata.com/api-v2-is-now-in-general-availability/ ; terms: https://collegefootballdata.com/terms
- SportsDataIO: https://sportsdata.io/developers/getting-started , https://sportsapis.dev/apis/sportsdata-io
- Sportradar: https://sportsapis.dev/apis/sportradar , https://developer.sportradar.com/getting-started/docs/your-account
- Genius Sports NFL extension: https://www.legalsportsreport.com/123307/genius-extends-nfl-betting-data-deal-at-least-five-years/ , https://nfl.com/news/nfl-extends-strategic-partnership-with-genius-sports
- MySportsFeeds / free API overview: https://dev.to/checklive/navigating-the-challenges-of-free-sports-data-apis-football-basketball-and-baseball-insights-3gok
- Best NFL APIs 2026 overview: https://highlightly.net/blogs/best-nfl-apis-in-2026
- Sleeper API: https://zuplo.com/blog/2025/05/12/sleeper-api
- Yahoo Fantasy API access: https://sports.yahoo.com/developer/access/
- The Odds API: https://the-odds-api.com/ , https://the-odds-api.com/sports-odds-data/nfl-odds.html

**Soccer**
- StatsBomb open data + User Agreement (LICENSE.pdf): https://github.com/statsbomb/open-data
- Wyscout public dataset (CC BY 4.0): https://pmc.ncbi.nlm.nih.gov/articles/PMC6817871 , https://figshare.com/collections/Soccer_match_event_dataset/4415000
- FBref loses Opta advanced stats (Jan 2026): https://amp.awfulannouncing.com/soccer/sports-reference-pulls-advanced-data-agreement-violation-dispute.html , https://www.theixsports.com/the-ix-soccer/fbrefs-loss-advanced-stats-womens-soccer-data-accessibility/
- football-data.org tiers: https://www.thestatsapi.com/blog/football-data-org-free-tier-limits-2026
- API-Football: https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide , https://highlightly.net/blogs/best-football-apis-in-2026
- Sportmonks: https://www.sportmonks.com/football-api/alternatives/sportradar/
- football-data.co.uk (via soccerdata docs): https://soccerdata.readthedocs.io/en/stable/datasources/MatchHistory.html
- ClubElo: https://soccerdata.readthedocs.io/en/stable/datasources/ClubElo.html
- FPL API docs (community): https://fpl-api-docs.notion.site/Fantasy-Premier-League-API-Documentation-1be2fd947c77804d8e90dd3f22f2ea68
- SkillCorner open data: https://docsearch.algolia.com/mcp/docs/repo/skillcorner/opendata ; PFF FC WC2022: https://www.blog.fc.pff.com/blog/enhanced-2022-world-cup-dataset
- Stats Perform as FIFA official betting data distributor: https://inside.fifa.com/media-releases/stats-perform-official-worldwide-betting-data-streaming-rights-distributor-world-cup

**Regulation**
- US sports betting legal states 2026: https://track360.io/blog/us-sports-betting-legal-states-tracker-2026
- DFS pick'em crackdowns: https://www.legalsportsreport.com/167182/dfs-fantasy-sports-operators-to-pull-out-of-florida-under-regulatory-pressure/ , https://www.legalsportsreport.com/167246/prizepicks-underdog-ordered-to-leave-arkansas-for-offering-player-props/
- India Online Gaming Act 2025: https://www.dhakatribune.com/sport/cricket/389651/india-bans-vast-online-gambling-industry , https://www.majmudarindia.com/wp-content/uploads/Promotion-and-Regulation-of-Online-Gaming-Act.pdf
