import os
import glob
import json
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.database import get_db
from app.models import Match, Player, PlayerAlias, PlayerMatchStats, PlayerGatherRating, PlayerGatherRatingHistory, MatchPayload
from app.services.ingest import ingest_match_payloads, recalculate_all_ratings, load_aliases
from app.utils import SLOW_QUERIES, record_slow_query

router = APIRouter(prefix="/api/admin", tags=["admin"])

class ReprocessRequest(BaseModel):
    match_ids: Optional[List[int]] = None

@router.post("/match/{match_id}/adopt/{source_id}")
def adopt_match_payloads(match_id: int, source_id: int, db: Session = Depends(get_db)):
    """
    Manually adopts all payloads from a source match into a target match.
    Useful for merging fragmented rounds that failed automatic detection.
    """
    target = db.query(Match).filter(Match.id == match_id).one_or_none()
    source = db.query(Match).filter(Match.id == source_id).one_or_none()
    if not target or not source:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Move payloads
    source_payloads = db.query(MatchPayload).filter(MatchPayload.match_id == source.id).all()
    for sp in source_payloads:
        sp.match_id = target.id
        # Ensure unique round number in target
        existing_round = db.query(MatchPayload).filter(
            MatchPayload.match_id == target.id,
            MatchPayload.round_number == sp.round_number
        ).first()
        if existing_round and existing_round.id != sp.id:
            # Shift to next available
            max_r = db.query(func.max(MatchPayload.round_number)).filter(MatchPayload.match_id == target.id).scalar()
            sp.round_number = (max_r or 0) + 1
            
    db.commit()
    
    # Delete the now-empty source match
    db.delete(source)
    db.commit()
    
    return {"status": "ok", "message": f"Match {source_id} merged into {match_id}. Please run reprocess for match {match_id}."}


@router.post("/match/{match_id}/force-draw")
def force_match_draw(match_id: int, db: Session = Depends(get_db)):
    """
    Manually forces a match to be a Draw (0).
    Useful for matches where round payloads are missing or corrupted.
    """
    match_row = db.query(Match).filter(Match.id == match_id).one_or_none()
    if not match_row:
        raise HTTPException(status_code=404, detail="Match not found")
    
    match_row.winner_team = 0
    match_row.winner_identity = 0
    db.commit()
    
    # Recalculate all ratings to reflect the new match result
    recalculate_all_ratings(db)
    
    return {"status": "ok", "message": f"Match {match_id} set to Draw and ratings recalculated."}


@router.post("/reprocess")
def reprocess_matches(req: ReprocessRequest, db: Session = Depends(get_db)):
    """
    Reprocesses existing matches from their JSON source files or relational payloads.
    If req.match_ids is provided, only those database IDs are reprocessed.
    """
    match_ids = req.match_ids
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
        payloads = []
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
            # --- NEW RELATIONAL SOURCE CHECK ---
            # Prioritize the immutable match_payloads table for reconstruction
            payload_rows = db.query(MatchPayload).filter(MatchPayload.match_id == m.id).order_by(MatchPayload.round_number).all()
            if payload_rows:
                try:
                    payloads = [json.loads(row.payload) for row in payload_rows]
                except Exception as e:
                    print(f"Error parsing MatchPayload for {m.match_id}: {e}")
            
            # Fallback to legacy raw_payload column only if the table is empty
            if not payloads and m.raw_payload:
                try:
                    payloads = json.loads(m.raw_payload)
                    if not isinstance(payloads, list):
                        payloads = [payloads]
                except Exception as e:
                    print(f"Error parsing raw_payload for {m.match_id}: {e}")
            
            if not payloads:
                # No source data to re-ingest...
                # directly from the columns already stored in player_match_stats.
                print(f"Info: No source for match {m.match_id} (DB ID: {m.id}) — recalculating UE from existing columns.")
                rows = db.query(PlayerMatchStats).filter(PlayerMatchStats.match_id == m.id).all()
                for row in rows:
                    kills = row.kills or 0
                    revives = row.revives or 0
                    medkits = (row.medkits or 0) + (row.team_medpacks or 0)
                    xp = row.xp or 0
                    combat_deaths = row.deaths or 0 # Fallback assumes 'deaths' column is scoreboard (Dth)
                    sk = row.self_kills or 0
                    points = kills + (revives * 0.33) + (medkits * 0.25) + (xp * 0.10)
                    total_actions = points + combat_deaths + (sk * 0.25)
                    row.unified_eff = round((points / total_actions) * 100.0, 1) if total_actions > 0 else 0.0
                db.flush()
                reprocessed_count += 1
                continue
        else:
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
            
            for f in files:
                try:
                    with open(f, "r") as fp:
                        payloads.append(json.load(fp))
                except Exception as e:
                    print(f"Error reading {f}: {e}")
        
        if payloads:
            print(f"Reprocessing match {m.match_id} with {len(payloads)} rounds...")
            ingest_match_payloads(db, payloads, target_db_match_id=m.id)
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


