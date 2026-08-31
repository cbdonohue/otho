# Otho remaining-work plan

Audit of `/workspace` on `cursor/otho-modular-monolith-d7b9` (content HEAD `e4a3685`). PR #1 is merged to `main` (`b1e82f8`). This is an execution plan, not a vibe roadmap.

## 1. Current state

v0.1 is a **working modular monolith skeleton**. The architecture is real: Sleeper JSON is confined to `backend/app/providers/sleeper/mapper.py`, plugins consume `backend/app/domain/*` via `AnalysisContext`, and the UI is decision-shaped. What is **not** real yet is the intelligence those plugins claim — almost every number traces to `HeuristicProjectionProvider` (`search_rank` × position base), not to scoring settings, weekly stats, or an external projection feed.

### Real (ships and runs)

| Area | Where | What is actually true |
|---|---|---|
| FastAPI gateway | `backend/app/main.py`, `backend/app/api/*` | Health, leagues CRUD/sync/demo, plugin list/analyze, dashboard, Ask Otho, player search, WS endpoint |
| Domain models | `backend/app/domain/` | `Player`, `Roster`, `League`, `Matchup`, `Transaction`, `Projection`, `PlayerNews`, `Injury` |
| Sleeper provider | `client.py` → `mapper.py` → `provider.py` | League, users, rosters, matchups, transactions, NFL state, player catalog, trending. Client rate-limit `MIN_INTERVAL_S = 0.08` (~12/s) |
| Persist + read path | `LeagueService`, `PlayerService`, `SyncService` | Normalized league state in SQLite/Postgres. Plugins do not call Sleeper |
| Plugin SDK | `backend/app/plugins/sdk/` | `AnalysisPlugin` / `BackgroundPlugin`, `tools()`, widgets helpers, `otho.plugins` entry points in `pyproject.toml` + `PluginManager` |
| Event bus | `backend/app/core/events.py` | In-process fan-out. Constants exist for all 10 event types. `league.synced`, `roster.updated`, `matchup.updated`, `transaction.created`, `player.injury` are **published** from sync |
| Scheduler | `backend/app/core/scheduler.py` | asyncio loops with the documented intervals (rosters 90s, matchups 20/120/600, etc.) |
| Cache | `backend/app/core/cache.py` | Redis when `REDIS_URL` set, else in-memory. Locks exist |
| Dashboard | `frontend/src/pages/HomePage.tsx`, `backend/app/api/dashboard.py` | Hero YOU vs opponent, ACTIONS / OPPORTUNITIES / WATCH, starter bars, ASK OTHO dock |
| Ask Otho | `backend/app/services/ask.py` | Keyword fallback is tested. LLM tool-calling path exists (httpx → OpenAI-compatible) |
| Demo | `backend/app/services/demo.py` | 2-team local league, no network |
| Tests | `backend/tests/` | **14 pytest tests**, no network. Frontend `tsc` + Vite build |
| Docker | `docker-compose.yml` | Postgres 16 + Redis 7 + API + nginx frontend |

### Stubby / half-wired (looks like the vision, does not fulfill it)

**Projections** — `backend/app/providers/projections/heuristic.py`. Position base × Sleeper `search_rank` × injury multiplier. Floor/ceiling are `×0.55` / `×1.55`. Persisted to `projections` on first miss (`ProjectionService`). League `scoring_settings` (PPR, TE premium, 6-pt passing TDs) are stored on `League` and **never used**.

**News** — `StubNewsProvider`. Seeded from `Player.injury_status` during player sync. Lives in process memory. `player_news` table is never written.

**Stats** — `StubStatsProvider.weekly_stats` returns `{stats: {}}`. `player_stats` table is never written. Provider is never injected into `AnalysisContext`.

**PlayerValue** — `backend/app/domain/value.py` exists. Nothing computes or stores it.

**OpenAI Ask Otho** — `_llm_ask` is untested. No streaming, no conversation memory, no league briefing in the system prompt beyond ids. Default path is keyword regex → up to 4 plugins → concatenate summaries.

