from __future__ import annotations

import random

from app.domain import Roster


def simulate_standings(
    rosters: list[Roster],
    remaining: int,
    playoff_teams: int,
    iterations: int = 2500,
    seed: int = 21,
) -> dict[int, float]:
    """Each remaining game: team scores N(ppg, 18); pair randomly each week (simple)."""
    rng = random.Random(seed)
    made = {r.roster_id: 0 for r in rosters}
    ppg = {r.roster_id: (r.points_for / r.games_played if r.games_played else 100.0) for r in rosters}
    ids = [r.roster_id for r in rosters]
    for _ in range(iterations):
        wins = {r.roster_id: r.wins for r in rosters}
        pf = {r.roster_id: r.points_for for r in rosters}
        for _week in range(max(0, remaining)):
            shuffled = ids[:]
            rng.shuffle(shuffled)
            pairs = list(zip(shuffled[::2], shuffled[1::2], strict=False))
            for a, b in pairs:
                sa = max(60.0, rng.gauss(ppg[a], 18))
                sb = max(60.0, rng.gauss(ppg[b], 18))
                pf[a] += sa
                pf[b] += sb
                if sa >= sb:
                    wins[a] += 1
                else:
                    wins[b] += 1
        ordered = sorted(ids, key=lambda i: (wins[i], pf[i]), reverse=True)
        for rid in ordered[:playoff_teams]:
            made[rid] += 1
    return {rid: round(made[rid] / iterations, 4) for rid in made}
