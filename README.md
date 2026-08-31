# Otho

**Otho** is a fantasy-football **analysis operating system**. Sleeper is one data provider. Every piece of analysis is a plugin. **Ask Otho** is the main interface.

This is not a prettier Sleeper dashboard. Sleeper supplies league state; plugins add intelligence; the UI answers: **what should I be doing right now?**

## Architectural rule (non-negotiable)

Plugins **never** depend on Sleeper JSON.

```
Sleeper JSON  →  SleeperProvider  →  normalized domain models  →  plugins
```

Normalized objects live in `backend/app/domain/` (`Player`, `Roster`, `League`, `Matchup`, `Transaction`, `Projection`, `PlayerNews`, `Injury`, `PlayerValue`). Mapping from Sleeper JSON happens **only** in `backend/app/providers/sleeper/mapper.py`. Later you can add FantasyPros, injury APIs, betting lines, or ML models without rewriting plugins.

## Quick start (local, no Docker)

Python 3.12+ and Node 20+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# SQLite + in-process cache are the defaults — Postgres/Redis optional.

PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

- **LOAD DEMO** seeds a local two-team league (no network).
- **SYNC LEAGUE** takes a public Sleeper league ID from the league URL (`https://sleeper.com/leagues/<id>/...`). The Sleeper API is public and needs no auth. The first NFL player catalog sync is large; it is cached for 24h.

Ask Otho works **without** `OPENAI_API_KEY`: it runs relevant plugins and synthesizes an answer from their results. Set `OPENAI_API_KEY` (OpenAI-compatible) to let the model pick tools via `plugin.tools()`.

## Docker Compose

```bash
docker compose up --build
```

Services: Postgres 16, Redis 7, FastAPI (`:8000`), Vite/nginx frontend (`:5173`).

```
GET /health
```

## Repository layout

```
backend/app/
  main.py              # FastAPI gateway
  api/                 # leagues, plugins, dashboard, ask, websocket, players
  core/                # config, database, cache, events, scheduler, ORM
  domain/              # provider-agnostic fantasy objects
  providers/
    sleeper/           # client + mapper + provider
    projections/       # heuristic stub (v0.1)
    news/ stats/       # stub interfaces
  services/            # sync, league/player/projection/news, Ask Otho
  plugins/
    sdk/               # tiny plugin API
    manager.py         # builtins + importlib.metadata entry points
    builtin/           # v0.1 analysis plugins
frontend/              # React + Vite dashboard
```

## Plugin SDK

```python
@dataclass(frozen=True)
class PluginMetadata:
    id: str
    name: str
    description: str
    version: str
    category: str
    icon: str | None = None

class AnalysisPlugin(ABC):
    metadata: PluginMetadata
    async def analyze(self, context: AnalysisContext, params: dict) -> AnalysisResult: ...
    def tools(self) -> list[AgentTool]: ...          # Ask Otho
    subscriptions: list[str] = []                    # background plugins
    async def handle_event(self, event) -> None: ...
```

Three kinds:

1. **Analysis** — user-invoked `analyze` (`POST /api/plugins/{id}/analyze`)
2. **Background** — `subscriptions` + `handle_event` on the in-process event bus (Redis Streams can replace the transport later; the plugin API does not change)
3. **Agent tools** — `plugin.tools()` discovered by Ask Otho

Plugins return **widgets** (`player_card`, `player_table`, `metric`, `chart`, `ranking`, `alert`, `timeline`, `matchup`, `recommendation`, `comparison`, `markdown`). The frontend renders them; plugins do not import React.

### Built-in plugins (v0.1)

| id | what it does |
|----|----------------|
| `matchup` | Monte Carlo matchup from projections + positional variance |
| `lineup` | Start/sit vs optimal lineup |
| `waiver_wire` | Rank free agents by projection × positional need |
| `roster_health` | Positional grades / holes |
| `opponent_scout` | Opponent strengths and likely waiver needs |
| `league_activity` | Transaction pulse (also a background subscriber) |
| `injury_watch` | Injury/roster-change detector (background + analysis) |
| `trade_finder` | 1-for-1 ideas + trade grader |
| `playoff_odds` | Rest-of-season Monte Carlo standings |

### Add a plugin

**Built-in:** create `backend/app/plugins/builtin/<name>/` with `plugin.py`, `models.py`, `analyzer.py`. Export `PLUGIN = YourPlugin`. Add the module to `BUILTIN_MODULES` in `plugins/manager.py`.

**Installable:** publish a package that exposes an `otho.plugins` entry point:

```toml
[project.entry-points."otho.plugins"]
my_plugin = "my_pkg.plugin:MyPlugin"
```

```bash
pip install my-otho-plugin
```

Otho loads `importlib.metadata.entry_points(group="otho.plugins")` on boot. Your plugin class is constructed with no args and must implement `AnalysisPlugin`. It receives `AnalysisContext` (league / player / projection / news services, cache, events) — never a Sleeper client.

## Event bus

In-process async bus from day one. Events:

`league.synced`, `roster.updated`, `matchup.updated`, `transaction.created`, `player.news`, `player.injury`, `projection.updated`, `game.started`, `game.completed`, `week.changed`

WebSocket: `WS /api/live/{league_id}`.

## Data sync (Sleeper)

Public read-only API, `https://api.sleeper.app/v1/`, rate-limited in the client (~12 req/s, well under 1000/min). Adaptive polling:

| data | interval |
|------|----------|
| NFL players | 24h (cached hard) |
| league settings | 6h |
| rosters | ~90s |
| transactions | ~90s |
| matchups live / game day / else | 20s / 120s / 600s |
| trending | ~7 min |

Roster snapshots are stored historically in `snapshots`, not only current state.

## API

```
GET  /health
GET  /api/leagues
POST /api/leagues                  { "league_id": "<sleeper id>" }
POST /api/leagues/demo
GET  /api/leagues/{league_id}
GET  /api/leagues/{league_id}/rosters
GET  /api/leagues/{league_id}/matchups
GET  /api/leagues/{league_id}/transactions

GET  /api/plugins
GET  /api/plugins/{plugin_id}
POST /api/plugins/{plugin_id}/analyze?league_id=...
     { "roster_id": 4, "week": 8, "iterations": 10000 }

GET  /api/dashboard/{league_id}
GET  /api/dashboard/{league_id}/widgets
POST /api/ask                      { "question", "league_id", "roster_id" }
WS   /api/live/{league_id}
```

## Tests

Unit tests do **not** hit the network.

```bash
pip install -e ".[dev]"
PYTHONPATH=backend pytest -q
cd frontend && npm run typecheck && npm run build
```

## Config

See `.env.example`. `DATABASE_URL` defaults to SQLite; set `postgresql+asyncpg://...` for Postgres. Leave `REDIS_URL` empty for the in-process cache. CORS defaults include `http://localhost:5173`.

## Roadmap

v0.1 is a working modular monolith skeleton. Remaining work — current state, workstreams, plugin backlog, and the next three things — lives in [`docs/PLAN.md`](docs/PLAN.md).

## Branding

The product is **Otho**. Entry-point group: **`otho.plugins`**. UI label for the agent: **ASK OTHO**.
