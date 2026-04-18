import time
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session, defer, joinedload
from collections import defaultdict

from app.database import get_db
from app.models import Match, Player, PlayerMatchStats
from app.schemas import MatchDetailOut, MatchSummaryOut, PlayerMatchRowOut
from app.utils import record_slow_query

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _row(pms: PlayerMatchStats, pl: Player) -> PlayerMatchRowOut:
    wb = None
    if pms.weapon_breakdown_json:
        try:
            wb = json.loads(pms.weapon_breakdown_json)
        except json.JSONDecodeError:
            pass

    return PlayerMatchRowOut(
        player_guid=pl.guid,
        name_display=pl.display_name,
        name_raw=pms.name_raw,
        team=pms.team,
        eff=pms.eff,
        unified_eff=pms.unified_eff,
        kdr=pms.kdr,
        kills=pms.kills,
        deaths=pms.deaths,
        damage_given=pms.damage_given,
        damage_received=pms.damage_received,
        headshots=pms.headshots,
        gibs=pms.gibs,
        revives=pms.revives,
        medkits=pms.medkits,
        team_medpacks=pms.team_medpacks,
        spam_kills=pms.spam_kills,
        distance_travelled_meters=pms.distance_travelled_meters,
        distance_travelled_spawn_avg=pms.distance_travelled_spawn_avg,
        crouched_seconds=pms.crouched_seconds,
        proned_seconds=pms.proned_seconds,
        leaned_seconds=pms.leaned_seconds,
        classes_played=json.loads(pms.classes_played_json) if pms.classes_played_json else [],
        time_played_pct=pms.time_played_pct,
        team_kills=pms.team_kills,
        team_damage_given=pms.team_damage_given,
        team_gibs=pms.team_gibs,
        self_kills=pms.self_kills,
        xp=pms.xp,
        weapon_breakdown=wb,
    )


@router.get("", response_model=list[MatchSummaryOut])
def list_matches(
    skip: int = 0, 
    limit: int = 50, 
    mapname: Optional[str] = None,
    player_name: Optional[str] = None,
    from_date: Optional[int] = None,
    to_date: Optional[int] = None,
    db: Session = Depends(get_db),
    response: Response = None
) -> list[MatchSummaryOut]:
    start_time = time.time()
    
    # Base query with filters
    q = db.query(Match)
    if mapname:
        q = q.filter(Match.mapname == mapname)
    if from_date:
        q = q.filter(Match.round_start_unix >= from_date)
    if to_date:
        q = q.filter(Match.round_start_unix <= to_date)
    if player_name:
        q = q.join(PlayerMatchStats).join(Player).filter(Player.display_name.ilike(f"%{player_name}%")).distinct()
    
    # Get total count for pagination headers
    total_count = q.count()
    if response:
        response.headers["X-Total-Count"] = str(total_count)
        # Expose header for cross-origin frontend
        response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    
    # Final query with defer, joinedload and pagination
    q = q.options(defer(Match.raw_payload), joinedload(Match.mvp_player))
    q = q.order_by(Match.round_start_unix.desc()).offset(skip).limit(min(limit, 200))
    matches = q.all()
    
    if not matches:
        return []

    # Batch fetch all players and stats for the entire page in one join query (Fixes N+1)
    # Only load required columns to avoid fetching massive JSON strings in PlayerMatchStats
    match_ids = [m.id for m in matches]
    player_rows = (
        db.query(
            PlayerMatchStats.match_id, 
            PlayerMatchStats.team, 
            PlayerMatchStats.eff, 
            PlayerMatchStats.xp, 
            Player.display_name
        )
        .join(Player, Player.id == PlayerMatchStats.player_id)
        .filter(PlayerMatchStats.match_id.in_(match_ids))
        .filter(PlayerMatchStats.round_index == 0)
        .all()
    )
    
    # Group results by match_id for O(1) lookup in the loop below
    players_by_match = defaultdict(list)
    for row in player_rows:
        players_by_match[row.match_id].append(row)
    
    out = []
    for m in matches:
        m_players = players_by_match[m.id]
        axis_names = []
        allies_names = []
        mvp_name = None
        best_score = -1.0

        for row in m_players:
            if row.team == 1:
                axis_names.append(row.display_name)
            elif row.team == 2:
                allies_names.append(row.display_name)
            
            # Team-agnostic MVP logic: highest score overall
            score = row.eff + (row.xp / 10.0)
            if m.winner_team > 0 and row.team == m.winner_team:
                score += 0.01
                
            if score > best_score:
                best_score = score
                mvp_name = row.display_name

        out.append(MatchSummaryOut(
            id=m.id,
            match_id=m.match_id,
            mapname=m.mapname,
            winner_team=m.winner_team,
            round_start_unix=m.round_start_unix,
            round_end_unix=m.round_end_unix,
            axis_players=sorted(axis_names),
            allies_players=sorted(allies_names),
            mvp_name=m.mvp_player.display_name if m.mvp_player else mvp_name,
            mvp_guid=m.mvp_player.guid if m.mvp_player else None,
        ))

    duration = time.time() - start_time
    record_slow_query("list_matches", duration, f"count={len(matches)}")
    
    return out


