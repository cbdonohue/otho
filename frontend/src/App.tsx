import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { useDashboard } from "./components/AskOtho";
import { HomePage } from "./pages/HomePage";
import { PluginPage } from "./pages/PluginPage";

export default function App() {
  const [leagues, setLeagues] = useState<{ league_id: string; name: string }[]>([]);
  const [leagueId, setLeagueId] = useState<string | undefined>();
  const [rosterId, setRosterId] = useState<number | undefined>();
  const [week, setWeek] = useState<number | undefined>();
  const [sleeperId, setSleeperId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const { data, error, loading } = useDashboard(leagueId, rosterId, week);

  async function refreshLeagues(select?: string) {
    const res = await api.leagues();
    setLeagues(res.leagues);
    const next = select || res.leagues[0]?.league_id;
    if (next) setLeagueId(next);
  }

  useEffect(() => {
    refreshLeagues().catch((e) => setErr(e instanceof Error ? e.message : "boot failed"));
  }, []);

  useEffect(() => {
    if (data?.roster && rosterId == null) setRosterId(data.roster.roster_id);
    if (data?.week && week == null) setWeek(data.week);
  }, [data, rosterId, week]);

  async function addSleeper() {
    setBusy(true);
    setErr(null);
    try {
      const res = await api.addLeague(sleeperId.trim());
      await refreshLeagues(res.league.league_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "sync failed");
    } finally {
      setBusy(false);
    }
  }

  async function demo() {
    setBusy(true);
    setErr(null);
    try {
      const res = await api.seedDemo();
      await refreshLeagues(res.league.league_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "demo failed");
    } finally {
      setBusy(false);
    }
  }

  if (!leagueId) {
    return (
      <div className="setup">
        <div className="brand">OTHO</div>
        <h1>Fantasy analysis OS</h1>
        <p className="muted">
          Sleeper is a data provider. Plugins do the thinking. Paste a public Sleeper league ID (from the league URL)
          or load the built-in demo.
        </p>
        <label className="muted">SLEEPER LEAGUE ID</label>
        <input className="field" value={sleeperId} onChange={(e) => setSleeperId(e.target.value)} placeholder="1122669988891230208" />
        <button onClick={addSleeper} disabled={busy || !sleeperId.trim()}>
          {busy ? "SYNCING…" : "SYNC LEAGUE"}
        </button>
        <button onClick={demo} disabled={busy}>
          LOAD DEMO
        </button>
        {err && <p className="err">{err}</p>}
      </div>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          OTHO
          <span>ANALYSIS OS</span>
        </div>
        <div className="topbar-controls">
          {data?.hero && (
            <span className="muted">
              <span className="live-dot" />
              WEEK {data.week}
            </span>
          )}
          <select
            value={week ?? ""}
            onChange={(e) => setWeek(Number(e.target.value))}
          >
            {Array.from({ length: 18 }, (_, i) => i + 1).map((w) => (
              <option key={w} value={w}>
                WEEK {w}
              </option>
            ))}
          </select>
          <select value={leagueId} onChange={(e) => setLeagueId(e.target.value)}>
            {leagues.map((l) => (
              <option key={l.league_id} value={l.league_id}>
                {l.name}
              </option>
            ))}
          </select>
          <select
            value={rosterId ?? ""}
            onChange={(e) => setRosterId(Number(e.target.value))}
          >
            {(data?.rosters || []).map((r) => (
              <option key={r.roster_id} value={r.roster_id}>
                {r.name} ({r.record})
              </option>
            ))}
          </select>
        </div>
      </header>
      <nav className="nav">
        <NavLink to="/" end>
          League Pulse
        </NavLink>
        <NavLink to="/waivers">Waivers</NavLink>
        <NavLink to="/trades">Trades</NavLink>
        <NavLink to="/players">Players</NavLink>
        <NavLink to="/matchups">Matchups</NavLink>
        <NavLink to="/playoffs">Playoffs</NavLink>
      </nav>
      {(loading || error) && !data && (
        <div className="page muted">{loading ? "Crunching plugins…" : error}</div>
      )}
      <Routes>
        <Route path="/" element={<HomePage dash={data} leagueId={leagueId} rosterId={rosterId} />} />
        <Route
          path="/waivers"
          element={<PluginPage pluginId="waiver_wire" leagueId={leagueId} rosterId={rosterId} title="WAIVERS" />}
        />
        <Route
          path="/trades"
          element={<PluginPage pluginId="trade_finder" leagueId={leagueId} rosterId={rosterId} title="TRADES" />}
        />
        <Route
          path="/players"
          element={<PluginPage pluginId="roster_health" leagueId={leagueId} rosterId={rosterId} title="PLAYERS / HEALTH" />}
        />
        <Route
          path="/matchups"
          element={<PluginPage pluginId="matchup" leagueId={leagueId} rosterId={rosterId} title="MATCHUPS" />}
        />
        <Route
          path="/playoffs"
          element={<PluginPage pluginId="playoff_odds" leagueId={leagueId} rosterId={rosterId} title="PLAYOFFS" />}
        />
      </Routes>
    </div>
  );
}
