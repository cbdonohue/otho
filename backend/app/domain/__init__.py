"""Provider-agnostic fantasy domain models.

Plugins MUST depend on these objects, never on Sleeper (or any provider) JSON.
"""

from app.domain.analysis import AnalysisBrief, PositionalGrade
from app.domain.injury import Injury
from app.domain.league import League, LeagueUser
from app.domain.matchup import Matchup, MatchupSide
from app.domain.news import PlayerNews
from app.domain.player import Player, TrendingPlayer
from app.domain.projection import Projection
from app.domain.roster import Roster, RosterPlayer
from app.domain.transaction import Transaction
from app.domain.value import PlayerValue

__all__ = [
    "AnalysisBrief",
    "Injury",
    "League",
    "LeagueUser",
    "Matchup",
    "MatchupSide",
    "Player",
    "PlayerNews",
    "PlayerValue",
    "PositionalGrade",
    "Projection",
    "Roster",
    "RosterPlayer",
    "Transaction",
    "TrendingPlayer",
]
