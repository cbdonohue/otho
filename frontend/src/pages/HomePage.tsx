import { WidgetView } from "../widgets/WidgetView";
import type { Dashboard } from "../api";
import { AskOtho } from "../components/AskOtho";

export function HomePage({
  dash,
  leagueId,
  rosterId,
}: {
  dash: Dashboard | null;
  leagueId?: string;
  rosterId?: number;
}) {
  if (!dash) {
    return <div className="page muted">Load a league to see what you should do right now.</div>;
  }
  const hero = dash.hero;
  const wp = hero?.win_probability ?? 0.5;
  const maxProj = Math.max(...dash.starters.map((s) => s.projection), 1);
  return (
    <>
      <div className="page">
        {hero && (
          <section className="hero">
            <div className="hero-side">
              <div className="hero-label">YOU · {hero.you.record}</div>
              <div className="hero-name">{hero.you.name}</div>
              <div className="hero-score">{(hero.projected_you ?? hero.you.points).toFixed(1)}</div>
              <div className="muted">proj · live {hero.you.points.toFixed(1)}</div>
            </div>
            <div className="hero-mid">
              <div className="vs">LIVE MATCHUP</div>
              <div className="wp-bar">
                <div className="you" style={{ width: `${wp * 100}%` }} />
                <div className="them" style={{ width: `${(1 - wp) * 100}%` }} />
              </div>
              <div className="wp-num">WIN PROB {(wp * 100).toFixed(0)}%</div>
              <div className="muted">WEEK {hero.week}</div>
            </div>
            <div className="hero-side right">
              <div className="hero-label">OPPONENT · {hero.opponent?.record ?? "BYE"}</div>
              <div className="hero-name">{hero.opponent?.name ?? "BYE"}</div>
              <div className="hero-score" style={{ color: "var(--orange)" }}>
                {(hero.projected_opp ?? hero.opponent?.points ?? 0).toFixed(1)}
              </div>
              <div className="muted">proj · live {(hero.opponent?.points ?? 0).toFixed(1)}</div>
            </div>
          </section>
        )}

        <div className="columns">
          {(["actions", "opportunities", "watch"] as const).map((key) => (
            <div className={`col ${key}`} key={key}>
              <h3>{key.toUpperCase()}</h3>
              <div className="col-body">
                {dash.columns[key].length === 0 && <div className="empty">Quiet.</div>}
                {dash.columns[key].slice(0, 6).map((w, i) => (
                  <WidgetView key={i} widget={w} />
                ))}
              </div>
            </div>
          ))}
        </div>

        <section className="starters">
          <h3 className="hero-label">STARTERS</h3>
          {dash.starters.map((s) => (
            <div className="starter-row" key={s.player_id}>
              <span className="pos-tag">{s.position}</span>
              <div>
                {s.name} <span className="muted">{s.team}</span>
                {s.injury ? <span className="err"> · {s.injury}</span> : null}
              </div>
              <div className="metric-value" style={{ fontSize: 16 }}>
                {s.projection.toFixed(1)}
              </div>
              <div className="bar">
                <div style={{ width: `${(100 * s.projection) / maxProj}%` }} />
              </div>
            </div>
          ))}
        </section>
      </div>
      <AskOtho leagueId={leagueId} rosterId={rosterId} />
    </>
  );
}