**WebSocket** — `WS /api/live/{league_id}` in `backend/app/api/websocket.py` broadcasts events. **Frontend never connects.** Home always shows a red “LIVE” dot and the label “LIVE MATCHUP”.

**Redis** — used only as a key/value cache + lock. Comment in `events.py` says it “optionally mirrors to Redis pub/sub”; it does not. No Streams, no job queue, no pub/sub. Event bus is in-process only (dies with the API process; does not cross replicas).

**Snapshots** — `SyncService.sync_league` inserts a full roster JSON blob into `snapshots` **every league poll**. Scheduler `_rosters` calls `_leagues` every 90s, so this is unbounded write amplification. **Nothing ever reads `snapshots`.**

**ORM tables that exist and are unused:** `roster_players`, `matchup_players`, `player_news`, `player_stats`. `plugin_results` is written on analyze and never read. `init_db()` is `Base.metadata.create_all` — Alembic `0001_initial` exists but is not run on boot. Alembic env rewrites URLs to `psycopg2`, which is **not** in `pyproject.toml` dependencies.

**Trending is broken across requests.** `sync_trending` sets `PlayerService._trending` on the sync instance and also `cache.set("trending", ...)`. Every plugin request constructs a **new** `PlayerService` (`context_factory.py`) with `_trending = []`. Cache is never read. Waiver “trending” multiplier is therefore always 0 in the live app.

**Waiver wire crash.** `positional_need` in `waiver_wire/analyzer.py` line 29 references undefined `gap`. Tests pass because the fake roster is stacked (`top >= typical`). Any real roster with a below-typical position throws `NameError` — and that plugin is in `HOME_PLUGINS`, so **the home dashboard can 500 a column** (the dashboard swallows plugin exceptions into `plugin_payloads[].error`, so the page still loads, but waivers are empty).

**Scheduler “live” detection** is `any(matchup.home.points > 0)` — true for the rest of the week after the first player scores. No NFL game clock, no `game.started` / `game.completed` / `week.changed` publishers. `SleeperClient.traded_picks` is unused. Matchup `projected_points` is mapped from Sleeper `custom_points` (commissioner override), not a projection.

**Background plugins** (`league_activity`, `injury_watch`) keep alerts in `self._alerts` / `self._events` on the process. Restart wipes them. They do not write DB or push dashboard invalidation.

**Frontend week state** is used on Home (`useDashboard(..., week)`) but **not passed** to `PluginPage` or Ask Otho. Nav label “League Pulse” is the home decision board, not `league_activity`. `/players` is roster health, not a player explorer. `api.ts` has `API = ""` and Vite proxies `/api` + `/health` but **not** `/api/live` as a first-class WS client.

### Missing vs original vision

- Auth, users, “this is my roster” (you pick a roster in a `<select>`; no Sleeper user login)
- Multi-league identity, dynasty vs redraft product split
- FAAB remaining / bid recommendations (only `waiver_budget_used` stored)
- Actual remaining schedule for playoff sims (current sim **randomly pairs** teams each remaining week)
- Historical intelligence (luck, manager profiles, waiver efficiency) — blocked on unread snapshots
- Real Projection / News / Stats providers
- Betting lines, weather
- SSE
- CI (no `.github/workflows`)
- Plugin versioning, widget JSON schema, external plugin example package
- Next.js was in the original sketch; **Vite/React is the right call — do not rewrite**

