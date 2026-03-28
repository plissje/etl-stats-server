import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Player, PlayerGatherRating, PlayerGatherRatingHistory, PlayerMatchStats
from app.schemas import PlayerProfileOut

router = APIRouter(prefix="/api/players", tags=["players"])


WEAPON_NAME_MAP = {
    "WS_KNIFE": "Knife",
    "WS_KNIFE_KBAR": "K-Bar",
    "WS_LUGER": "Luger",
    "WS_COLT": "Colt",
    "WS_MP40": "MP40",
    "WS_THOMPSON": "Thompson",
    "WS_STEN": "Sten",
    "WS_FG42": "FG42",
    "WS_PANZERFAUST": "Panzerfaust",
    "WS_BAZOOKA": "Bazooka",
    "WS_FLAMETHROWER": "Flamethrower",
    "WS_GRENADE": "Grenade",
    "WS_MORTAR": "Mortar",
    "WS_MORTAR2": "Mortar",
    "WS_DYNAMITE": "Dynamite",
    "WS_AIRSTRIKE": "Airstrike",
    "WS_ARTILLERY": "Artillery",
    "WS_SATCHEL": "Satchel",
    "WS_GRENADELAUNCHER": "Grenade Launcher",
    "WS_LANDMINE": "Landmine",
    "WS_MG42": "MG42",
    "WS_BROWNING": "Browning",
    "WS_CARBINE": "M1 Carbine",
    "WS_KAR98": "Kar98",
    "WS_GARAND": "Garand",
    "WS_K43": "K43",
    "WS_MP34": "MP34",
    "WS_SYRINGE": "Syringe",
}

def _aggregate_weapons(stats_rows: list[PlayerMatchStats]) -> list[dict[str, Any]]:
    acc: dict[str, dict[str, float | int | str | None]] = {}
    for pms in stats_rows:
        if not pms.weapon_breakdown_json:
            continue
        try:
            parts = json.loads(pms.weapon_breakdown_json)
        except json.JSONDecodeError:
            continue
        for w in parts:
            raw_key = str(w.get("name") or w.get("slot"))
            display_name = WEAPON_NAME_MAP.get(raw_key, raw_key)
            
            if display_name not in acc:
                acc[display_name] = {
                    "name": display_name,
                    "hits": 0,
                    "shots": 0,
                    "kills": 0,
                    "headshots": 0,
                }
            acc[display_name]["hits"] += int(w.get("hits") or 0)
            acc[display_name]["shots"] += int(w.get("shots") or 0)
            acc[display_name]["kills"] += int(w.get("kills") or 0)
            acc[display_name]["headshots"] += int(w.get("headshots") or 0)
    out = []
    for v in acc.values():
        shots = int(v["shots"])
        hits = int(v["hits"])
        pct = round(100.0 * hits / shots, 2) if shots > 0 else None
        out.append({**v, "accuracy_pct": pct})
    out.sort(key=lambda x: (-(x["accuracy_pct"] or 0), -int(x["kills"])))
    return out[:12]


