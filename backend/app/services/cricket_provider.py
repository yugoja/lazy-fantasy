"""Abstract cricket data provider interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderPlayer:
    provider_id: str
    name: str
    team_name: str
    batting_runs: int = 0
    batting_balls: int = 0
    bowling_wickets: int = 0
    bowling_overs: float = 0.0


@dataclass
class ProviderMatchInfo:
    provider_match_id: str
    name: str  # e.g. "MI vs CSK, 3rd Match"
    # "Match not started" | "Live" | "Result" | unknown string
    status: str
    team1_name: str
    team2_name: str
    lineup_announced: bool
    team1_players: list[ProviderPlayer] = field(default_factory=list)
    team2_players: list[ProviderPlayer] = field(default_factory=list)
    winner_name: str | None = None
    pom_name: str | None = None
    overs_completed: float | None = None


class CricketProvider(ABC):
    @abstractmethod
    def get_match_info(self, provider_match_id: str) -> ProviderMatchInfo | None:
        """Fetch full scorecard + lineup for a single match.
        Returns None on error so callers can skip the cycle."""
        ...

    @abstractmethod
    def search_matches(self, series_id: str) -> list[ProviderMatchInfo]:
        """List all matches in a series (e.g. IPL season)."""
        ...
