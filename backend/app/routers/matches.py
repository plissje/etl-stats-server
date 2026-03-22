from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Match, Player, PlayerMatchStats
from app.schemas import MatchDetailOut, MatchSummaryOut, PlayerMatchRowOut

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _row(pms: PlayerMatchStats, pl: Player) -> PlayerMatchRowOut:
    return PlayerMatchRowOut(
        player_guid=pl.guid,
        name_display=pl.display_name,
        name_raw=pms.name_raw,
        team=pms.team,
        eff=pms.eff,
        kdr=pms.kdr,
        kills=pms.kills,
        deaths=pms.deaths,
        damage_given=pms.damage_given,
        damage_received=pms.damage_received,
        headshots=pms.headshots,
        gibs=pms.gibs,
        revives=pms.revives,
        team_medpacks=pms.team_medpacks,
    )


@router.get("", response_model=list[MatchSummaryOut])
def list_matches(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)) -> list[Match]:
    q = db.query(Match).order_by(Match.created_at.desc()).offset(skip).limit(min(limit, 200))
    return q.all()


@router.get("/{match_db_id}", response_model=MatchDetailOut)
def match_detail(match_db_id: int, db: Session = Depends(get_db)) -> MatchDetailOut:
    m = db.query(Match).filter(Match.id == match_db_id).one_or_none()
    if not m:
        raise HTTPException(404, "match not found")
    rows = (
        db.query(PlayerMatchStats, Player)
        .join(Player, Player.id == PlayerMatchStats.player_id)
        .filter(PlayerMatchStats.match_id == m.id)
        .all()
    )
    axis, allies = [], []
    for pms, pl in rows:
        r = _row(pms, pl)
        if pms.team == 1:
            axis.append(r)
        else:
            allies.append(r)
    axis.sort(key=lambda x: (-x.kills, x.name_display.lower()))
    allies.sort(key=lambda x: (-x.kills, x.name_display.lower()))
    return MatchDetailOut(
        match=MatchSummaryOut(
            id=m.id,
            match_id=m.match_id,
            mapname=m.mapname,
            winner_team=m.winner_team,
            round_start_unix=m.round_start_unix,
            round_end_unix=m.round_end_unix,
        ),
        axis=axis,
        allies=allies,
    )
