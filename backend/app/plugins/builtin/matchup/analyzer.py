from __future__ import annotations

import random
from statistics import mean

from app.domain import Player, Projection

POSITION_STD = {
    "QB": 6.4,
    "RB": 5.6,
    "WR": 5.2,
    "TE": 4.1,
    "K": 3.0,
    "DEF": 5.1,
}


def std_for(position: str | None, points: float) -> float:
    base = POSITION_STD.get((position or "").upper(), 4.5)
    return max(1.5, min(base, points * 0.55 + 1.2))


def sample_score(players: list[tuple[Player, Projection]], rng: random.Random) -> float:
    total = 0.0
    for player, proj in players:
        sigma = std_for(player.position, proj.points)
        total += max(0.0, rng.gauss(proj.points, sigma))
    return total


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, int(round((p / 100) * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


def simulate(
    home: list[tuple[Player, Projection]],
    away: list[tuple[Player, Projection]],
    iterations: int = 4000,
    seed: int = 8,
) -> dict:
    rng = random.Random(seed)
    home_scores: list[float] = []
    away_scores: list[float] = []
    wins = 0
    ties = 0
    for _ in range(iterations):
        h = sample_score(home, rng)
        a = sample_score(away, rng)
        home_scores.append(h)
        away_scores.append(a)
        if h > a:
            wins += 1
        elif abs(h - a) < 0.05:
            ties += 1
    home_scores.sort()
    away_scores.sort()
    win_p = (wins + 0.5 * ties) / max(1, iterations)
    return {
        "iterations": iterations,
        "win_probability": round(win_p, 4),
        "home": {
            "mean": round(mean(home_scores), 2),
            "p10": round(percentile(home_scores, 10), 2),
            "p90": round(percentile(home_scores, 90), 2),
        },
        "away": {
            "mean": round(mean(away_scores), 2),
            "p10": round(percentile(away_scores, 10), 2),
            "p90": round(percentile(away_scores, 90), 2),
        },
    }
