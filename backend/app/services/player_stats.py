from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Tuple
from app.models import Player, PlayerGatherRating, PlayerMatchStats
from collections import Counter
import json

def get_player_ratings_and_roles(db: Session, guids: List[str]) -> Tuple[Dict[str, float], Dict[str, str]]:
    """
    Fetches SR ratings and calculates the dominant role for a list of GUIDs.
    Returns: (ratings_map, roles_map)
    """
    from app.services.aliases import resolve_guid
    
    # Resolve all input GUIDs to Master GUIDs for consistent DB lookup
    found_guids = [resolve_guid(g).upper() for g in guids if g]
    
    if not found_guids:
        return {}, {}

    # 1. Fetch ratings
    db_ratings = (
        db.query(Player.guid, PlayerGatherRating.current_rating)
        .join(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
        .filter(Player.guid.in_(found_guids))
        .all()
    )
    ratings_map = {guid.upper(): rating for guid, rating in db_ratings}

    # 2. Fetch stats for role calculation
    stats_rows = (
        db.query(Player.guid, PlayerMatchStats.classes_played_json, PlayerMatchStats.weapon_breakdown_json)
        .join(Player, Player.id == PlayerMatchStats.player_id)
        .filter(Player.guid.in_(found_guids))
        .order_by(desc(PlayerMatchStats.id))
        .limit(1000) # Bulk fetch recent stats
        .all()
    )

    player_class_times = {} 
    player_weapon_kills = {}
    
    RIFLE_WEAPONS = {"WS_K43", "WS_GARAND", "WS_KAR98", "WS_M1_GARAND", "WS_K43_RIFLE", "WS_SVT40", "WS_GPG40", "WS_M7"}
    SMG_WEAPONS = {"WS_THOMPSON", "WS_MP40", "WS_STEN"}

    for guid, classes_json, weapons_json in stats_rows:
        guid = guid.upper()
        if guid not in player_class_times:
            player_class_times[guid] = Counter()
            player_weapon_kills[guid] = Counter()

        if classes_json:
            try:
                classes = json.loads(classes_json)
                classes.sort(key=lambda x: x.get('timestamp', 0))
                for i, c in enumerate(classes):
                    class_name = c.get('toClass', 'unknown').lower()
                    start_time = c.get('timestamp', 0)
                    duration = max(0, classes[i+1].get('timestamp', 0) - start_time) if i + 1 < len(classes) else 600
                    player_class_times[guid][class_name] += duration
            except: pass

        if weapons_json:
            try:
                weapons = json.loads(weapons_json)
                for w in weapons:
                    w_name = w.get('name', '')
                    kills = w.get('kills', 0)
                    if w_name in RIFLE_WEAPONS or w_name in SMG_WEAPONS:
                        player_weapon_kills[guid][w_name] += kills
            except: pass

    roles_map = {}
    for guid, counts in player_class_times.items():
        if not counts: continue
        
        weighted_counts = Counter(counts)
        weighted_counts['engineer'] = int(weighted_counts['engineer'] * 1.5)
        weighted_counts['fieldop'] = int(weighted_counts['fieldop'] * 1.3)
        
        top_class = weighted_counts.most_common(1)[0][0]
        role = "Medic" 
        if top_class == "medic": role = "Medic"
        elif top_class == "fieldop": role = "Field Ops"
        elif top_class == "engineer":
            w_kills = player_weapon_kills.get(guid, Counter())
            role = "Rifle/Eng" if sum(w_kills[w] for w in RIFLE_WEAPONS) > sum(w_kills[w] for w in SMG_WEAPONS) else "Engineer"
        
        roles_map[guid] = role

    return ratings_map, roles_map
