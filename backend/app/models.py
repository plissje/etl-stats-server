from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    mapname: Mapped[str] = mapped_column(String(128), index=True)
    winner_team: Mapped[int] = mapped_column(Integer)
    round_start_unix: Mapped[int] = mapped_column(Integer, default=0, index=True)
    round_end_unix: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    round1_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    round2_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    is_gather: Mapped[bool] = mapped_column(Integer, default=0) # 0=no, 1=yes
    match_winner_raw: Mapped[str | None] = mapped_column(String(16), nullable=True) # alpha/beta/draw

    mvp_player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True, index=True)

    round1_alpha_side: Mapped[int | None] = mapped_column(Integer, nullable=True)
    round2_alpha_side: Mapped[int | None] = mapped_column(Integer, nullable=True)

    server_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    server_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    player_stats: Mapped[list["PlayerMatchStats"]] = relationship(
        "PlayerMatchStats", back_populates="match", cascade="all, delete-orphan"
    )
    payloads: Mapped[list["MatchPayload"]] = relationship(
        "MatchPayload", back_populates="match", cascade="all, delete-orphan"
    )
    mvp_player: Mapped["Player | None"] = relationship("Player")


class MatchPayload(Base):
    __tablename__ = "match_payloads"
    __table_args__ = (UniqueConstraint("match_id", "round_number", name="uq_match_round_payload"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    match: Mapped["Match"] = relationship("Match", back_populates="payloads")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    raw_name_last: Mapped[str | None] = mapped_column(String(256), nullable=True)
    name_locked: Mapped[int] = mapped_column(Integer, default=0) # 0=no, 1=yes

    match_stats: Mapped[list["PlayerMatchStats"]] = relationship(
        "PlayerMatchStats", back_populates="player"
    )
    gather_rating: Mapped["PlayerGatherRating | None"] = relationship(
        "PlayerGatherRating", back_populates="player", uselist=False
    )
    rating_history: Mapped[list["PlayerGatherRatingHistory"]] = relationship(
        "PlayerGatherRatingHistory", back_populates="player"
    )
    aliases: Mapped[list["PlayerAlias"]] = relationship(
        "PlayerAlias", back_populates="player", cascade="all, delete-orphan"
    )


class PlayerAlias(Base):
    __tablename__ = "player_aliases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    alias: Mapped[str] = mapped_column(String(128), index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    player: Mapped["Player"] = relationship("Player", back_populates="aliases")


class PlayerMatchStats(Base):
    __tablename__ = "player_match_stats"
    __table_args__ = (UniqueConstraint("match_id", "player_id", "round_index", name="uq_match_player_round"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_index: Mapped[int] = mapped_column(Integer, default=0, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    team: Mapped[int] = mapped_column(Integer)

    kills: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    kdr: Mapped[float] = mapped_column(Float, default=0.0)
    eff: Mapped[float] = mapped_column(Float, default=0.0)
    unified_eff: Mapped[float] = mapped_column(Float, default=0.0)

    damage_given: Mapped[int] = mapped_column(Integer, default=0)
    damage_received: Mapped[int] = mapped_column(Integer, default=0)
    team_damage_given: Mapped[int] = mapped_column(Integer, default=0)
    team_damage_received: Mapped[int] = mapped_column(Integer, default=0)
    headshots: Mapped[int] = mapped_column(Integer, default=0)
    gibs: Mapped[int] = mapped_column(Integer, default=0)
    self_kills: Mapped[int] = mapped_column(Integer, default=0)
    team_kills: Mapped[int] = mapped_column(Integer, default=0)
    team_deaths_received: Mapped[int] = mapped_column(Integer, default=0)
    team_gibs: Mapped[int] = mapped_column(Integer, default=0)
    time_played_pct: Mapped[float] = mapped_column(Float, default=0.0)
    xp: Mapped[int] = mapped_column(Integer, default=0)

    revives: Mapped[int] = mapped_column(Integer, default=0)
    medkits: Mapped[int] = mapped_column(Integer, default=0)
    team_medpacks: Mapped[int] = mapped_column(Integer, default=0)
    pickup_medkits: Mapped[int] = mapped_column(Integer, default=0)
    pickup_ammopacks: Mapped[int] = mapped_column(Integer, default=0)
    shoves_given: Mapped[int] = mapped_column(Integer, default=0)
    shoves_received: Mapped[int] = mapped_column(Integer, default=0)
    spam_kills: Mapped[int] = mapped_column(Integer, default=0)

    distance_travelled_meters: Mapped[float] = mapped_column(Float, default=0.0)
    distance_travelled_spawn_avg: Mapped[float] = mapped_column(Float, default=0.0)
    spawn_count: Mapped[int] = mapped_column(Integer, default=0)
    speed_ups_avg: Mapped[float] = mapped_column(Float, default=0.0)
    speed_ups_peak: Mapped[float] = mapped_column(Float, default=0.0)
    crouched_seconds: Mapped[int] = mapped_column(Integer, default=0)
    proned_seconds: Mapped[int] = mapped_column(Integer, default=0)
    leaned_seconds: Mapped[int] = mapped_column(Integer, default=0)
    in_mg_seconds: Mapped[int] = mapped_column(Integer, default=0)
    in_sprint_seconds: Mapped[int] = mapped_column(Integer, default=0)
    in_disguise_seconds: Mapped[int] = mapped_column(Integer, default=0)
    is_downed_seconds: Mapped[int] = mapped_column(Integer, default=0)
    classes_played_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    objectives_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    hs_accuracy_event: Mapped[float | None] = mapped_column(Float, nullable=True)
    nemesis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    weapon_breakdown_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    name_raw: Mapped[str | None] = mapped_column(String(256), nullable=True)

    match: Mapped["Match"] = relationship("Match", back_populates="player_stats")
    player: Mapped["Player"] = relationship("Player", back_populates="match_stats")


class PlayerGatherRating(Base):
    __tablename__ = "player_gather_rating"

    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), primary_key=True)
    current_rating: Mapped[float] = mapped_column(Float, default=1500.0)
    mu: Mapped[float] = mapped_column(Float, default=25.0, server_default="25.0")
    sigma: Mapped[float] = mapped_column(Float, default=8.333, server_default="8.333")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    player: Mapped["Player"] = relationship("Player", back_populates="gather_rating")


class PlayerGatherRatingHistory(Base):
    __tablename__ = "player_gather_rating_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    rating: Mapped[float] = mapped_column(Float)
    delta: Mapped[float] = mapped_column(Float)
    mu: Mapped[float] = mapped_column(Float, nullable=True)
    sigma: Mapped[float] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    player: Mapped["Player"] = relationship("Player", back_populates="rating_history")
    match: Mapped["Match"] = relationship("Match")
