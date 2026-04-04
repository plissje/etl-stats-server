from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.deps import verify_stats_token
from app.schemas import SubmitStatsBody
from app.services.ingest import ingest_match_payloads
from app.models import Match, Player, PlayerMatchStats

router = APIRouter(prefix="/api", tags=["stats"])


@router.post("/submit-stats", dependencies=[Depends(verify_stats_token)])
def submit_stats(body: SubmitStatsBody | list[SubmitStatsBody], db: Session = Depends(get_db)) -> dict:
    try:
        if isinstance(body, list):
            payloads = [p.model_dump(exclude_none=True) for p in body]
        else:
            payloads = [body.model_dump(exclude_none=True)]
        
        match_row = ingest_match_payloads(db, payloads)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"ok": True, "match_db_id": match_row.id, "match_id": match_row.match_id}

@router.get("/match-manager/{ip}/{port}")
def get_match_id(ip: str, port: int) -> dict:
    from datetime import datetime
    import uuid
    # Use UTC timestamp + random suffix for global uniqueness
    now_unix = int(datetime.utcnow().timestamp())
    match_id = f"{uuid.uuid4().hex[:6]}{now_unix % 10000}"
    return {"match_id": match_id}

@router.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)) -> dict:
    total_matches = db.query(Match).count()
    total_players = db.query(Player).count()
    
    # Top 5 Played Maps
    top_maps_query = (
        db.query(Match.mapname, func.count(Match.id).label("match_count"))
        .group_by(Match.mapname)
        .order_by(func.count(Match.id).desc())
        .limit(5)
        .all()
    )
    top_maps = [{"mapname": m, "count": c} for m, c in top_maps_query]

    # Top 5 Players by SR
    from app.models import PlayerGatherRating
    top_players_query = (
        db.query(Player.display_name, Player.guid, PlayerGatherRating.current_rating)
        .join(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
        .order_by(PlayerGatherRating.current_rating.desc())
        .limit(5)
        .all()
    )
    top_players = [{"name": n, "guid": g, "rating": r} for n, g, r in top_players_query]

    # Recent 10 Matches
    recent_matches_query = (
        db.query(Match.id, Match.match_id, Match.mapname, Match.created_at)
        .order_by(Match.created_at.desc())
        .limit(10)
        .all()
    )
    recent_matches = [
        {"id": db_id, "match_id": m_id, "mapname": mapn, "created_at": ca.isoformat()}
        for db_id, m_id, mapn, ca in recent_matches_query
    ]

    # Total Time Played
    total_time_query = db.query(func.sum(Match.round_end_unix - Match.round_start_unix)).filter(Match.round_end_unix > 0).scalar() or 0
    total_time_played_s = int(total_time_query)

    # Top 5 MVPs
    top_mvps_query = (
        db.query(Player.display_name, Player.guid, func.count(Match.id).label("mvp_count"))
        .join(Match, Player.id == Match.mvp_player_id)
        .group_by(Player.id)
        .order_by(func.count(Match.id).desc())
        .limit(5)
        .all()
    )
    top_mvps = [{"name": n, "guid": g, "count": c} for n, g, c in top_mvps_query]

    # Total Kills
    total_kills = db.query(func.sum(PlayerMatchStats.kills)).filter(PlayerMatchStats.round_index == 0).scalar() or 0
    
    # Total Damage
    total_damage = db.query(func.sum(PlayerMatchStats.damage_given)).filter(PlayerMatchStats.round_index == 0).scalar() or 0

    # Matches by Day (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    thirty_days_ago_unix = int(thirty_days_ago.timestamp())
    
    matches_by_day_query = (
        db.query(
            func.date(func.datetime(Match.round_start_unix, 'unixepoch')).label("day"), 
            func.count(Match.id).label("count")
        )
        .filter(Match.round_start_unix >= thirty_days_ago_unix)
        .group_by(func.date(func.datetime(Match.round_start_unix, 'unixepoch')))
        .all()
    )
    
    # Fill in zeros for days with no matches
    matches_map = {day: count for day, count in matches_by_day_query}
    matches_by_day = []
    for i in range(31):
        day_date = (thirty_days_ago + timedelta(days=i)).date().isoformat()
        matches_by_day.append({
            "day": day_date,
            "count": matches_map.get(day_date, 0)
        })

    # Total Performaces (Player-Match summaries)
    total_performances = db.query(func.count(PlayerMatchStats.id)).filter(PlayerMatchStats.round_index == 0).scalar() or 0

    return {
        "total_matches": total_matches,
        "total_players": total_players,
        "total_performances": total_performances,
        "top_maps": top_maps,
        "top_players": top_players,
        "top_mvps": top_mvps,
        "recent_matches": recent_matches,
        "total_kills": int(total_kills),
        "total_damage": int(total_damage),
        "total_time_played_s": total_time_played_s,
        "matches_by_day": matches_by_day,
    }
