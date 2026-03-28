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
    axis_players: list[str] = []
    allies_players: list[str] = []
    mvp_name: str | None = None
    mvp_guid: str | None = None


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
    spam_kills: int

    distance_travelled_meters: float
    distance_travelled_spawn_avg: float
    spawn_count: int = 0
    speed_ups_avg: float = 0.0
    speed_ups_peak: float = 0.0
    crouched_seconds: int
    proned_seconds: int
    leaned_seconds: int
    classes_played: list[dict[str, Any]] | None = None

    time_played_pct: float
    team_kills: int
    team_damage_given: int
    team_gibs: int
    self_kills: int
    weapon_breakdown: list[dict[str, Any]] | None = None

class MatchRivalryOut(BaseModel):
    killer_guid: str
    killer_name: str
    victim_guid: str
    victim_name: str
    count: int

class MatchDetailOut(BaseModel):
    match: MatchSummaryOut
    axis: list[PlayerMatchRowOut]
    allies: list[PlayerMatchRowOut]
    axis_round1: list[PlayerMatchRowOut] | None = None
    allies_round1: list[PlayerMatchRowOut] | None = None
    axis_round2: list[PlayerMatchRowOut] | None = None
    allies_round2: list[PlayerMatchRowOut] | None = None
    rivalry: MatchRivalryOut | None = None


class PlayerProfileOut(BaseModel):
    guid: str
    display_name: str
    raw_name: str | None = None
    current_rating: float
    mvp_count: int = 0
    rating_history: list[dict[str, Any]] = []
    top_weapons: list[dict[str, Any]] = []
    nemesis: dict[str, Any] | None = None
    aliases: list[str] = []
    total_matches: int = 0
    match_history: list[dict[str, Any]] = []
    lifetime_stats: dict[str, Any] | None = None