@router.get("")
def search_players(q: str = "", skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    from sqlalchemy import desc
    query = db.query(Player.guid, Player.display_name, Player.raw_name_last, PlayerGatherRating.current_rating) \
              .join(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
    if q:
        query = query.filter(Player.display_name.ilike(f"%{q}%"))
    query = query.order_by(desc(PlayerGatherRating.current_rating)).offset(skip).limit(limit)
    rows = query.all()
    return [{"guid": r.guid, "display_name": r.display_name, "raw_name": r.raw_name_last, "val": round(r.current_rating, 1)} for r in rows]


@router.get("/leaderboards")
def leaderboards(db: Session = Depends(get_db)):
    openskill_top = (
        db.query(Player, PlayerGatherRating)
        .join(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
        .order_by(PlayerGatherRating.current_rating.desc())
        .limit(10)
        .all()
    )
    
    medic_stats = (
        db.query(Player, func.avg(PlayerMatchStats.revives))
        .join(PlayerMatchStats, Player.id == PlayerMatchStats.player_id)
        .group_by(Player.id)
        .having(func.count(PlayerMatchStats.id) >= 3)
        .order_by(func.avg(PlayerMatchStats.revives).desc())
        .limit(10)
        .all()
    )
    
    ss_stats = (
        db.query(Player, func.avg(PlayerMatchStats.hs_accuracy_event))
        .join(PlayerMatchStats, Player.id == PlayerMatchStats.player_id)
        .group_by(Player.id)
        .having(func.count(PlayerMatchStats.id) >= 3)
        .order_by(func.avg(PlayerMatchStats.hs_accuracy_event).desc())
        .limit(10)
        .all()
    )

    return {
        "openskill": [{"guid": pl.guid, "display_name": pl.display_name, "raw_name": pl.raw_name_last, "val": round(gr.current_rating, 1)} for pl, gr in openskill_top],
        "medic": [{"guid": pl.guid, "display_name": pl.display_name, "raw_name": pl.raw_name_last, "val": revives or 0} for pl, revives in medic_stats],
        "sharpshooter": [{"guid": pl.guid, "display_name": pl.display_name, "raw_name": pl.raw_name_last, "val": round(avg_hs or 0, 1)} for pl, avg_hs in ss_stats],
    }


@router.get("/{guid}", response_model=PlayerProfileOut)
def player_profile(guid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    g = guid.strip().upper()
    print(f"DEBUG: player_profile for guid='{g}' (original='{guid}')")
    pl = db.query(Player).filter(Player.guid == g).one_or_none()
    
    if not pl:
        print(f"DEBUG: player not found in DB for guid='{g}'")
        raise HTTPException(404, "player not found")

    gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == pl.id).one_or_none()
    rating = gr.current_rating if gr else 1500.0

    from app.models import Match
    mvp_count = db.query(Match).filter(Match.mvp_player_id == pl.id).count()

    hist = (
        db.query(PlayerGatherRatingHistory)
        .filter(PlayerGatherRatingHistory.player_id == pl.id)
        .order_by(PlayerGatherRatingHistory.recorded_at.asc())
        .all()
    )
    rating_history = [
        {
            "match_id": h.match_id,
            "rating": h.rating,
            "delta": h.delta,
            "recorded_at": h.recorded_at.isoformat(),
        }
        for h in hist
    ]

    pms_list = db.query(PlayerMatchStats).filter(PlayerMatchStats.player_id == pl.id).all()
    top_weapons = _aggregate_weapons(pms_list)

    nemesis_counts = {}
    killed_by_counts = {}
    for pms in pms_list:
        if pms.nemesis_json:
            try:
                nj = json.loads(pms.nemesis_json)
                for k, v in nj.get("kills", {}).items():
                    nemesis_counts[k] = nemesis_counts.get(k, 0) + v
                for k, v in nj.get("deaths", {}).items():
                    killed_by_counts[k] = killed_by_counts.get(k, 0) + v
            except: pass
            
    nemesis_out = {
        "killed_most": [{"guid": k, "count": v} for k, v in sorted(nemesis_counts.items(), key=lambda x: -x[1])[:5]],
        "killed_by_most": [{"guid": k, "count": v} for k, v in sorted(killed_by_counts.items(), key=lambda x: -x[1])[:5]],
    }
    
    all_guids = {x["guid"] for x in nemesis_out["killed_most"]} | {x["guid"] for x in nemesis_out["killed_by_most"]}
    if all_guids:
        name_map = dict(db.query(Player.guid, Player.display_name).filter(Player.guid.in_(all_guids)).all())
        for row in nemesis_out["killed_most"]:
            row["name"] = name_map.get(row["guid"], row["guid"][:8])
        for row in nemesis_out["killed_by_most"]:
            row["name"] = name_map.get(row["guid"], row["guid"][:8])

    # Calculate lifetime stats (totals)
    tr_list = [pms for pms in pms_list if pms.round_index == 0]
    lifetime = {
        "kills": sum(tr.kills for tr in tr_list),
        "deaths": sum(tr.deaths for tr in tr_list),
        "damage_given": sum(tr.damage_given for tr in tr_list),
        "damage_received": sum(tr.damage_received for tr in tr_list),
        "headshots": sum(tr.headshots for tr in tr_list),
        "gibs": sum(tr.gibs for tr in tr_list),
        "self_kills": sum(tr.self_kills for tr in tr_list),
        "team_kills": sum(tr.team_kills for tr in tr_list),
        "revives": sum(tr.revives for tr in tr_list),
        "avg_eff": round(sum(tr.eff for tr in tr_list) / len(tr_list), 1) if tr_list else 0
    }

    # Get aliases
    from app.models import PlayerAlias
    alias_rows = db.query(PlayerAlias).filter(PlayerAlias.player_id == pl.id).all()
    aliases = list({a.alias for a in alias_rows})

    # Get total matches and recent match history
    from app.models import Match
    total_matches = db.query(func.count(PlayerMatchStats.id)).filter(PlayerMatchStats.player_id == pl.id, PlayerMatchStats.round_index == 0).scalar() or 0
    
    recent_pms = (
        db.query(PlayerMatchStats, Match)
        .join(Match, Match.id == PlayerMatchStats.match_id)
        .filter(PlayerMatchStats.player_id == pl.id, PlayerMatchStats.round_index == 0)
        .order_by(Match.round_start_unix.desc())
        .limit(50)
        .all()
    )
    
    match_history = []
    for pms, m in recent_pms:
        match_history.append({
            "id": m.id,
            "mapname": m.mapname,
            "team": pms.team,
            "winner_team": m.winner_team,
            "kills": pms.kills,
            "deaths": pms.deaths,
            "xp": pms.xp,
            "timestamp": m.round_start_unix,
        })

    return {
        "guid": pl.guid,
        "display_name": pl.display_name,
        "raw_name": pl.raw_name_last,
        "current_rating": rating,
        "mvp_count": mvp_count,
        "rating_history": rating_history,
        "top_weapons": top_weapons,
        "nemesis": nemesis_out,
        "aliases": aliases,
        "total_matches": total_matches,
        "match_history": match_history,
        "lifetime_stats": lifetime,
    }
