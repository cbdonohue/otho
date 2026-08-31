import type { Widget } from "./api";

function sev(w: Widget): string {
  return String(w.severity || w.type || "info");
}

export function WidgetView({ widget }: { widget: Widget }) {
  const t = widget.type;
  if (t === "recommendation") {
    return (
      <div className={`widget sev-${sev(widget)}`}>
        <div className="w-title">{String(widget.title)}</div>
        <div className="w-sub">{String(widget.subtitle)}</div>
        {widget.confidence != null && (
          <div className="muted" style={{ marginTop: 4, fontFamily: "var(--font-mono)", fontSize: 11 }}>
            confidence {(Number(widget.confidence) * 100).toFixed(0)}%
          </div>
        )}
      </div>
    );
  }
  if (t === "alert") {
    return (
      <div className={`widget sev-${sev(widget)}`}>
        <div className="w-title">{String(widget.title)}</div>
        <div className="w-sub">{String(widget.body)}</div>
      </div>
    );
  }
  if (t === "metric") {
    return (
      <div className="widget">
        <div className="metric-row">
          <span className="muted">{String(widget.label)}</span>
          <span className="metric-value">{String(widget.value)}</span>
        </div>
        {widget.hint ? <div className="w-sub">{String(widget.hint)}</div> : null}
      </div>
    );
  }
  if (t === "ranking") {
    const items = (widget.items as { rank: number; label: string; value: number | string; meta?: string }[]) || [];
    return (
      <div className="widget">
        {widget.title ? <div className="w-title">{String(widget.title)}</div> : null}
        {items.map((item) => (
          <div className="rank-item" key={`${item.rank}-${item.label}`}>
            <span className="rank-n">{item.rank}</span>
            <span style={{ flex: 1 }}>{item.label}</span>
            <span className="muted">{item.meta}</span>
            <span className="metric-value" style={{ fontSize: 14 }}>
              {typeof item.value === "number" && item.value <= 1 && item.value >= 0
                ? `${(item.value * 100).toFixed(0)}%`
                : item.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  if (t === "player_table") {
    const columns = (widget.columns as string[]) || [];
    const rows = (widget.rows as Record<string, unknown>[]) || [];
    return (
      <div className="widget" style={{ overflowX: "auto" }}>
        {widget.title ? <div className="w-title">{String(widget.title)}</div> : null}
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((c) => (
                  <td key={c}>{String(row[c] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (t === "matchup") {
    const home = widget.home as { name: string; projected?: number; record?: string };
    const away = widget.away as { name: string; projected?: number; record?: string } | null;
    return (
      <div className="widget">
        <div className="w-title">
          {home?.name} vs {away?.name ?? "BYE"}
        </div>
        <div className="w-sub">
          {home?.projected?.toFixed?.(1)} – {away?.projected?.toFixed?.(1)} · win{" "}
          {widget.win_probability != null ? `${(Number(widget.win_probability) * 100).toFixed(0)}%` : "—"}
        </div>
      </div>
    );
  }
  if (t === "timeline") {
    const events = (widget.events as { title: string; body: string; week?: number }[]) || [];
    return (
      <div className="widget">
        {widget.title ? <div className="w-title">{String(widget.title)}</div> : null}
        {events.slice(0, 8).map((e, i) => (
          <div className="rank-item" key={i}>
            <span className="rank-n">{e.week ?? "·"}</span>
            <div>
              <div>{e.title}</div>
              <div className="w-sub">{e.body}</div>
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (t === "comparison") {
    const left = widget.left as Record<string, unknown>;
    const right = widget.right as Record<string, unknown>;
    return (
      <div className="widget">
        <div className="w-title">{String(widget.title || "Comparison")}</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <div>
            <div>{String(left?.name)}</div>
            <div className="metric-value">{String(left?.projection ?? "")}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div>{String(right?.name)}</div>
            <div className="metric-value">{String(right?.projection ?? "")}</div>
          </div>
        </div>
      </div>
    );
  }
  if (t === "chart") {
    const labels = (widget.labels as string[]) || [];
    const series = (widget.series as { values: number[] }[]) || [];
    const values = series[0]?.values || [];
    const max = Math.max(1, ...values);
    return (
      <div className="widget">
        {widget.title ? <div className="w-title">{String(widget.title)}</div> : null}
        {labels.map((label, i) => (
          <div key={label} style={{ display: "grid", gridTemplateColumns: "40px 1fr 48px", gap: 8, alignItems: "center", margin: "6px 0" }}>
            <span className="pos-tag">{label}</span>
            <div className="bar">
              <div style={{ width: `${(100 * (values[i] || 0)) / max}%` }} />
            </div>
            <span className="muted" style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
              {(values[i] || 0).toFixed(1)}
            </span>
          </div>
        ))}
      </div>
    );
  }
  if (t === "markdown" || t === "player_card") {
    return (
      <div className="widget">
        <div className="w-title">{String(widget.title || widget.name || "")}</div>
        <div className="w-sub">{String(widget.content || widget.subtitle || "")}</div>
      </div>
    );
  }
  return (
    <div className="widget">
      <div className="muted">{t}</div>
    </div>
  );
}
