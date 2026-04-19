import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, defer
from sqlalchemy import func

from app.database import get_db
from app.models import Player, PlayerAlias, PlayerGatherRating, PlayerGatherRatingHistory, PlayerMatchStats
from app.schemas import PlayerProfileOut, PlayerSearchResultsOut, PlayerSearchEntryOut
from app.utils import record_slow_query

router = APIRouter(prefix="/api/players", tags=["players"])


# Map raw weapon IDs and legacy string names to centralized Groups
WEAPON_GROUP_MAP = {
    # SMGs
    "WS_MP40": "SMG", "MP40": "SMG", "MP-40": "SMG",
    "WS_THOMPSON": "SMG", "THOMPSON": "SMG",
    "WS_STEN": "SMG", "STEN": "SMG",
    "WS_MP34": "SMG", "MP34": "SMG",
    
    # Rifles (Semi & Bolt)
    "WS_KAR98": "Rifle", "KAR98": "Rifle", "KAR98 (AXIS)": "Rifle", "WS_KAR98_ALT": "Rifle",
    "WS_GARAND": "Rifle", "GARAND": "Rifle",
    "WS_K43": "Rifle", "K43": "Rifle",
    "WS_CARBINE": "Rifle", "CARBINE": "Rifle", "M1 CARBINE": "Rifle", "CARBINE (ALLIED)": "Rifle",
    "WS_RIFLE": "Rifle", "RIFLE": "Rifle",
    
    # Snipers
    "WS_FG42": "Sniper", "FG42": "Sniper",
    "K43 SCOPE": "Sniper", "GARAND SCOPE": "Sniper",
    
    # Pistols
    "WS_LUGER": "Pistol", "LUGER": "Pistol",
    "WS_COLT": "Pistol", "COLT": "Pistol",
    
    # Hand Grenades
    "WS_GRENADE": "Hand Grenade", "HAND GRENADE": "Hand Grenade", "GRENADE": "Hand Grenade",
    
    # Rifle Grenades
    "WS_GRENADELAUNCHER": "Rifle Grenade", "GRENADE LAUNCHER": "Rifle Grenade",
    "WS_RIFLE_GRENADE": "Rifle Grenade", "RIFLE GRENADE": "Rifle Grenade",
    
    # Heavy Weapons
    "WS_PANZERFAUST": "Heavy", "PANZERFAUST": "Heavy",
    "WS_BAZOOKA": "Heavy", "BAZOOKA": "Heavy",
    "WS_FLAMETHROWER": "Heavy", "FLAMETHROWER": "Heavy",
    "WS_MORTAR": "Heavy", "MORTAR": "Heavy", "WS_MORTAR2": "Heavy",
    
    # MGs
    "WS_MG42": "MG", "MG42": "MG",
    "WS_BROWNING": "MG", "BROWNING": "MG",

    # Support Strikes
    "WS_AIRSTRIKE": "Air/Artillery", "AIRSTRIKE": "Air/Artillery",
    "WS_ARTILLERY": "Air/Artillery", "ARTILLERY": "Air/Artillery",
    
    # Explosives
    "WS_DYNAMITE": "Dynamite", "DYNAMITE": "Dynamite",
    "WS_SATCHEL": "Satchel", "SATCHEL": "Satchel",
    "WS_LANDMINE": "Landmine", "LANDMINE": "Landmine",
    
    # Melee
    "WS_KNIFE": "Knife", "KNIFE": "Knife", "WS_KNIFE_KBAR": "Knife", "KNIFE (KBAR)": "Knife", "WS_KNIFE_ALT": "Knife",
    
    # Hidden / Support (mapped to None will be filtered out)
    "WS_SYRINGE": None, "SYRINGE": None, "SYRINGE (REVIVES) / REVIVES": None, "SYRINGE (REVIVES)": None,
    "WS_MEDKIT": None, "MEDKIT": None, "LANDMINE / MEDKIT": None, "WS_MEDKIT_ALT": None,
    "WS_MEDPACK": None, "MEDPACK": None, "AMMOPACK": None, "WS_AMMOPACK": None, "CARBINE (ALLIED) / AMMO": None,
    "WS_NONE": None, "NONE": None, "UNKNOWN": None
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
            raw_key = str(w.get("name") or w.get("slot")).strip().upper()
            display_name = WEAPON_GROUP_MAP.get(raw_key, raw_key)
            
            # Skip hidden categories (Syringes, Medkits)
            if display_name is None:
                continue

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
        # Accuracy normalization: cap at 100% just in case of weird legacy data
        pct = min(100.0, round(100.0 * hits / shots, 2)) if shots > 0 else 0.0
        out.append({**v, "accuracy": pct})
    
    # Sort by impact (Kills) then Accuracy
    out.sort(key=lambda x: (-(int(x["kills"])), -(x["accuracy"] or 0)))
    return out[:15] # Return top 15 groups


@router.get("", response_model=PlayerSearchResultsOut)
def search_players(q: str = "", skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    from sqlalchemy import desc
    from app.services.player_stats import get_player_ratings_and_roles
    
    # Base query for players
    query = db.query(Player).join(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
    if q:
        query = query.filter(Player.display_name.ilike(f"%{q}%"))
    
    # Get total count before pagination
    total_count = query.count()
    
    # Get the page of results
    players = query.order_by(desc(PlayerGatherRating.current_rating)).offset(skip).limit(limit).all()
    
    if not players:
        return PlayerSearchResultsOut(players=[], total=total_count)
    
    # Fetch roles for this specific set of players
    guids = [p.guid for p in players]
    _, roles_map = get_player_ratings_and_roles(db, guids)
    
    out_players = []
    for p in players:
        out_players.append(PlayerSearchEntryOut(
            guid=p.guid,
            display_name=p.display_name,
            raw_name=p.raw_name_last,
            val=round(p.gather_rating.current_rating, 1) if p.gather_rating else 1500.0,
            main_role=roles_map.get(p.guid.upper(), "Unknown")
        ))
        
    return PlayerSearchResultsOut(players=out_players, total=total_count)


@router.get("/leaderboards")
def leaderboards(db: Session = Depends(get_db)):
    from sqlalchemy import text
    
    start_time = time.time()
    
    openskill_top = (
        db.query(Player.guid, Player.display_name, Player.raw_name_last, PlayerGatherRating.current_rating)
        .join(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
        .order_by(PlayerGatherRating.current_rating.desc())
        .limit(10)
        .all()
    )
    
    medic_stats = (
        db.query(Player.guid, Player.display_name, Player.raw_name_last, func.avg(PlayerMatchStats.revives).label("val"))
        .join(PlayerMatchStats, Player.id == PlayerMatchStats.player_id)
        .filter(PlayerMatchStats.round_index == 0)
        .group_by(Player.id)
        .having(func.count(PlayerMatchStats.id) >= 3)
        .order_by(func.avg(PlayerMatchStats.revives).desc())
        .limit(10)
        .all()
    )

    killer_stats = (
        db.query(Player.guid, Player.display_name, Player.raw_name_last, func.avg(PlayerMatchStats.kills).label("val"))
        .join(PlayerMatchStats, Player.id == PlayerMatchStats.player_id)
        .filter(PlayerMatchStats.round_index == 0)
        .group_by(Player.id)
        .having(func.count(PlayerMatchStats.id) >= 3)
        .order_by(func.avg(PlayerMatchStats.kills).desc())
        .limit(10)
        .all()
    )

    undertaker_stats = (
        db.query(Player.guid, Player.display_name, Player.raw_name_last, func.avg(PlayerMatchStats.gibs).label("val"))
        .join(PlayerMatchStats, Player.id == PlayerMatchStats.player_id)
        .filter(PlayerMatchStats.round_index == 0)
        .group_by(Player.id)
        .having(func.count(PlayerMatchStats.id) >= 3)
        .order_by(func.avg(PlayerMatchStats.gibs).desc())
        .limit(10)
        .all()
    )
    
    # True Mathematical Accuracy (SUM(Headshots) / SUM(Shots))
    ss_query_text = """
        SELECT 
            p.guid, p.display_name, p.raw_name_last, 
            (SUM(CAST(json_extract(weap.value, '$.headshots') AS FLOAT)) / SUM(CAST(json_extract(weap.value, '$.shots') AS FLOAT))) * 100.0 as val
        FROM player_match_stats pms
        JOIN players p ON p.id = pms.player_id, 
             json_each(pms.weapon_breakdown_json) weap
        WHERE pms.round_index = 0 AND pms.weapon_breakdown_json IS NOT NULL
        GROUP BY pms.player_id
        HAVING SUM(CAST(json_extract(weap.value, '$.shots') AS INTEGER)) >= 500
        ORDER BY val DESC
        LIMIT 10
    """
    ss_stats = db.execute(text(ss_query_text)).fetchall()

    # SMG Accuracy (slot 4,5,6,26)
    smg_query_text = """
        SELECT 
            p.guid, p.display_name, p.raw_name_last, 
            (SUM(CAST(json_extract(weap.value, '$.hits') AS FLOAT)) / SUM(CAST(json_extract(weap.value, '$.shots') AS FLOAT))) * 100.0 as val
        FROM player_match_stats pms
        JOIN players p ON p.id = pms.player_id, 
             json_each(pms.weapon_breakdown_json) weap
        WHERE pms.round_index = 0 
          AND pms.weapon_breakdown_json IS NOT NULL
          AND CAST(json_extract(weap.value, '$.slot') AS INTEGER) IN (4, 5, 6, 26)
        GROUP BY pms.player_id
        HAVING SUM(CAST(json_extract(weap.value, '$.shots') AS INTEGER)) >= 500
        ORDER BY val DESC
        LIMIT 10
    """
    smg_stats = db.execute(text(smg_query_text)).fetchall()

    duration = time.time() - start_time
    record_slow_query("leaderboards", duration, "fetch")

    return {
        "openskill": [{"guid": r.guid, "display_name": r.display_name, "raw_name": r.raw_name_last, "val": round(r.current_rating, 1)} for r in openskill_top],
        "medic": [{"guid": r.guid, "display_name": r.display_name, "raw_name": r.raw_name_last, "val": round(r.val or 0, 1)} for r in medic_stats],
        "sharpshooter": [{"guid": r.guid, "display_name": r.display_name, "raw_name": r.raw_name_last, "val": round(r.val or 0, 1)} for r in ss_stats],
        "killer": [{"guid": r.guid, "display_name": r.display_name, "raw_name": r.raw_name_last, "val": round(r.val or 0, 1)} for r in killer_stats],
        "undertaker": [{"guid": r.guid, "display_name": r.display_name, "raw_name": r.raw_name_last, "val": round(r.val or 0, 1)} for r in undertaker_stats],
        "accuracy_smg": [{"guid": r.guid, "display_name": r.display_name, "raw_name": r.raw_name_last, "val": round(r.val or 0, 1)} for r in smg_stats],
    }


@router.get("/{guid}", response_model=PlayerProfileOut)
def player_profile(
    guid: str, 
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20
) -> dict[str, Any]:
    start_time = time.time()
    g = guid.strip().upper()
    pl = db.query(Player).filter(Player.guid == g).one_or_none()
    
    if not pl:
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

    # 1. SQL-Level Aggregation for Lifetime Stats
    lifetime_row = db.query(
        func.sum(PlayerMatchStats.kills).label("kills"),
        func.sum(PlayerMatchStats.deaths).label("deaths"),
        func.sum(PlayerMatchStats.damage_given).label("damage_given"),
        func.sum(PlayerMatchStats.damage_received).label("damage_received"),
        func.sum(PlayerMatchStats.headshots).label("headshots"),
        func.sum(PlayerMatchStats.gibs).label("gibs"),
        func.sum(PlayerMatchStats.self_kills).label("self_kills"),
        func.sum(PlayerMatchStats.team_kills).label("team_kills"),
        func.sum(PlayerMatchStats.revives).label("revives"),
        func.avg(PlayerMatchStats.eff).label("avg_eff"),
        func.count(PlayerMatchStats.id).label("match_count")
    ).filter(
        PlayerMatchStats.player_id == pl.id, 
        PlayerMatchStats.round_index == 0
    ).first()

    total_matches = lifetime_row.match_count if lifetime_row and lifetime_row.match_count else 0

    lifetime = {
        "kills": lifetime_row.kills or 0,
        "deaths": lifetime_row.deaths or 0,
        "damage_given": lifetime_row.damage_given or 0,
        "damage_received": lifetime_row.damage_received or 0,
        "headshots": lifetime_row.headshots or 0,
        "gibs": lifetime_row.gibs or 0,
        "self_kills": lifetime_row.self_kills or 0,
        "team_kills": lifetime_row.team_kills or 0,
        "revives": lifetime_row.revives or 0,
        "avg_eff": round(lifetime_row.avg_eff or 0.0, 1) if lifetime_row.avg_eff is not None else 0.0
    }
    
    # 2. Selective JSON loading for weapons, nemesis, and classes
    # We only load the JSON columns, avoiding the rest of the massive ORM object
    json_rows = db.query(
        PlayerMatchStats.weapon_breakdown_json,
        PlayerMatchStats.nemesis_json,
        PlayerMatchStats.classes_played_json,
        PlayerMatchStats.round_index
    ).filter(PlayerMatchStats.player_id == pl.id).all()
    
    # We still need a duck-typed object for _aggregate_weapons to consume
    class MockPMS:
        def __init__(self, wjson):
            self.weapon_breakdown_json = wjson

    summary_pms_list = [MockPMS(r.weapon_breakdown_json) for r in json_rows if r.round_index == 0 and r.weapon_breakdown_json]
    top_weapons = _aggregate_weapons(summary_pms_list)

    nemesis_counts = {}
    killed_by_counts = {}
    for r in json_rows:
        if r.nemesis_json:
            try:
                nj = json.loads(r.nemesis_json)
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

    class_stats = {
        "soldier": 0, "medic": 0, "engineer": 0, "fieldop": 0, "covertops": 0
    }
    
    for r in json_rows:
        if r.round_index == 0 and r.classes_played_json:
            try:
                classes = json.loads(r.classes_played_json)
                unique_match_classes = {c["toClass"] for c in classes if "toClass" in c}
                for cname in unique_match_classes:
                    cname_lower = cname.lower()
                    if cname_lower in class_stats:
                        class_stats[cname_lower] += 1
            except: pass

    # Get aliases and normalize them
    from app.parsers.names import strip_quake_colors, normalize_nick
    
    # Sort by ID or last_seen to get the most recent aliases logically
    alias_rows = (
        db.query(PlayerAlias.alias)
        .filter(PlayerAlias.player_id == pl.id)
        .order_by(PlayerAlias.last_seen.desc())
        .limit(100)
        .all()
    )
    
    unique_aliases = []
    seen = set()
    for row in alias_rows:
        # Group by normalized identity
        normal = normalize_nick(row.alias)
        lower_norm = normal.lower()
        if lower_norm not in seen and len(lower_norm) > 1:
            seen.add(lower_norm)
            # We show the original alias string for this identity (it's the most recent one due to the sort order)
            unique_aliases.append(row.alias)
            if len(unique_aliases) >= 10:
                break
                
    aliases = unique_aliases

    # Optimized history query: join with Match and RatingHistory
    recent_pms = (
        db.query(
            PlayerMatchStats.team, PlayerMatchStats.kills, PlayerMatchStats.deaths, PlayerMatchStats.xp,
            Match.id, Match.mapname, Match.winner_team, Match.round_start_unix,
            PlayerGatherRatingHistory.delta
        )
        .join(Match, Match.id == PlayerMatchStats.match_id)
        .outerjoin(PlayerGatherRatingHistory, (PlayerGatherRatingHistory.player_id == PlayerMatchStats.player_id) & (PlayerGatherRatingHistory.match_id == PlayerMatchStats.match_id))
        .filter(PlayerMatchStats.player_id == pl.id, PlayerMatchStats.round_index == 0)
        .order_by(Match.round_start_unix.desc())
        .offset(skip)
        .limit(min(limit, 100))
        .all()
    )
    
    match_history = []
    for r in recent_pms:
        match_history.append({
            "id": r.id,
            "mapname": r.mapname,
            "team": r.team,
            "winner_team": r.winner_team,
            "kills": r.kills,
            "deaths": r.deaths,
            "xp": r.xp,
            "timestamp": r.round_start_unix,
            "sr_delta": r.delta,
        })

    duration = time.time() - start_time
    record_slow_query("player_profile", duration, f"guid={pl.guid}")

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
        "class_stats": class_stats,
    }
