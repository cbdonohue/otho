import { useEffect, useState, type FormEvent } from "react";
import { api, type Dashboard, type Widget } from "../api";
import { WidgetView } from "../widgets/WidgetView";

export function AskOtho({
  leagueId,
  rosterId,
}: {
  leagueId?: string;
  rosterId?: number;
}) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [tools, setTools] = useState<string[]>([]);
  const [mode, setMode] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  async function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!leagueId || !q.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await api.ask(q.trim(), leagueId, rosterId);
      setAnswer(res.answer);
      setWidgets(res.widgets || []);
      setTools(res.tools_used || []);
      setMode(res.mode);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Ask failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ask-dock">
      {answer && (
        <div className="ask-panel">
          <div className="ask-label">OTHO · {mode}</div>
          <div className="ask-answer">{answer}</div>
          {tools.length > 0 && (
            <div className="muted" style={{ marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 11 }}>
              tools: {tools.join(" · ")}
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 8, marginTop: 12 }}>
            {widgets.slice(0, 6).map((w, i) => (
              <WidgetView key={i} widget={w} />
            ))}
          </div>
        </div>
      )}
      <form className="ask-box" onSubmit={submit}>
        <div className="ask-label">ASK OTHO</div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="What should I do this week? Start Warren? Rank waivers?"
          disabled={!leagueId || busy}
        />
        <button type="submit" disabled={!leagueId || busy}>
          {busy ? "RUNNING" : "RUN"}
        </button>
      </form>
      {err && <div className="err" style={{ maxWidth: 1400, margin: "6px auto 0" }}>{err}</div>}
    </div>
  );
}

export function useDashboard(leagueId?: string, rosterId?: number, week?: number) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!leagueId) return;
    let cancel = false;
    setLoading(true);
    api
      .dashboard(leagueId, rosterId, week)
      .then((d) => {
        if (!cancel) setData(d);
      })
      .catch((e) => {
        if (!cancel) setError(e instanceof Error ? e.message : "load failed");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [leagueId, rosterId, week]);

  return { data, error, loading, setData };
}