@router.post("/recalculate-ratings")
def recalculate_ratings(db: Session = Depends(get_db)):
    """
    Triggers a full ratings recalculation from scratch across all matches.
    """
    recalculate_all_ratings(db)
    return {"status": "ok", "message": "Global rating recalculation complete."}


@router.get("/match/{match_db_id}/raw")
def get_match_raw(match_db_id: int, db: Session = Depends(get_db)):
    """
    Exposes the raw round payloads for a given match (for debugging only).
    Reads from the relational MatchPayload table which contains all rounds in order.
    Falls back to the legacy raw_payload column for very old matches.
    """
    from app.models import MatchPayload
    m = db.query(Match).filter(Match.id == match_db_id).one_or_none()
    if not m:
        raise HTTPException(404, "match not found")

    # Prefer relational table (has all rounds)
    payload_rows = (
        db.query(MatchPayload)
        .filter(MatchPayload.match_id == m.id)
        .order_by(MatchPayload.round_number)
        .all()
    )
    if payload_rows:
        try:
            return [json.loads(row.payload) for row in payload_rows]
        except Exception as e:
            return {"error": f"Failed to parse relational payloads: {e}"}

    # Fallback: legacy raw_payload column (Round 1 only)
    if not m.raw_payload:
        return {"error": "no raw payload stored for this match"}
    try:
        return json.loads(m.raw_payload)
    except:
        return {"raw": m.raw_payload}