@router.get("/{match_db_id}", response_model=MatchDetailOut)
def match_detail(match_db_id: int, db: Session = Depends(get_db)) -> MatchDetailOut:
    m = db.query(Match).options(defer(Match.raw_payload)).filter(Match.id == match_db_id).one_or_none()
    if not m:
        raise HTTPException(404, "match not found")
    rows = (
        db.query(PlayerMatchStats, Player)
        .join(Player, Player.id == PlayerMatchStats.player_id)
        .filter(PlayerMatchStats.match_id == m.id)
        .all()
    )
    axis, allies = [], []
    axis_round1, allies_round1 = [], []
    axis_round2, allies_round2 = [], []
    for pms, pl in rows:
        r = _row(pms, pl)
        if pms.round_index == 0:
            if pms.team == 1: axis.append(r)
            else: allies.append(r)
        elif pms.round_index == 1:
            if pms.team == 1: axis_round1.append(r)
            else: allies_round1.append(r)
        elif pms.round_index == 2:
            if pms.team == 1: axis_round2.append(r)
            else: allies_round2.append(r)

    axis.sort(key=lambda x: (-x.unified_eff, x.name_display.lower()))
    allies.sort(key=lambda x: (-x.unified_eff, x.name_display.lower()))
    axis_round1.sort(key=lambda x: (-x.unified_eff, x.name_display.lower()))
    allies_round1.sort(key=lambda x: (-x.unified_eff, x.name_display.lower()))
    axis_round2.sort(key=lambda x: (-x.unified_eff, x.name_display.lower()))
    allies_round2.sort(key=lambda x: (-x.unified_eff, x.name_display.lower()))

    max_rivalry = None
    max_count = 0
    guid_to_name = {p.guid: p.display_name for _, p in rows}

    for pms, pl in rows:
        if not pms.nemesis_json:
            continue
        try:
            nj = json.loads(pms.nemesis_json)
            for victim_guid, count in nj.get("kills", {}).items():
                if count > max_count:
                    max_count = count
                    max_rivalry = {
                        "killer_guid": pl.guid,
                        "killer_name": pl.display_name,
                        "victim_guid": victim_guid,
                        "victim_name": guid_to_name.get(victim_guid, victim_guid[:8]),
                        "count": count
                    }
        except:
            pass

    # Team-agnostic MVP logic
    best_score = -1.0
    mvp = None
    for pms, pl in rows:
        if pms.round_index != 0: continue
        score = pms.eff + (pms.xp / 10.0)
        if m.winner_team > 0 and pms.team == m.winner_team:
            score += 0.01
        if score > best_score:
            best_score = score
            mvp = pl

    # Resolve Alpha/Beta side metadata
    # The rule is: Alpha started as Axis (Team 1) in Round 1, Beta as Allies (Team 2).
    # This is consistent for all matches to ensure stable history reconstruction.
    r1_alpha_side = 1 # Axis
    r2_alpha_side = 2 # Allies

    return MatchDetailOut(
        match=MatchSummaryOut(
            id=m.id,
            match_id=m.match_id,
            mapname=m.mapname,
            winner_team=m.winner_team,
            round_start_unix=m.round_start_unix,
            round_end_unix=m.round_end_unix,
            axis_players=[r.name_display for r in axis],
            allies_players=[r.name_display for r in allies],
            mvp_name=mvp.display_name if mvp else None,
        ),
        axis=axis,
        allies=allies,
        axis_round1=axis_round1,
        allies_round1=allies_round1,
        axis_round2=axis_round2,
        allies_round2=allies_round2,
        round1_alpha_side=r1_alpha_side,
        round2_alpha_side=r2_alpha_side,
        rivalry=max_rivalry
    )


@router.delete("/{match_db_id}")
def delete_match(match_db_id: int, db: Session = Depends(get_db)):
    m = db.query(Match).filter(Match.id == match_db_id).one_or_none()
    if not m:
        raise HTTPException(404, "match not found")
    
    db.delete(m)
    db.commit()
    return {"status": "deleted", "id": match_db_id}


@router.delete("/map/{mapname}")
def delete_matches_by_map(mapname: str, db: Session = Depends(get_db)):
    matches = db.query(Match).filter(Match.mapname == mapname).all()
    count = len(matches)
    for m in matches:
        db.delete(m)
    db.commit()
    return {"status": "deleted", "count": count, "map": mapname}
