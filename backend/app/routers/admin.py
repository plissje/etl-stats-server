import os
import glob
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Match, Player, PlayerAlias, PlayerMatchStats, PlayerGatherRating, PlayerGatherRatingHistory
from app.services.ingest import ingest_match_payloads, recalculate_all_ratings, load_aliases

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/reprocess")
def reprocess_matches(match_ids: Optional[List[int]] = None, db: Session = Depends(get_db)):
    """
    Reprocesses existing matches from their JSON source files.
    If match_ids is provided, only those database IDs are reprocessed.
    If None, all matches in the database are reprocessed.
    """
    if match_ids:
        matches = db.query(Match).filter(Match.id.in_(match_ids)).all()
    else:
        matches = db.query(Match).all()

    # Define potential candidate paths for the refs directory
    potential_roots = [
        "/app", # Primary path for Docker
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), # Local repo root (4 levels)
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), # Backend package root (3 levels)
        os.getcwd(), # Current working directory
        "/" # Absolute root fallback
    ]
    
    reprocessed_count = 0
    for m in matches:
        files = []
        for root in potential_roots:
            # Check root/refs/gamestats, root/refs, root/gamestats
            search_paths = [
                os.path.join(root, "refs", "gamestats"),
                os.path.join(root, "refs"),
                os.path.join(root, "gamestats")
            ]
            
            for path in search_paths:
                if not os.path.exists(path):
                    continue
                pattern = os.path.join(path, f"*-{m.match_id}-*.json")
                files = glob.glob(pattern)
                if files:
                    break
            if files:
                break
            
        if not files:
            print(f"Warning: No source files found for match_id {m.match_id} (DB ID: {m.id})")
            continue
        
        # Sort files by round if possible
        def get_round(f):
            try:
                name = os.path.basename(f)
                if "round-" in name:
                    return int(name.split("round-")[1].split(".")[0])
            except:
                pass
            return 0
        files.sort(key=get_round)
        
        payloads = []
        for f in files:
            try:
                with open(f, "r") as fp:
                    payloads.append(json.load(fp))
            except Exception as e:
                print(f"Error reading {f}: {e}")
        
        if payloads:
            print(f"Reprocessing match {m.match_id} with {len(payloads)} rounds...")
            ingest_match_payloads(db, payloads)
            reprocessed_count += 1
            
    # Always recalculate ratings after reprocessing to ensure consistency
    # This function processes ALL matches in the database chronologically.
    recalculate_all_ratings(db)
    total_matches = db.query(Match).count()
    
    return {
        "status": "ok", 
        "healed_from_json": reprocessed_count, 
        "total_recalculated_matches": total_matches
    }


@router.post("/consolidate")
def consolidate_aliases(db: Session = Depends(get_db)):
    """
    Globally consolidates the database by merging statistics from alias GUIDs
    into their master identity and purging redundant player records.
    """
    alias_map = load_aliases()
    if not alias_map:
        return {"status": "ok", "message": "No aliases to consolidate"}

    try:
        consolidated_count = 0
        # alias_map is {alias_guid: master_guid}
        
        # Track which masters we've seen to update their ratings at the end
        affected_masters = set()

        for alias_guid, master_guid in alias_map.items():
            master_player = db.query(Player).filter(Player.guid == master_guid).first()
            alias_player = db.query(Player).filter(Player.guid == alias_guid).first()

            if not master_player or not alias_player:
                continue
            
            if master_player.id == alias_player.id:
                continue

            print(f"DEBUG: Consolidating {alias_player.display_name} ({alias_guid}) -> {master_player.display_name} ({master_guid})")
            
            # 1. Update Match MVPs
            db.query(Match).filter(Match.mvp_player_id == alias_player.id).update(
                {"mvp_player_id": master_player.id}, synchronize_session=False
            )
            db.flush()

            # 2. Migrate PlayerAlias records
            db.query(PlayerAlias).filter(PlayerAlias.player_id == alias_player.id).update(
                {"player_id": master_player.id}, synchronize_session=False
            )
            db.flush()

            # 3. Migrate all PlayerMatchStats row-by-row
            alias_stats = db.query(PlayerMatchStats).filter(PlayerMatchStats.player_id == alias_player.id).all()
            for a_stat in alias_stats:
                m_stat = db.query(PlayerMatchStats).filter(
                    PlayerMatchStats.player_id == master_player.id,
                    PlayerMatchStats.match_id == a_stat.match_id,
                    PlayerMatchStats.round_index == a_stat.round_index
                ).first()

                if m_stat:
                    m_stat.kills += a_stat.kills
                    m_stat.deaths += a_stat.deaths
                    m_stat.xp += a_stat.xp
                    m_stat.damage_given += a_stat.damage_given
                    m_stat.damage_received += a_stat.damage_received
                    m_stat.headshots += a_stat.headshots
                    m_stat.revives += a_stat.revives
                    db.delete(a_stat)
                else:
                    a_stat.player_id = master_player.id
            db.flush()

            # 4. Purge alias ratings and history
            db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == alias_player.id).delete()
            db.query(PlayerGatherRatingHistory).filter(PlayerGatherRatingHistory.player_id == alias_player.id).delete()
            db.flush()
            
            # 5. Finally, delete the alias player record
            # Use direct delete on the object to ensure cascades/safeties
            db.delete(alias_player)
            db.flush()
            
            affected_masters.add(master_player.id)
            consolidated_count += 1

        db.commit()
    except Exception as e:
        db.rollback()
        import traceback
        print(f"CRITICAL CONSOLIDATION ERROR: {e}")
        print(traceback.format_exc())
        return {"status": "error", "message": f"Consolidation failed: {str(e)}"}

    # 4. Trigger full SR recalculation to ensure consistency
    recalculate_all_ratings(db)

    return {
        "status": "ok", 
        "consolidated_aliases": consolidated_count,
        "message": "Global consolidation and rating recalculation complete."
    }


@router.get("/aliases")
def get_aliases():
    # Use the same persistent path
    mapping_path = "/app/data/aliases.json"
    if not os.path.exists(mapping_path):
        data_dir = os.path.join(os.getcwd(), "data")
        mapping_path = os.path.join(data_dir, "aliases.json")
        if not os.path.exists(mapping_path):
             mapping_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "aliases.json")

    if not os.path.exists(mapping_path):
        return []
    with open(mapping_path, "r") as f:
        return json.load(f)


@router.post("/aliases")
def update_aliases(data: List[dict]):
    # Always save to the persistent location for Docker
    mapping_path = "/app/data/aliases.json"
    # Ensure directory exists if not in Docker
    if not os.path.exists("/app/data"):
        os.makedirs(os.path.join(os.getcwd(), "data"), exist_ok=True)
        mapping_path = os.path.join(os.getcwd(), "data", "aliases.json")

    with open(mapping_path, "w") as f:
        json.dump(data, f, indent=2)
    return {"status": "ok"}