def run_db_migrations(db: Session):
    """
    Applies missing database columns and indexes.
    This effectively allows self-healing schema updates without manual SQL access.
    """
    # Get the raw connection from SQLAlchemy for ALTER TABLE 
    conn = db.get_bind().raw_connection()
    try:
        cursor = conn.cursor()
        
        # Helper to add column if it doesn't exist
        def add_col(table, col, definition):
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
                print(f"DEBUG: Added {col} to {table}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    pass
                else:
                    print(f"DEBUG: Error adding {col}: {e}")

        # Helper to add index if it doesn't exist
        def add_idx(table, col, idx_name=None):
            if not idx_name:
                idx_name = f"idx_{table}_{col}"
            try:
                cursor.execute(f"CREATE INDEX {idx_name} ON {table}({col})")
                print(f"DEBUG: Created index {idx_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    pass
                else:
                    print(f"DEBUG: Error adding index {idx_name}: {e}")

        add_col("matches", "raw_payload", "TEXT")
        add_col("matches", "round1_duration", "INTEGER")
        add_col("matches", "round2_duration", "INTEGER")
        add_col("matches", "is_gather", "INTEGER DEFAULT 0")
        add_col("matches", "match_winner_raw", "VARCHAR(16)")
        add_col("matches", "server_ip", "VARCHAR(64)")
        add_col("matches", "server_port", "INTEGER")
        add_col("matches", "round1_alpha_side", "INTEGER")
        add_col("matches", "round2_alpha_side", "INTEGER")
        add_col("players", "name_locked", "INTEGER DEFAULT 0")

        add_col("player_match_stats", "unified_eff", "FLOAT DEFAULT 0.0")
        add_col("player_match_stats", "medkits", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "team_deaths_received", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "pickup_medkits", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "pickup_ammopacks", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "shoves_given", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "shoves_received", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "in_mg_seconds", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "in_sprint_seconds", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "in_disguise_seconds", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "is_downed_seconds", "INTEGER DEFAULT 0")
        add_col("player_match_stats", "objectives_json", "TEXT")
        
        # Performance Indexes
        add_idx("matches", "round_start_unix")
        add_idx("matches", "mapname")
        add_idx("matches", "mvp_player_id")
        add_idx("player_match_stats", "player_id, round_index", "idx_pms_player_round")
        
        conn.commit()
        return {"status": "ok", "message": "Database schema migration and indexing complete."}
    except Exception as e:
        return {"status": "error", "message": f"Migration failed: {str(e)}"}


@router.post("/migrate")
def migrate_endpoint(db: Session = Depends(get_db)):
    return run_db_migrations(db)


@router.post("/migrate-payloads")
def migrate_payloads_to_table(db: Session = Depends(get_db)):
    """
    1. Sanitize Data: Fixes 'negative minuses' by setting negative values to 0.
    2. Schema Update: Ensures 'match_payloads' table exists.
    3. Migration: Transitions JSON history from 'matches.raw_payload' to 'match_payloads' rows.
    """
    from app.database import init_db, engine
    
    # 1. DATA SANITIZATION (The 'Negative Minuses' Fix)
    try:
        # Use raw SQL to efficiently update all rows across the DB
        sanity_query = text("""
            UPDATE player_match_stats 
            SET revives = MAX(0, revives), 
                self_kills = MAX(0, self_kills), 
                team_kills = MAX(0, team_kills), 
                gibs = MAX(0, gibs),
                team_gibs = MAX(0, team_gibs),
                damage_given = MAX(0, damage_given),
                damage_received = MAX(0, damage_received),
                time_played_pct = MAX(0, time_played_pct)
            WHERE revives < 0 OR self_kills < 0 OR team_kills < 0 
               OR gibs < 0 OR team_gibs < 0 OR damage_given < 0                OR damage_received < 0 OR time_played_pct < 0
        """)
        db.execute(sanity_query)
        
        # 1b. RECALCULATE DERIVED COLUMNS (KDR/EFF) after fix
        recalc_query = text("""
            UPDATE player_match_stats 
            SET kdr = CASE WHEN deaths > 0 THEN ROUND(CAST(kills AS FLOAT) / deaths, 2) ELSE kills END,
                eff = CASE WHEN (kills + deaths + self_kills) > 0 
                           THEN ROUND(100.0 * kills / (kills + deaths + self_kills), 1) 
                           ELSE 0.0 END
            WHERE kdr < 0 OR eff < 0
        """)
        db.execute(recalc_query)
        db.commit()
    except Exception as e:
        print(f"Sanitization Warning: {e}")

    # 2. SCHEMA UPDATE
    init_db()

    # 3. MIGRATION
    matches = db.query(Match).filter(Match.raw_payload.isnot(None)).all()
    created_rows = 0
    skipped_matches = 0

    for m in matches:
        # Check if already migrated to avoid double-entry
        existing_count = db.query(MatchPayload).filter(MatchPayload.match_id == m.id).count()
        if existing_count > 0:
            skipped_matches += 1
            continue

        try:
            payloads_list = json.loads(m.raw_payload)
            if not isinstance(payloads_list, list):
                payloads_list = [payloads_list]
            
            for i, p in enumerate(payloads_list):
                # Guess round number from internal payload 'round' or use index+1
                round_num = p.get("round", i + 1)
                new_p = MatchPayload(
                    match_id=m.id,
                    round_number=round_num,
                    payload=json.dumps(p)
                )
                db.add(new_p)
                created_rows += 1
        except Exception as e:
            print(f"Error migrating payloads for match {m.id}: {e}")

    db.commit()
    
    # 4. RECALCULATE GLOBAL RATINGS (SR)
    # Since we've healed negative values, we want to ensure SR reflects the clean data.
    from app.services.ingest import recalculate_all_ratings
    recalculate_all_ratings(db)
    
    return {
        "status": "ok",
        "sanitized": "ok",
        "migrated_rounds": created_rows,
        "already_migrated_matches": skipped_matches
    }


@router.post("/db-maintenance")
def db_maintenance(db: Session = Depends(get_db)):
    """
    Performs SQLite maintenance: VACUUM and ANALYZE.
    """
    try:
        db.execute(text("VACUUM"))
        db.execute(text("ANALYZE"))
        return {"status": "ok", "message": "Database VACUUM and ANALYZE complete."}
    except Exception as e:
        raise HTTPException(500, f"Maintenance failed: {str(e)}")


@router.get("/db-stats")
def db_stats(db: Session = Depends(get_db)):
    """
    Returns database statistics including row counts and index information.
    """
    try:
        counts = {
            "matches": db.query(Match).count(),
            "player_match_stats": db.query(PlayerMatchStats).count(),
            "players": db.query(Player).count(),
            "player_aliases": db.query(PlayerAlias).count(),
            "match_payloads": db.query(MatchPayload).count(),
        }
        
        # Get index list
        indexes = []
        res = db.execute(text("SELECT name, tbl_name FROM sqlite_master WHERE type='index'"))
        for row in res:
            indexes.append({"name": row[0], "table": row[1]})
            
        return {
            "counts": counts,
            "indexes": indexes,
            "db_size_bytes": os.path.getsize("etl_stats.db") if os.path.exists("etl_stats.db") else 0
        }
    except Exception as e:
        raise HTTPException(500, f"Stats failed: {str(e)}")


@router.get("/slow-queries")
def get_slow_queries():
    """Returns the last 50 recorded slow queries."""
    return {"slow_queries": SLOW_QUERIES}


def run_consolidation(db: Session) -> dict:
    """
    Core logic: merges all alias player records into their master identity.
    Called at startup and via the /consolidate endpoint.
    """
    alias_map = load_aliases()
    if not alias_map:
        return {"status": "ok", "message": "No aliases to consolidate", "consolidated_aliases": 0}

    consolidated_count = 0
    skipped_count = 0

    try:
        for alias_guid, master_guid in alias_map.items():
            if alias_guid == master_guid:
                skipped_count += 1
                continue

            master_player = db.query(Player).filter(Player.guid == master_guid).first()
            alias_player = db.query(Player).filter(Player.guid == alias_guid).first()

            if not alias_player:
                skipped_count += 1
                continue
            if not master_player:
                # Alias exists but master doesn't yet — re-label it
                alias_player.guid = master_guid
                db.flush()
                skipped_count += 1
                continue
            if master_player.id == alias_player.id:
                skipped_count += 1
                continue

            print(f"[Consolidate] {alias_player.display_name} ({alias_guid}) → {master_player.display_name} ({master_guid})")

            # 1. Re-attribute Match MVP references
            db.query(Match).filter(Match.mvp_player_id == alias_player.id).update(
                {"mvp_player_id": master_player.id}, synchronize_session=False
            )

            # 2. Migrate PlayerAlias name records
            db.query(PlayerAlias).filter(PlayerAlias.player_id == alias_player.id).update(
                {"player_id": master_player.id}, synchronize_session=False
            )

            # 3. Migrate all PlayerMatchStats — full column set
            alias_stats = db.query(PlayerMatchStats).filter(
                PlayerMatchStats.player_id == alias_player.id
            ).all()

            for a_stat in alias_stats:
                m_stat = db.query(PlayerMatchStats).filter(
                    PlayerMatchStats.player_id == master_player.id,
                    PlayerMatchStats.match_id == a_stat.match_id,
                    PlayerMatchStats.round_index == a_stat.round_index,
                ).first()

                if m_stat:
                    # Conflict: sum all additive counters into the master row
                    m_stat.kills                     += a_stat.kills or 0
                    m_stat.deaths                    += a_stat.deaths or 0
                    m_stat.self_kills                += a_stat.self_kills or 0
                    m_stat.team_kills                += a_stat.team_kills or 0
                    m_stat.gibs                      += a_stat.gibs or 0
                    m_stat.team_gibs                 += a_stat.team_gibs or 0
                    m_stat.headshots                 += a_stat.headshots or 0
                    m_stat.xp                        += a_stat.xp or 0
                    m_stat.damage_given              += a_stat.damage_given or 0
                    m_stat.damage_received           += a_stat.damage_received or 0
                    m_stat.team_damage_given         += a_stat.team_damage_given or 0
                    m_stat.team_damage_received      += a_stat.team_damage_received or 0
                    m_stat.revives                   += a_stat.revives or 0
                    m_stat.medkits                   += a_stat.medkits or 0
                    m_stat.team_medpacks             += a_stat.team_medpacks or 0
                    m_stat.team_deaths_received      += a_stat.team_deaths_received or 0
                    m_stat.spam_kills                += a_stat.spam_kills or 0
                    m_stat.spawn_count               += a_stat.spawn_count or 0
                    m_stat.crouched_seconds          += a_stat.crouched_seconds or 0
                    m_stat.proned_seconds            += a_stat.proned_seconds or 0
                    m_stat.leaned_seconds            += a_stat.leaned_seconds or 0
                    m_stat.distance_travelled_meters += a_stat.distance_travelled_meters or 0.0
                    
                    # Recalculate derived floats (Scoreboard Standard)
                    m_stat.kdr = round(m_stat.kills / max(1, m_stat.deaths), 2)
                    m_stat.eff = round(100.0 * m_stat.kills / max(1, m_stat.kills + m_stat.deaths), 1)
                    
                    # Unified Efficiency (Competitive Weights)
                    kills = m_stat.kills; revives = m_stat.revives; xp = m_stat.xp
                    damage = m_stat.damage_given; combat_deaths = m_stat.deaths; sk = m_stat.self_kills
                    points = kills + (revives * 0.33) + (damage / 100.0) + (xp * 0.1)
                    total_ue = points + combat_deaths + (sk * 0.25)
                    m_stat.unified_eff = round((points / total_ue) * 100.0, 1) if total_ue > 0 else 0.0
                    db.delete(a_stat)
                else:
                    # No conflict — simply re-attribute the row to the master
                    a_stat.player_id = master_player.id

            db.flush()

            # 4. Purge alias rating rows (will be recalculated from scratch for master)
            db.query(PlayerGatherRating).filter(
                PlayerGatherRating.player_id == alias_player.id
            ).delete(synchronize_session=False)
            db.query(PlayerGatherRatingHistory).filter(
                PlayerGatherRatingHistory.player_id == alias_player.id
            ).delete(synchronize_session=False)
            db.flush()

            # 5. Delete the now-empty alias player record
            db.delete(alias_player)
            db.flush()

            consolidated_count += 1

        db.commit()

    except Exception as e:
        db.rollback()
        import traceback
        print(f"[Consolidate] CRITICAL ERROR: {e}\n{traceback.format_exc()}")
        return {"status": "error", "message": f"Consolidation failed: {str(e)}"}

    if consolidated_count > 0:
        print(f"[Consolidate] Merged {consolidated_count} alias(es). Triggering full SR recalculation...")
        recalculate_all_ratings(db)

    return {
        "status": "ok",
        "consolidated_aliases": consolidated_count,
        "skipped": skipped_count,
        "message": f"Consolidated {consolidated_count} alias(es). Ratings recalculated." if consolidated_count > 0 else "Database already clean — no orphans found.",
    }


@router.post("/consolidate")
def consolidate_aliases(db: Session = Depends(get_db)):
    """
    Globally consolidates the database by merging statistics from alias GUIDs
    into their master identity. Also runs automatically on server startup.
    """
    return run_consolidation(db)


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


@router.get("/ghost-boosts")
def get_ghost_boosts() -> Dict[str, float]:
    mapping_path = "/app/data/ghost_boosts.json"
    if not os.path.exists(mapping_path):
        data_dir = os.path.join(os.getcwd(), "data")
        mapping_path = os.path.join(data_dir, "ghost_boosts.json")
        if not os.path.exists(mapping_path):
             mapping_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ghost_boosts.json")

    if not os.path.exists(mapping_path):
        return {}
    with open(mapping_path, "r") as f:
        return json.load(f)


@router.post("/ghost-boosts")
def update_ghost_boosts(data: Dict[str, float]):
    mapping_path = "/app/data/ghost_boosts.json"
    if not os.path.exists("/app/data"):
        os.makedirs(os.path.join(os.getcwd(), "data"), exist_ok=True)
        mapping_path = os.path.join(os.getcwd(), "data", "ghost_boosts.json")

    with open(mapping_path, "w") as f:
        json.dump(data, f, indent=2)
    return {"status": "ok"}


class PlayerNameUpdate(BaseModel):
    display_name: str


@router.post("/players/{guid}/display-name")
def update_player_display_name(guid: str, body: PlayerNameUpdate, db: Session = Depends(get_db)):
    """
    Manually overrides a player's display name. 
    This is useful for 'locking' a clean name that won't be overwritten 
    by subsequent tag changes during ingestion.
    """
    player = db.query(Player).filter(Player.guid == guid).one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player.display_name = body.display_name
    player.name_locked = 1
    db.commit()
    return {"status": "ok", "guid": guid, "new_name": body.display_name}
