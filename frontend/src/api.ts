const API = "";

export type Widget = {
  type: string;
  plugin_id?: string;
  [key: string]: unknown;
};

export type Dashboard = {
  league: { league_id: string; name: string; week: number; season: string };
  roster: { roster_id: number; owner_name?: string; record: string; starters: string[] };
  rosters: { roster_id: number; name: string; record: string }[];
  week: number;
  hero: {
    you: { name: string; record: string; points: number; roster_id: number };
    opponent: { name: string; record: string; points: number; roster_id: number } | null;
    week: number;
    projected_you?: number;
    projected_opp?: number;
    win_probability?: number;
  } | null;
  starters: {
    player_id: string;
    name: string;
    position?: string;
    team?: string;
    projection: number;
    injury?: string;
  }[];
  columns: { actions: Widget[]; opportunities: Widget[]; watch: Widget[] };
  plugins: unknown[];
  nfl_state: { week?: number; season?: string; season_type?: string };
};

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => http<{ status: string }>("/health"),
  leagues: () => http<{ leagues: { league_id: string; name: string; week?: number }[] }>("/api/leagues"),
  addLeague: (league_id: string) =>
    http<{ league: { league_id: string } }>("/api/leagues", {
      method: "POST",
      body: JSON.stringify({ league_id, provider: "sleeper" }),
    }),
  seedDemo: () => http<{ league: { league_id: string } }>("/api/leagues/demo", { method: "POST" }),
  dashboard: (leagueId: string, rosterId?: number, week?: number) => {
    const q = new URLSearchParams();
    if (rosterId) q.set("roster_id", String(rosterId));
    if (week) q.set("week", String(week));
    const qs = q.toString();
    return http<Dashboard>(`/api/dashboard/${leagueId}${qs ? `?${qs}` : ""}`);
  },
  plugins: () => http<{ plugins: { id: string; name: string; description: string; category: string }[] }>("/api/plugins"),
  analyze: (pluginId: string, leagueId: string, body: Record<string, unknown>) =>
    http(`/api/plugins/${pluginId}/analyze?league_id=${leagueId}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  ask: (question: string, leagueId: string, rosterId?: number) =>
    http<{ answer: string; mode: string; tools_used: string[]; widgets: Widget[] }>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question, league_id: leagueId, roster_id: rosterId }),
    }),
  rosters: (leagueId: string) => http<{ rosters: unknown[] }>(`/api/leagues/${leagueId}/rosters`),
  matchups: (leagueId: string) => http<{ matchups: unknown[]; week: number }>(`/api/leagues/${leagueId}/matchups`),
  transactions: (leagueId: string) =>
    http<{ transactions: unknown[] }>(`/api/leagues/${leagueId}/transactions`),
};
