from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SubmitStatsBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    player_stats: dict[str, dict[str, Any]] = Field(default_factory=dict)
    round_info: dict[str, Any] | None = None


class MatchSummaryOut(BaseModel):
    id: int
    match_id: str
    mapname: str
    winner_team: int
    round_start_unix: int
    round_end_unix: int


class PlayerMatchRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_guid: str
    name_display: str
    name_raw: str | None
    team: int
    eff: float
    kdr: float
    kills: int
    deaths: int
    damage_given: int
    damage_received: int
    headshots: int
    gibs: int
    revives: int
    team_medpacks: int


class MatchDetailOut(BaseModel):
    match: MatchSummaryOut
    axis: list[PlayerMatchRowOut]
    allies: list[PlayerMatchRowOut]


class PlayerProfileOut(BaseModel):
    guid: str
    display_name: str
    current_rating: float
    rating_history: list[dict[str, Any]]
    top_weapons: list[dict[str, Any]]