Builtin plugins: 9 exist as real Python, none are “empty stubs,” all are **thin and projection-heuristic-bound**. See [plugin backlog](#6-plugin-backlog).

## 2. North star

Otho is an **analysis operating system**. Sleeper (and later anyone else) is a state pipe. Plugins answer decisions. The home screen and Ask Otho exist to answer **what should I be doing right now?** — start/sit, claims, trades, injuries, opponent behavior — not to prettier-print box scores. If a feature does not change a decision or the agent’s ability to explain one, it is not the next build.

## 3. Principles / constraints

1. **Plugins never see Sleeper JSON.** Mapping only in `providers/sleeper/mapper.py`. New sources implement `FantasyDataProvider` / `ProjectionProvider` / `NewsProvider` / `StatsProvider` in `providers/base.py`.
2. **Widget contract.** Plugins return the typed dicts in `sdk/widgets.py`; `WidgetView.tsx` renders. No React inside plugins. Adding a widget type is a versioned SDK change, both sides.
3. **Three plugin kinds stay.** Analysis (`analyze`), background (`subscriptions` + `handle_event`), agent tools (`tools()` + `call_tool`). Redis Streams later must not change that API.
4. **Ask Otho is the primary UI.** Dashboard columns are the always-on briefing; the dock is where novel questions go. The model may not invent league facts.
5. **Adaptive sync, plugins read the DB.** Stay under ~1000 Sleeper calls/min (already conservative). Cache the player catalog. Don’t let plugins scrape Sleeper.
6. **Snapshots are the memory.** Point-in-time roster/matchup/league state is how manager psychology, luck, and “since yesterday” work. Write them deliberately; query them.
7. **SQLite + in-memory cache stay valid for local demo.** Postgres + Redis are first-class in Docker, not required to click LOAD DEMO.

## 4. Workstreams and sequenced milestones

Phases: **Foundation hardening → Intelligence depth → Differentiation → Polish/scale.**

Dependencies: projections unlock plugin quality; snapshots + transaction history unlock historical plugins; WS + scheduler quality unlock “live”; Ask Otho quality is gated on tool quality, not prompt cleverness.

### Stream A — Core platform

#### A1. Foundation: sync quality and storage honesty

**Goal:** League state in the DB is complete, cheap to poll, and historically queryable.

**Tasks:**

- Stop `_rosters` from calling full `sync_league` (`scheduler.py`). Split settings (6h) vs roster diff (90s) vs snapshot-on-change only.
- Snapshot policy: write `kind=roster` only when player set/starters change; add `kind=matchup` on score change; cap retention (e.g. keep weekly close + last 48h of diffs). Add `LeagueService.get_snapshots(league_id, week=, since=)`.
- Populate `roster_players` and `matchup_players` on upsert (tables already exist in `core/models.py`) so plugins can query slots without parsing JSON blobs.
- Player catalog: upsert-by-id instead of `DELETE FROM players` (`PlayerService.upsert_players`).
- Persist trending from cache in `PlayerService.trending()` (read `cache.get("trending")`).
- Persist news/injuries to `player_news` when seeded; `NewsService` reads DB first.
- Publish `week.changed` when `League.week` increments; publish `projection.updated` when projection rows change. Leave `game.started` / `game.completed` until an NFL schedule source exists (A2/B2).
- Fix matchup live interval: “points > 0” is not live. Until schedule exists, use weekday + Sleeper `nfl_state` (`season_type`, `display_week`) as a weaker signal; document it.
- Use distributed lock around per-league sync, not only player catalog.

**Deps:** none.

**Done:** A 12-team sync survives 24h without `snapshots` exploding; restarting the API does not lose trending/news; a test asserts snapshot count does not grow when rosters are unchanged.

**Risk:** SQLite + 90s writes already showed lock issues (see `e4a3685`). Prefer WAL + shorter transactions; don’t block dashboard on sync.

#### A2. Live transport

**Goal:** The UI moves when the league moves.

**Tasks:**

- Frontend `WebSocket` to `/api/live/{league_id}` (Vite already `ws: true` on `/api`; nginx already upgrades).
- On `matchup.updated` / `roster.updated` / `transaction.created` / `player.injury`, refetch dashboard (debounce 2–5s).
- Replace always-on LIVE chrome with states: PRE / LIVE / FINAL based on matchup points + clock when available.
- Optional SSE `GET /api/live/{league_id}/sse` later for environments that hate WS; not blocking.

**Deps:** A1 event quality.

**Done:** Demo or synced league: change is visible on Home without refresh.

**Risk:** Dashboard currently runs 6 plugins per GET with no cache — live refetch will melt. Add plugin-result cache (TTL 30–60s, keyed by `league,roster,week,plugin`) **in the same milestone**.

#### A3. Jobs / Redis Streams (scale, not demo)

**Goal:** Scheduler and events survive multiple API workers.

**Tasks:**

- Extract poll loops from the FastAPI process (or run them on worker 0 with a Redis lock).
- Event bus Redis Streams transport behind the existing `subscribe` / `publish` API.
- Plugin cache + latest league state in Redis as designed.

**Deps:** A1, Docker Redis already in compose.

**Done:** Two uvicorn workers, one scheduler, events still reach WS clients.

**Risk:** Easy to over-engineer. Skip until a second user or a second process is real.

### Stream B — Provider layer

#### B1. Scoring-aware projections (highest leverage in the repo)

**Goal:** Every plugin’s numbers mean “points in *this* league.”

**Tasks:**

- Add `StatsProvider` implementation that fills `player_stats` (Sleeper undocumented stats, or NFL.com/other — isolate in `providers/stats/`).
- Change `HeuristicProjectionProvider` (or replace) to: `points = f(usage, opponent, injury, league.scoring_settings)`. Even a transparent formula beats rank × 18.4.
- Thread `scoring_settings` into `ProjectionService.projections(...)`.
- Keep `source` on `Projection` so FantasyPros can coexist (`otho.heuristic` vs `fantasypros` vs `otho.ml`).
- Stop mapping `custom_points` → `projected_points` in `mapper.py`; store commissioner overrides separately.

**Deps:** none (can start immediately).

**Done:** PPR vs standard demo/test league produces different WR projections; OUT still 0; plugins unchanged.

**Risk:** Sleeper stats endpoint is unofficial. Wrap behind `StatsProvider` so it can be swapped.

#### B2. Real projection + news providers

**Goal:** External feeds without plugin rewrites.

**Tasks:**

- `providers/projections/fantasypros.py` (or similar) implementing `ProjectionProvider`. Config: API key in `.env.example`.
- `providers/news/` HTTP adapter: injury reports + headlines → `PlayerNews` / `Injury`. Publish `player.news` / `player.injury`.
- Wire chosen providers in `main.py` lifespan instead of hard-coding `StubNewsProvider` + `HeuristicProjectionProvider`.
- Fallback chain: paid feed → heuristic. Plugins must not care.

**Deps:** B1 interface cleanup.

**Done:** Flipping env vars changes projection `source` in plugin output; removing the key still runs.

**Risk:** Licensing/ToS. Ship heuristic+stats first so the product is usable without keys.

#### B3. Later feeds

NFL schedule/game times (unlocks true live polling + “before 1 PM”), weather, betting lines. Do **not** start until B1 is in and two in-season weekends have been survived.

### Stream C — Plugin SDK & widget contract

#### C1. Contract tests and versioning

**Goal:** A third-party `otho.plugins` package can be written from docs + tests, not from reading builtins.

**Tasks:**

- JSON Schema (or Pydantic models) for each widget type; validate in `PluginManager.analyze` in dev.
- `AnalysisContext` gains `stats_service` (optional, default stub) without breaking existing plugins.
- Example external package in-repo (`examples/otho-plugin-hello` or a test entry point) proving `load_entry_points`.
- Pin SDK version on `PluginMetadata`; manager logs incompatibles.
- Fix unused import `grade_from_score` in waiver analyzer while touching SDK consumers.

**Deps:** none.

**Done:** `pytest` builds a dummy entry-point plugin; invalid widget fails loudly in tests.

**Risk:** Over-formalizing widgets before the UI needs new ones. Schema-lite is enough.

### Stream D — Builtin plugins

#### D1. Harden the nine that exist (do this before new plugins)

**Goal:** v0.1 plugins are trustworthy on a real 12-team league this week.

**Tasks by plugin:**

- **waiver_wire:** define `gap = typical[pos] - top`; FAAB remaining (`league.settings` waiver budget − `waiver_budget_used`); drop_candidates as a second ranking (worst bench vs best FA); read trending from cache; don’t scan 400 players then slice — filter by position need first.
- **lineup:** greedy is OK for v0.1.5; respect `is_out`; expose slot-level “you are starting an empty/OUT”; pass `week` from UI.
- **matchup:** condition on **remaining** players (subtract live `player_points` from projection); independent Gaussians are fine until correlation (QB/WR stacks) is a named plugin.
- **injury_watch:** suggest replacement from bench then waivers; persist events.
- **trade_finder:** cap combinatorial explosion; 2-for-1 search with value bands; use ROS/value when B1 exists, not only this week’s proj.
- **playoff_odds:** use **actual remaining matchup graph** from synced weeks (Sleeper matchups for weeks `current..playoff_start-1`). Random pairing is the #1 reason odds are fiction.
- **opponent_scout:** add “they will need X on waivers” from their IR/OUT + thin depth, not only letter grades.
- **league_activity:** add to Home `watch` (or a Pulse drawer). “Since yesterday” filter. Include `league_activity` in `HOME_PLUGINS` or a cheap path that doesn’t Monte Carlo.
- **roster_health:** grade **relative to league** (z-score vs other rosters), not absolute 18=A+.

**Deps:** A1 trending/cache, B1 if you want numbers to be believed. Can land bugfixes (gap, FAAB display, playoff schedule) before B1.

**Done:** Fresh 12-team Sleeper sync: Home columns populated, no plugin errors in `dashboard.plugins[].error`, playoff odds change if you swap remaining opponents. Tests for waiver `gap`, playoff remaining-schedule, trending-after-new-PlayerService.

**Risk:** Dashboard latency. Cache plugin results (A2).

#### D2. Intelligence-depth plugins (after D1 + snapshots)

Build in this order (each is a builtin following `plugin.py` / `models.py` / `analyzer.py` + `BUILTIN_MODULES` + `otho.plugins` entry point + one pytest + one nav or Home column hook):

1. `drop_candidates` (or fold into waiver_wire — prefer fold unless UI needs its own page)
2. `player_trends` (needs `player_stats`)
3. `news_impact` (needs real news)
4. `schedule_strength` / `power_rankings`
5. `floor_ceiling` + `boom_bust` (matchup already has p10/p90 — extract)
6. `trade_analyzer` as a proper 2-way rest-of-season grader (keep `trade_finder` as search)
7. `buy_low_sell_high` (needs rest-of-season vs last-3-weeks)
8. `depth_analysis` (split from roster_health)
9. `stack_analysis` (QB/WR/TE correlation in matchup sim)
10. `waiver_efficiency` / `manager_efficiency` / `trade_history` (needs snapshots + txs)
11. `luck_index` (expected wins from points vs actual)
12. `matchup_simulator` season-level is already `playoff_odds`; weekly is `matchup` — don’t duplicate names
13. `lineup_optimizer` (constraint solver) only if greedy start/sit is empirically wrong on Superflex/IDP/best-ball

#### D3. Differentiation (later)

Revenge mode, league psychology, 10k what-if championship sims. Requires D2 historical plugins + A1 snapshots actually queried.

### Stream E — Ask Otho

#### E1. Tool quality and the example questions

**Goal:** The six README-class questions work in fallback **and** LLM mode.

| Question | Gap today | Build |
|---|---|---|
| What happened in my league since yesterday? | No time filter; `league_pulse` is this-week counts | Tool `league_delta(since=)` over txs + snapshots + injuries |
| Why am I projected to lose? | Matchup returns WP, not an attribution | Tool or matchup param `explain=true`: top negative slots vs opponent |
| Trade that helps RB without killing WR depth | `find_trade_targets` is 1-for-1 weekly | Pass constraints into trade_finder (`need_pos`, `protect_pos`) |
| What is my opponent likely to do on waivers? | Scout is letter grades | Opponent scout + waiver intersection |
| Season 10k times if I make this trade | `simulate_trade` is weekly delta; playoff_odds doesn’t accept roster edits | `playoff_odds` param `roster_overrides` |
| Who should I stash before waivers? | No stash vs this-week distinction | Waiver scoring: ROS vs this week flag |
| Anything before the 1 PM games? | No kickoff times | Needs NFL schedule provider — ship a poorer “before Sunday” using `nfl_state` until B3 |

**Also:**

- Streaming tokens for LLM mode (`text/event-stream` from `/api/ask`).
- Conversation turns (last N Q&A in the request).
- System prompt: inject week, record, opponent name, deadline if known — still **no invented stats**.
- Test the LLM path with a fake httpx (no live OpenAI in CI).
- Fallback: replace brittle `KEYWORD_TOOLS` with embedding-free routing table **plus** always running `league_pulse` for “what happened” questions.

**Deps:** D1 tools must return the data the questions need.

**Done:** Golden-question pytest on the demo league for fallback; one recorded fixture for `_llm_ask`. UI shows tools used (already does) and streams.

**Risk:** Spending time on prompts while projections are still rank-based. E1 after B1/D1.

### Stream F — Dashboard UX

#### F1. Decision surface completeness

**Goal:** Home answers “what now?” without visiting six plugin pages.

**Tasks:**

- Pass `week` into `PluginPage` and Ask Otho.
- Include `league_activity` pulse on Home (watch column).
- Empty/error/loading: today Home is blank until dashboard returns; plugin failures are silent. Surface `plugins[].error` in a collapsed debug, and per-column skeletons.
- Starters: show live points vs projection bar (data is on `MatchupSide.player_points` — unused on Home).
- Identify “You”: persist selected `roster_id` in `localStorage`; optional paste Sleeper user to auto-pick.
- Mobile: one `@media (max-width: 900px)` exists; Ask dock + hero still cramped. Stack Ask as a bottom sheet; don’t hide columns.
- Players route: either rename to Health or add search (`GET /api/players/search` already exists) + player card drawer.

**Deps:** A2 for live points to move.

**Done:** Week switch changes plugin pages; a failed waiver plugin shows an error chip, not “Quiet.”

**Risk:** Don’t add a component library. Keep the current visual language.

### Stream G — Historical intelligence

Blocked on A1 (snapshots that are read) + weeks of data.

#### G1. Snapshot query API and first historical plugins

- `GET /api/leagues/{id}/history?week=`
- Plugins: `luck_index`, `manager_profiles` (tx patterns), `waiver_efficiency`
- Luck = actual wins − expected wins from weekly scoring distributions already in matchup sim

**Done:** For a synced league with ≥3 weeks of snapshots, manager profile returns at least one behavioral flag that is testable with a fixture (e.g. “dropped a player after one game”).

### Stream H — Ops / quality

#### H1. Now

- GitHub Actions: `pip install -e ".[dev]" && pytest` + `npm run typecheck && npm run build`.
- Run Alembic on Postgres boot **or** delete the illusion: either `alembic upgrade head` in the backend Dockerfile and add `psycopg2-binary` (or use async alembic), or document `create_all` as the v0.1 migrator and stop implying Alembic is live.
- Healthcheck that verifies DB (`/health` is currently a literal).
- Logging: request id, league_id, plugin_id, sync duration, Sleeper status codes.
- Rate-limit metrics: count Sleeper calls/min on `SleeperClient`.
- Tests to add immediately: waiver `gap`, trending via cache, playoff remaining matchups, dashboard doesn’t 500 if one plugin fails (already true — assert it), mapper does not treat `custom_points` as projections.

#### H2. Later

- OpenTelemetry, Sentry, multi-user auth, backups, env-based projection keys in compose.

## 5. Milestone map (what to build in order)

```
Week-of-season usefulness
├── M0 D1 bugfixes (waiver gap, trending cache, week param) [no deps]
├── M1 B1 scoring-aware projections + stats table fill [no deps]
├── M2 A1 sync/snapshot/catalog integrity [no deps]
├── M3 D1 playoff actual schedule + remaining-projection matchup + FAAB
├── M4 A2 WS + plugin result cache + F1 week/errors/live points
├── M5 E1 Ask Otho golden questions
├── M6 B2 optional FantasyPros/news keys
├── M7 D2 player_trends, news_impact, luck_index, power_rankings
├── M8 G1 manager_profiles / waiver_efficiency
├── M9 D3 revenge / psychology / 10k what-if
└── M10 A3 Redis Streams + H2 auth/observability
```

M0–M5 is the product. M6+ is depth. M9–M10 is differentiation and scale.

**Definition of “Otho is useful this weekend”:** M0–M5 on a real Sleeper league: start/sit that matches scoring, waivers that don’t crash, WP that moves as games progress, Ask Otho explaining a projected loss from plugin data.

## 6. Plugin backlog

Status: **shipped** = reliable on a real league, **partial** = code exists but thin/wrong inputs, **not started**.

None of the nine builtins are shipped. All nine are **partial**: real Python, wired into `otho.plugins` / `HOME_PLUGINS` / Ask Otho tools, but bound to heuristic projections and (in several cases) wrong or missing inputs.

| Plugin | Status | What good looks like |
|---|---|---|
| `lineup` | partial | Slot-level start/sit vs optimal; flags empty/OUT starters; respects `is_out`; `week` from UI. Greedy is OK until Superflex/IDP empirically fails. |
| `lineup_optimizer` | not started | Constraint solver only if greedy start/sit is wrong on Superflex/IDP/best-ball. Do not build as a 10th heuristic plugin. |
| `matchup` | partial | Win probability over **remaining** players (subtract live `player_points` from projection). Independent Gaussians until `stack_analysis`. `explain=true` names top negative slots vs opponent. |
| `waiver_wire` | partial | `gap = typical[pos] - top` defined (no `NameError`); FAAB remaining; trending from cache; filter by position need before scanning 400 players; drop candidates as a second ranking. |
| `drop_candidates` | not started | Fold into `waiver_wire` unless UI needs its own page. Worst bench vs best FA, same scoring as claims. |
| `roster_health` | partial | Grades **relative to league** (z-score vs other rosters), not absolute 18 = A+. |
| `depth_analysis` | not started | Split from roster_health: by-position depth chart, IR/bye holes, who is one injury from a zero. |
| `opponent_scout` | partial | “They will need X on waivers” from IR/OUT + thin depth, not only letter grades. Intersects with waiver ranking for Ask Otho. |
| `league_activity` | partial | On Home watch (or a Pulse drawer). “Since yesterday” filter. Cheap path — no Monte Carlo. Persist events past process restart. |
| `injury_watch` | partial | Replacement from bench then waivers; persist events to DB; publish dashboard invalidation. Restart must not wipe alerts. |
| `trade_finder` | partial | Cap combinatorial explosion; 2-for-1 with value bands; constraints (`need_pos`, `protect_pos`); ROS/value when B1 exists, not only this week’s proj. |
| `trade_analyzer` | not started | Proper 2-way rest-of-season grader. Keep `trade_finder` as search. Accepts a proposed package, returns both sides’ ROS delta. |
| `playoff_odds` | partial | Actual remaining matchup graph from synced weeks (`current..playoff_start-1`). `roster_overrides` param so Ask Otho can sim a trade. Random pairing is the #1 reason odds are fiction. |
| `buy_low_sell_high` | not started | Rest-of-season value vs last-3-weeks production. Needs B1 stats + ROS. |
| `schedule_strength` | not started | Remaining opponent difficulty by position, from real matchup graph + projections. |
| `power_rankings` | not started | League-relative roster + recent scoring + remaining schedule. Not a restatement of Sleeper standing. |
| `luck_index` | not started | Actual wins − expected wins from weekly scoring distributions already in matchup sim. Needs snapshots + weeks of data. |
| `manager_efficiency` | not started | Start/sit mistakes, waiver hit rate, trade value captured — from snapshots + txs. |
| `waiver_efficiency` | not started | Claims vs available alternatives at the time (needs snapshots). Testable fixture: “dropped a player after one game.” |
| `trade_history` | not started | League trade log with value at the time of the deal, not current proj. Needs snapshots + txs. |
| `player_trends` | not started | Usage / targets / snap share over last N weeks. Needs `player_stats`. |
| `news_impact` | not started | Headline → affected players → delta to start/sit and waivers. Needs a real news provider. |
| `weather` | not started | Later feed (B3). Do not start until B1 is in and two in-season weekends have been survived. |
| `stack_analysis` | not started | QB/WR/TE correlation in matchup sim. Named plugin; do not silently bake correlation into `matchup`. |
| `boom_bust` | not started | Extract from matchup p10/p90. Weekly volatility, not a second WP. |
| `floor_ceiling` | not started | Extract from matchup p10/p90. Pair with `boom_bust`; don’t duplicate Monte Carlo. |
| `league_tendencies` | not started | Differentiation (D3): how this league actually trades, claims, and panics. Needs queried snapshots. |
| `manager_profiles` | not started | Tx-pattern flags (G1). ≥3 weeks of snapshots; at least one behavioral flag testable with a fixture. |
| `roster_value` | not started | Compute and store `PlayerValue` (`domain/value.py` exists, unused). ROS + positional scarcity in this league. |
| `championship_path` | not started | Differentiation: which remaining outcomes put you in the dance. Needs real remaining schedule (D1 playoff_odds). |
| `playoff_simulator` | not started | Season-level is already `playoff_odds`; weekly is `matchup`. **Do not duplicate names.** |
| Revenge mode | not started | D3. Do not build before ACTIONS is trustworthy on Sunday morning. |
| League psychology | not started | D3. Requires D2 historical plugins + A1 snapshots actually queried. |
| What-if 10k | not started | Championship sims with roster edits. `playoff_odds` + `roster_overrides` first; 10k what-if is later packaging. |

## 7. Recommended next 3 things

Opinionated for **in-season this week**, not architecture theater:

1. **Fix the v0.1 decision loop so it doesn’t lie or crash.** Undefined `gap` in `waiver_wire/analyzer.py`; `PlayerService.trending` reads Redis/in-memory cache; pass `week` from `App.tsx` into plugin pages and Ask Otho; remaining-points matchup (subtract live `player_points`); playoff odds using real remaining Sleeper matchups instead of random pairing.

2. **Make projections league-true.** Implement a stats-backed or scoring-settings-aware `ProjectionProvider` and persist `player_stats`. Until this lands, start/sit, waivers, trades, WP, and Ask Otho are rearranging `search_rank`. Heuristic can stay as fallback (`source=otho.heuristic`).

3. **Wire live Home + Ask Otho to those plugins.** WebSocket refetch, plugin-result cache so refetch is cheap, `league_delta` / matchup `explain` tools, and fallback routes for “what happened since yesterday” and “why am I projected to lose?” Do not buy FantasyPros or build revenge mode before a manager can trust Sunday morning’s ACTIONS column.

Do **not** next: Redis Streams, Next.js rewrite, auth, betting, 10k what-if, or a 10th plugin that still reads heuristic points.

## 8. Out of scope / later

- Auth / multi-user / Sleeper OAuth
- Dynasty / keeper / draft-pick trading as a product surface
- Best-ball / IDP-first
- Next.js rewrite (Vite/React stays)
- SSE until WS is proven in the UI
- Redis Streams / multi-worker jobs until one process is the bottleneck
- Betting lines, weather, own ML models
- Revenge / psychology / 10k championship what-if
- Mobile native apps
- Non-Sleeper league providers (ESPN, Yahoo)
- Rewriting plugins when adding FantasyPros — forbidden; that would be a regression

**Bottom line:** the OS shape is in place (`otho.plugins`, domain models, FastAPI, Vite dashboard, 9 builtins, Ask Otho fallback). Remaining work is to make the **data true**, the **sync historically queryable**, the **existing plugins non-buggy and schedule-aware**, and **Ask Otho + Home actually live**. Everything else is a plugin on top of that.
