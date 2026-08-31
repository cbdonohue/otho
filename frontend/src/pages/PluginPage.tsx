import { useEffect, useState } from "react";
import { api } from "../api";
import { WidgetView } from "../widgets/WidgetView";

export function PluginPage({
  pluginId,
  leagueId,
  rosterId,
  title,
}: {
  pluginId: string;
  leagueId?: string;
  rosterId?: number;
  title: string;
}) {
  const [result, setResult] = useState<{ title: string; summary: string; widgets: Record<string, unknown>[] } | null>(
    null,
  );
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!leagueId) return;
    api
      .analyze(pluginId, leagueId, { roster_id: rosterId })
      .then((r) => setResult(r as typeof result))
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, [pluginId, leagueId, rosterId]);

  return (
    <div className="page">
      <h2 className="hero-name">{title}</h2>
      {err && <div className="err">{err}</div>}
      {result && <p className="muted">{result.summary}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
        {result?.widgets?.map((w, i) => (
          <WidgetView key={i} widget={w as never} />
        ))}
      </div>
    </div>
  );
}
