import json
from datetime import datetime
from typing import Any
from collections import defaultdict

import os
from sqlalchemy.orm import Session

from app.models import (
    Match,
    Player,
    PlayerGatherRating,
    PlayerGatherRatingHistory,
    PlayerMatchStats,
    MatchPayload,
)
from app.parsers.events import compute_event_metrics, hs_accuracy, nemesis_to_json
from app.parsers.names import strip_quake_colors, normalize_nick
from app.parsers.weapon_stats import UnpackedWeaponStats, revives_from_unpacked, unpack_weapon_stats
from app.parsers.weapon_classes import ClassTimelineTracker
from app.rating import (
    PlayerPerformance,
    calculate_openskill_ratings,
    compute_display_rating,
    get_performance_score,
)


def _weapon_breakdown_json(u: UnpackedWeaponStats | None) -> str | None:
    if not u or not u.weapons:
        return None
    rows = []
    for w in u.weapons:
        acc = None
        if w.shots > 0:
            acc = round(100.0 * w.hits / w.shots, 2)
        rows.append(
            {
                "slot": w.slot,
                "name": w.name,
                "hits": w.hits,
                "shots": w.shots,
                "kills": w.kills,
                "deaths": w.deaths,
                "headshots": w.headshots,
                "accuracy": acc,
            }
        )
    return json.dumps(rows)


def _weapon_breakdown_json_from_dict(weapons: dict[int, dict] | None) -> str | None:
    if not weapons:
        return None
    rows = []
    for w in weapons.values():
        acc = None
        if w["shots"] > 0:
            acc = round(100.0 * w["hits"] / w["shots"], 2)
        rows.append(
            {
                "slot": w["slot"],
                "name": w["name"],
                "hits": w["hits"],
                "shots": w["shots"],
                "kills": w["kills"],
                "deaths": w["deaths"],
                "headshots": w["headshots"],
                "accuracy": acc,
            }
        )
    return json.dumps(rows)


def _eff_kdr(kills: int, combat_deaths: int) -> tuple[float, float]:
    eff = round(100.0 * kills / max(1, kills + combat_deaths), 1)
    kdr = round(kills / max(1, combat_deaths), 2)
    return eff, kdr


def _calc_delta(current: int | float, previous: int | float | None) -> int | float:
    if previous is None:
        return current
    delta = current - (previous or 0)
    if delta < 0:
        # Reset detected: previous session state was lost or engine counter rolled over
        return current
    return delta


def _calculate_unified_eff(kills: int, revives: int, damage_given: int, xp: int, combat_deaths: int, self_kills: int) -> float:
    # Unified Points formula
    # ET: Legacy tactical weights: 0.33 per Revive, 0.1 per XP
    points = kills + (revives * 0.33) + (damage_given / 100.0) + (xp * 0.1)
    
    # Total Actions denominator:
    # Combat deaths count as 1.0 (regular death)
    # Self-kills weighted at 0.25 (as requested)
    total_actions = points + combat_deaths + (self_kills * 0.25)
    if total_actions <= 0:
        return 0.0
    return round((points / total_actions) * 100.0, 1)


def load_aliases() -> dict[str, str]:
    """Load GUID aliases from the persistent data directory."""
    # Prioritize the mapped data volume for persistence
    mapping_path = "/app/data/aliases.json"
    if not os.path.exists(mapping_path):
        # Fallback for local development or first-run migration
        data_dir = os.path.join(os.getcwd(), "data")
        mapping_path = os.path.join(data_dir, "aliases.json")
        
        if not os.path.exists(mapping_path):
            # Last resort: check next to app (local dev fallback)
            mapping_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aliases.json")
            
    if not os.path.exists(mapping_path):
        return {}
    try:
        with open(mapping_path, "r") as f:
            data = json.load(f)
            # data is now a list of objects: [{"name": "...", "master_guid": "...", "aliases": [...]}]
            flat_map = {}
            if isinstance(data, list):
                for entry in data:
                    master = str(entry.get("master_guid", "")).strip().upper()
                    if not master:
                        continue
                    aliases = entry.get("aliases", [])
                    if isinstance(aliases, list):
                        for a in aliases:
                            flat_map[str(a).strip().upper()] = master
            return flat_map
    except Exception as e:
        print(f"Warning: Failed to load aliases.json: {e}")
        return {}


def _determine_winner_team(payloads: list[dict]) -> tuple[int, int | None, int | None]:
    """
    Determines the match winner from a list of round payloads.
    Returns (winner_team, round1_duration, round2_duration).
    """
    if not payloads:
        return 0, None, None

    # HEURISTIC 1: Trust engine-side score tracking if available in metadata
    # The Lua script calculates this using exact engine state/rules.
    for p in reversed(payloads):
        meta = p.get("metadata") or {}
        scores = meta.get("scores")
        if scores and scores.get("match_winner"):
            mw = scores["match_winner"]
            if mw == "draw":
                return 0, None, None # It's a draw
            
            # The 'round' block in scores tells us the winner of the round that just ended
            round_score = scores.get("round")
            if round_score and round_score.get("winner_et"):
                # If the match is finished, the match_winner reflects the overall winner.
                # However, our backend 'winner_team' usually stores the winner of the 
                # LAST round if it decided the match (or the side that won the map).
                # For now, if match_winner matches the last round winner, we return that team.
                if mw == round_score.get("winner"):
                    winner = int(round_score.get("winner_et"))
                    # Still calculate durations for display
                    r1 = payloads[0].get("round_info", {})
                    r2 = payloads[1].get("round_info", {}) if len(payloads) > 1 else {}
                    d1 = int(r1.get("round_end_unix") or 0) - int(r1.get("round_start_unix") or 0)
                    d2 = int(r2.get("round_end_unix") or 0) - int(r2.get("round_start_unix") or 0) if r2 else None
                    return winner, d1, d2

    # HEURISTIC 2: Manual Stopwatch/Duration logic (Fallback)
    if len(payloads) == 2:
        r1 = payloads[0].get("round_info", {})
        r2 = payloads[1].get("round_info", {})
        w1 = int(r1.get("winnerteam") or 0)
        w2 = int(r2.get("winnerteam") or 0)
        
        # Duration calculation (preferring millisecond precision if available)
        r1_ms = int(r1.get("round_end") or 0) - int(r1.get("round_start") or 0)
        r2_ms = int(r2.get("round_end") or 0) - int(r2.get("round_start") or 0)
        
        # Fallback to unix seconds for display-only fields in the DB 
        d1 = int(r1.get("round_end_unix") or 0) - int(r1.get("round_start_unix") or 0)
        d2 = int(r2.get("round_end_unix") or 0) - int(r2.get("round_start_unix") or 0)

        winner = 0
        if w1 > 0 and w2 > 0:
            if w1 != w2:
                # One physical team won both rounds (one as attacker, one as defender).
                # The winner of the match is the team that won Round 1.
                winner = w1
            else:
                # Same engine side won both rounds (e.g., both won as Allies).
                defender_et = int(r1.get("defenderteam") or 1)
                if w1 == defender_et:
                    # Double full hold (both teams won as defenders)
                    winner = 0 # True draw
                    # Normalize durations for display consistency if it's a full hold
                    d1 = d2 = max(d1, d2) if (d1 and d2) else d1
                else:
                    # Both teams completed the objective. The faster one wins.
                    if r1_ms < r2_ms: winner = w1
                    elif r2_ms < r1_ms: winner = 3 - w1
                    else: winner = 0 # True draw (identical times)
        elif w1 > 0: winner = w1
        elif w2 > 0: winner = w2
        
        return winner, d1, d2
    else:
        # Single round or 3+
        r = payloads[-1].get("round_info", {})
        winner = int(r.get("winnerteam") or 0)
        d = int(r.get("round_end_unix") or 0) - int(r.get("round_start_unix") or 0)
        return winner, d, None


def ingest_match_payloads(db: Session, payloads: list[dict[str, Any]], store_raw: bool = True, target_db_match_id: int = None, request_ip: str = None) -> Match:
    if not payloads:
        raise ValueError("no payloads provided")

    aliases = load_aliases()

    def get_epoch(p):
        r = p.get("round_info", {})
        
        # Priority 1: Check if the JSON already contains the correct Unix timestamps
        rs_u = int(r.get("round_start_unix") or 0)
        re_u = int(r.get("round_end_unix") or 0)
        
        if rs_u > 1000000000 and re_u > 1000000000:
            return rs_u, re_u

        re_r = int(r.get("round_end") or 0)
        rs_r = int(r.get("round_start") or 0)
        
        # If rs_r is 0, try to find the earliest event timestamp as a fallback
        actual_rs_r = rs_r
        if actual_rs_r == 0:
            evs = (r.get("damageStats") or []) + (r.get("obituaries") or []) + (r.get("messages") or [])
            if evs:
                min_ev = min(int(e.get("timestamp") or 999999999) for e in evs)
                if min_ev < 999999999:
                    actual_rs_r = max(0, min_ev - 5000)
        
        # Priority 2: Use matchID as the anchor. 
        # Filename matchID is usually the START time of the match.
        mid_val = 0
        try:
            mid_val = int(r.get("matchID") or p.get("matchID") or 0)
        except:
            pass

        if mid_val > 1000000000:
            # We treat matchID as the round start unix (rs_u)
            # Calculate boot time from rs_u and rs_r
            boot_u = float(mid_val) - (actual_rs_r / 1000.0)
            calculated_re_u = boot_u + (re_r / 1000.0)
            return int(mid_val), int(calculated_re_u)
            
        return 0, 0

    def _fix_timestamps(items, server_boot_u, rs_u):
        if not items or not isinstance(items, list):
            return
        for item in items:
            uptime_ms = item.get("timestamp")
            if uptime_ms is not None:
                item["timestamp_original"] = uptime_ms
                item["timestamp"] = int(server_boot_u + (int(uptime_ms) / 1000.0))

    # PRE-PROCESS: Fix timestamps in payloads BEFORE any serialization
    for p in payloads:
        round_info = p.get("round_info") or {}
        this_rs, this_re = get_epoch(p)
        
        re_r = int(round_info.get("round_end") or 0)
        server_boot_u = this_re - (re_r / 1000.0)
        
        # Update round_info with correct unix timestamps
        round_info["round_start_unix"] = this_rs
        round_info["round_end_unix"] = this_re
            
        _fix_timestamps(round_info.get("damageStats"), server_boot_u, this_rs)
        _fix_timestamps(round_info.get("obituaries"), server_boot_u, this_rs)
        _fix_timestamps(round_info.get("messages"), server_boot_u, this_rs)
        
    # Now payloads are "fixed", proceed with ingestion
    primary = payloads[0]
    round_info_primary = primary.get("round_info") or {}
    # Alignment: Oksii moved global fields to 'metadata'
    metadata_primary = primary.get("metadata") or {}

    match_id = ""
    # If the caller forces a DB match, use its string ID to bind the payloads
    if target_db_match_id:
        from app.models import Match
        existing_target = db.query(Match).filter(Match.id == target_db_match_id).one_or_none()
        if existing_target:
            match_id = existing_target.match_id
            
    # Failing that, find a match ID that actually exists in the database from the payloads
    if not match_id:
        from app.models import Match
        for p in payloads:
            m_id = str(p.get("metadata", {}).get("matchID") or p.get("round_info", {}).get("matchID") or p.get("matchID") or "")
            if m_id:
                if db.query(Match).filter(Match.match_id == m_id).first():
                    match_id = m_id
                    break

    # Fallback to the first payload if no existing match is found
    if not match_id:
        match_id = str(metadata_primary.get("matchID") or round_info_primary.get("matchID") or primary.get("matchID") or "")
        
    if not match_id:
        raise ValueError("missing matchID")

    # Extract server info from payloads
    server_ip = None
    server_port = None
    for p in payloads:
        ri = p.get("round_info") or {}
        if ri.get("server_ip"):
            server_ip = str(ri["server_ip"])
        if ri.get("server_port"):
            server_port = int(ri["server_port"])
            
    # Fallback to request IP if not in payload
    if not server_ip:
        server_ip = request_ip

    mapname = str(metadata_primary.get("mapname") or round_info_primary.get("mapname") or "")
    
    # Exclude certain maps from tracking
    if mapname.lower() in ("mp_sillyctf", "mp_valhalla"):
        print(f"DEBUG: Skipping matchID {match_id} because map '{mapname}' is in exclusion list.")
        return None

    # Initial winner determination from the incoming payloads.
    # NOTE: For Stopwatch matches this is often only 1 round (the server sends rounds one at a time).
    # The definitive winner is recalculated after merging with existing DB payloads — see below.
    winner_team, d1, d2 = _determine_winner_team(payloads)
    
    # GATHER DETECTION: Check features in metadata
    is_gather = 0
    if metadata_primary.get("features"):
        # If any gather feature like auto_scores, auto_rename is on, it's a gather match
        is_gather = 1
    
    match_winner_raw = None
    r1_alpha_side_meta = None
    # Extract the string winner (alpha/beta/draw) and Alpha side mapping
    for p in payloads:
        meta = p.get("metadata") or {}
        scores = meta.get("scores")
        if scores:
            if scores.get("match_winner"):
                match_winner_raw = scores["match_winner"]
            
            # Check for Alpha side in any round metadata
            round_meta = scores.get("round")
            if round_meta and round_meta.get("round_num") == 1:
                r1_alpha_side_meta = round_meta.get("alpha_side")
    
    rs, _ = get_epoch(payloads[0])
    _, re = get_epoch(payloads[-1])

    # 1. Primary lookup by exact Match ID
    existing = db.query(Match).filter(Match.match_id == match_id).one_or_none()
    
    if not existing:
        # 2. Heuristic: Check for a recent match on the same map and SAME SERVER (within 30 mins)
        # This allows Round 2 to merge even if it was assigned a different Match ID.
        # Anchor threshold to the round start time (rs) to support historical reprocessing.
        recent_threshold = rs - (30 * 60)
        
        recent_match_query = (
            db.query(Match)
            .filter(Match.mapname == mapname)
            .filter(Match.round_end_unix >= recent_threshold)
            .filter(Match.round_end_unix <= rs)
        )

        if server_ip:
            recent_match_query = recent_match_query.filter(Match.server_ip == server_ip)
        if server_port:
            recent_match_query = recent_match_query.filter(Match.server_port == server_port)

        recent_match = recent_match_query.order_by(Match.round_end_unix.desc()).first()
        if recent_match:
            print(f"DEBUG: Found recent match for map '{mapname}' (ID: {recent_match.match_id}) - adopting for round merging.")
            existing = recent_match
            # Adopt the existing match_id so subsequent logic links correctly
            match_id = existing.match_id
    
    # Track which round indices we are processing
    processing_round_indices = []
    for i, p in enumerate(payloads):
        r_info = p.get("round_info") or {}
        ri = int(r_info.get("round_index") or r_info.get("round") or (i + 1))
        processing_round_indices.append(ri)

    if existing:
        print(f"DEBUG: Found existing match record {match_id} - merging rounds.")
        
        # --- NEW RELATIONAL PAYLOAD STORAGE ---
        # For each incoming payload, we store it as a separate row in MatchPayload.
        # This prevents accidental truncation of the entire match history.
        for i, p in enumerate(payloads):
            ri_p = p.get("round_info") or {}
            round_num = int(ri_p.get("round_index") or ri_p.get("round") or (i + 1))
            
            # SEQUENCE CORRECTION: If Round 1 already exists but from a DIFFERENT start time,
            # we treat this as the next round (typical for fragmented matches like Match 155/171).
            if round_num == 1:
                existing_r1 = db.query(MatchPayload).filter(
                    MatchPayload.match_id == existing.id,
                    MatchPayload.round_number == 1
                ).one_or_none()
                if existing_r1:
                    try:
                        ex_p = json.loads(existing_r1.payload)
                        ex_rs = int((ex_p.get("round_info") or {}).get("round_start_unix") or 0)
                        cu_rs = int(ri_p.get("round_start_unix") or 0)
                        if ex_rs > 0 and cu_rs > 0 and cu_rs > ex_rs:
                            print(f"DEBUG: Found Round 1 collision for Match {existing.id}. New round starts later ({cu_rs} > {ex_rs}) - remapping to Round 2.")
                            round_num = 2
                    except:
                        pass

            # Upsert logic for the specific round
            existing_payload_row = db.query(MatchPayload).filter(
                MatchPayload.match_id == existing.id,
                MatchPayload.round_number == round_num
            ).one_or_none()
            
            if existing_payload_row:
                existing_payload_row.payload = json.dumps(p)
            else:
                db.add(MatchPayload(
                    match_id=existing.id,
                    round_number=round_num,
                    payload=json.dumps(p)
                ))
        
        db.flush() # Ensure MatchPayload rows are in the session
        
        # --- FULL HISTORY RECONSTRUCTION ---
        # We always process THE ENTIRE match history from the MatchPayload table.
        # This guarantees Round 0 (Total Score) is always accurate.
        all_payload_rows = db.query(MatchPayload).filter(MatchPayload.match_id == existing.id).order_by(MatchPayload.round_number).all()
        payloads = [json.loads(mp_row.payload) for mp_row in all_payload_rows]
        
        # ... logic for ratings reversal remains the same ...

        # Revert ratings for existing histories (they will be recalculated)
        hists = (
            db.query(PlayerGatherRatingHistory)
            .filter(PlayerGatherRatingHistory.match_id == existing.id)
            .all()
        )
        for h in hists:
            gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == h.player_id).one_or_none()
            if gr:
                gr.current_rating = max(100.0, gr.current_rating - h.delta)
        db.query(PlayerGatherRatingHistory).filter(PlayerGatherRatingHistory.match_id == existing.id).delete()
        
        # We RE-IDENTIFY processing rounds now that we've merged
        processing_round_indices = []
        for i, p in enumerate(payloads):
            r_info = p.get("round_info") or {}
            ri = int(r_info.get("round_index") or r_info.get("round") or (i + 1))
            processing_round_indices.append(ri)

        # Delete all round rows we are about to (re)process (plus the total row at round_index=0)
        db.query(PlayerMatchStats).filter(
            PlayerMatchStats.match_id == existing.id,
            PlayerMatchStats.round_index.in_([0] + processing_round_indices)
        ).delete()
        
        # --- RECOMPUTE WINNER FROM THE FULL MERGED PAYLOAD SET ---
        winner_team, d1, d2 = _determine_winner_team(payloads)
        
        # Determine the definitive Alpha Side for Round 1
        # Priority: Metadata > Existing DB > Default (1=Axis)
        alpha_side_r1 = r1_alpha_side_meta or existing.round1_alpha_side or 1
        existing.round1_alpha_side = alpha_side_r1
        
        # Map Engine Winner to Pinned Winner
        engine_to_pinned = {1: 1, 2: 2}
        p1_stats = payloads[0].get("player_stats") or {}
        if p1_stats:
            sample_guid = next(iter(p1_stats))
            sample_pdata = p1_stats[sample_guid]
            engine_team = int(sample_pdata.get("team") or 0)
            engine_side = int(sample_pdata.get("side") or 0)
            # If we don't have 'side' in player stats, we use defenderteam heuristic
            if engine_side == 0:
                ri_p = payloads[0].get("round_info") or {}
                defender_et = ri_p.get("defenderteam")
                if defender_et:
                    # In ET, defender is usually Axis (Side 1) or Allies (Side 2)
                    # For Bremen/Goldrush, Axis (1) defends.
                    # We assume defender_et corresponds to Side 1 (Axis) for now.
                    engine_side = 1 if engine_team == defender_et else 2

            if engine_team in (1, 2) and engine_side in (1, 2):
                if engine_side == alpha_side_r1:
                    engine_to_pinned = {engine_team: 1, (3 - engine_team): 2}
                else:
                    engine_to_pinned = {engine_team: 2, (3 - engine_team): 1}
        
        # Calculate final winner
        # Priority: Explicit match_winner_raw > Custom Logic
        if match_winner_raw == "alpha":
            final_winner = 1
        elif match_winner_raw == "beta":
            final_winner = 2
        elif match_winner_raw == "draw":
            final_winner = 0
        else:
            final_winner = engine_to_pinned.get(winner_team, winner_team)
            
        existing.mapname = mapname
        existing.winner_team = final_winner
        existing.round1_duration = d1
        existing.round2_duration = d2
        existing.round_start_unix = min(existing.round_start_unix, rs)
        existing.round_end_unix = max(existing.round_end_unix, re)
        existing.is_gather = is_gather
        existing.match_winner_raw = match_winner_raw
        if server_ip: existing.server_ip = server_ip
        if server_port: existing.server_port = server_port
        match_row = existing
        db.flush()
    else:
        print(f"DEBUG: Creating new match record for matchID {match_id}")
        
        # --- RECOMPUTE WINNER ---
        winner_team, d1, d2 = _determine_winner_team(payloads)
        
        # Determine the definitive Alpha Side for Round 1
        # Priority: Metadata > Default (1=Axis)
        alpha_side_r1 = r1_alpha_side_meta or 1
        
        # Map Engine Winner to Pinned Winner
        engine_to_pinned = {1: 1, 2: 2}
        p1_stats = payloads[0].get("player_stats") or {}
        if p1_stats:
            sample_guid = next(iter(p1_stats))
            sample_pdata = p1_stats[sample_guid]
            engine_team = int(sample_pdata.get("team") or 0)
            engine_side = int(sample_pdata.get("side") or 0)
            if engine_side == 0:
                ri_p = payloads[0].get("round_info") or {}
                defender_et = ri_p.get("defenderteam")
                if defender_et:
                    engine_side = 1 if engine_team == defender_et else 2

            if engine_team in (1, 2) and engine_side in (1, 2):
                if engine_side == alpha_side_r1:
                    engine_to_pinned = {engine_team: 1, (3 - engine_team): 2}
                else:
                    engine_to_pinned = {engine_team: 2, (3 - engine_team): 1}
        
        # Calculate final winner
        if match_winner_raw == "alpha":
            final_winner = 1
        elif match_winner_raw == "beta":
            final_winner = 2
        elif match_winner_raw == "draw":
            final_winner = 0
        else:
            final_winner = engine_to_pinned.get(winner_team, winner_team)

        match_row = Match(
            match_id=match_id,
            mapname=mapname,
            winner_team=final_winner,
            round1_duration=d1,
            round2_duration=d2,
            round_start_unix=rs,
            round_end_unix=re,
            is_gather=is_gather,
            match_winner_raw=match_winner_raw,
            round1_alpha_side=alpha_side_r1,
            server_ip=server_ip,
            server_port=server_port,
            # We also save to the legacy raw_payload for backward compatibility/backup for now
            raw_payload=json.dumps(payloads),
        )
        db.add(match_row)
        db.flush()
        
        # Store initial rounds in the new relational table
        for i, p in enumerate(payloads):
            ri_p = p.get("round_info") or {}
            round_num = int(ri_p.get("round_index") or ri_p.get("round") or (i + 1))
            db.add(MatchPayload(
                match_id=match_row.id,
                round_number=round_num,
                payload=json.dumps(p)
            ))
        db.flush()

    # To calculate total stats, we keep track of values per guid
    class TotalStat:
        def __init__(self, name_raw: str, display: str, team: int):
            self.name_raw = name_raw
            self.display = display
            self.team = team
            self.kills = 0
            self.deaths = 0 # Now represents COMBAT deaths (enemy-inflicted)
            self.team_deaths_received = 0
            self.damage_given = 0
            self.damage_received = 0
            self.team_damage_given = 0
            self.team_damage_received = 0
            self.headshots = 0
            self.gibs = 0
            self.self_kills = 0
            self.team_kills = 0
            self.team_gibs = 0
            self.time_played_pcts = []
            self.xp = 0
            self.revives = 0
            self.medkits = 0
            self.team_medpacks = 0 # Ammo
            self.spam_kills = 0
            self.headshot_hits = 0
            self.shots_recorded = 0
            self.distance_travelled_meters = 0.0
            self.distance_travelled_spawn_avg = 0.0
            self.spawn_count = 0
            self.speed_ups_avg = 0.0
            self.speed_ups_peak = 0.0
            self.crouched_seconds = 0
            self.proned_seconds = 0
            self.leaned_seconds = 0
            self.in_mg_seconds = 0
            self.in_sprint_seconds = 0
            self.in_disguise_seconds = 0
            self.is_downed_seconds = 0
            self.shoves_given = 0
            self.shoves_received = 0
            self.pickup_medkits = 0
            self.pickup_ammopacks = 0
            self.classes_played_lists = []
            self.objectives_list = []
            self.weapons: dict[int, dict] = {}

    # Map to accumulate totals across ALL rounds (existing in DB + new in payloads)
    total_stats_by_guid: dict[str, TotalStat] = {}
    player_db_by_guid: dict[str, Player] = {}
    first_team_by_guid: dict[str, int] = {}
    # Map to track cumulative session state *immediately before* the current round
    prev_unpacked_by_guid: dict[str, UnpackedWeaponStats] = {}

    # --- PROTOCOL IDENTIFICATION ---
    # Determine if we have a granular 'gamelog' (Modern API v2.x)
    has_gamelog_any = any((p.get("gamelog") is not None) or ( (p.get("round_info") or {}).get("gamelog") is not None) for p in payloads)
    
    # --- CLEAN RE-INGESTION LOGIC ---
    # We always wipe the "Total Score" (round_index=0) as it must be recalculated
    # from the sum of all available rounds (both DB and new payloads).
    # Clear out all previous statistics for this match (rounds and totals)
    db.query(PlayerMatchStats).filter(
        PlayerMatchStats.match_id == match_row.id
    ).delete()

    # Identify the round indices in the current payloads.
    payload_rounds = []
    for i, body in enumerate(payloads):
        ri = body.get("round_info") or {}
        r_idx = int(ri.get("round_index") or ri.get("round") or (i + 1))
        payload_rounds.append(r_idx)

    # Delete existing round-specific stats ONLY for the rounds we are currently ingesting.
    db.query(PlayerMatchStats).filter(
        PlayerMatchStats.match_id == match_row.id,
        PlayerMatchStats.round_index.in_(payload_rounds)
    ).delete()
    db.flush()

    # --- LOAD ROUNDS FROM DB ---
    # In a clean-slate reprocess, this will be empty. 
    # For a rolling update (e.g. adding Round 2 to a live match), it loads Round 1.
    existing_stats = db.query(PlayerMatchStats).filter(
        PlayerMatchStats.match_id == match_row.id,
        PlayerMatchStats.round_index > 0
    ).order_by(PlayerMatchStats.round_index.asc()).all()

    for row in existing_stats:
        p = row.player
        guid = p.guid
        player_db_by_guid[guid] = p
        if guid not in total_stats_by_guid:
            total_stats_by_guid[guid] = TotalStat(row.name_raw or "", p.display_name or "", row.team)
            if row.team in (1, 2):
                first_team_by_guid[guid] = row.team
        else:
            if guid not in first_team_by_guid and row.team in (1, 2):
                first_team_by_guid[guid] = row.team
        
        ts = total_stats_by_guid[guid]
        ts.kills += row.kills
        ts.deaths += row.deaths
        ts.damage_given += row.damage_given
        ts.damage_received += row.damage_received
        ts.team_damage_given += row.team_damage_given
        ts.team_damage_received += row.team_damage_received
        ts.headshots += row.headshots
        ts.gibs += row.gibs
        ts.self_kills += row.self_kills
        ts.team_kills += row.team_kills
        ts.team_gibs += row.team_gibs
        ts.xp += row.xp
        ts.revives += row.revives
        ts.medkits += row.medkits
        ts.team_medpacks += row.team_medpacks
        ts.spam_kills += row.spam_kills
        ts.spawn_count += row.spawn_count
        ts.speed_ups_avg += row.speed_ups_avg
        ts.speed_ups_peak = max(ts.speed_ups_peak, row.speed_ups_peak)
        ts.distance_travelled_spawn_avg += row.distance_travelled_spawn_avg
        ts.distance_travelled_meters += row.distance_travelled_meters
        ts.crouched_seconds += row.crouched_seconds
        ts.proned_seconds += row.proned_seconds
        ts.leaned_seconds += row.leaned_seconds
        ts.in_mg_seconds += row.in_mg_seconds
        ts.in_sprint_seconds += row.in_sprint_seconds
        ts.in_disguise_seconds += row.in_disguise_seconds
        ts.is_downed_seconds += row.is_downed_seconds
        ts.shoves_given += row.shoves_given
        ts.shoves_received += row.shoves_received
        ts.pickup_medkits += row.pickup_medkits
        ts.pickup_ammopacks += row.pickup_ammopacks
        
        if row.classes_played_json:
            ts.classes_played_lists.extend(json.loads(row.classes_played_json))
        if row.objectives_json:
            ts.objectives_list.extend(json.loads(row.objectives_json))
        ts.time_played_pcts.append(row.time_played_pct)

        # Seed prev_unpacked_by_guid for delta calculation
        # We need the MOST RECENT round's cumulative state for each player
        if guid not in prev_unpacked_by_guid or row.round_index > getattr(prev_unpacked_by_guid[guid], "_round_idx", 0):
            # Create a mock unpacked object or data-wrapper from the DB row
            from app.parsers.weapon_stats import UnpackedWeaponStats, WeaponStatRow
            
            # Parse stored JSON breakdown
            stored_weapons = []
            if row.weapon_breakdown_json:
                try:
                    wb = json.loads(row.weapon_breakdown_json)
                    for slot_s, w in wb.items():
                        stored_weapons.append(WeaponStatRow(
                            slot=int(slot_s),
                            name=w.get("name", ""),
                            hits=w.get("hits", 0),
                            shots=w.get("shots", 0),
                            kills=w.get("kills", 0),
                            deaths=w.get("deaths", 0),
                            headshots=w.get("headshots", 0)
                        ))
                except:
                    pass
            
            mock_unpacked = UnpackedWeaponStats(
                mask=0, 
                weapons=stored_weapons,
                damage_given=row.damage_given,
                damage_received=row.damage_received,
                team_damage_given=row.team_damage_given,
                team_damage_received=row.team_damage_received,
                gibs=row.gibs,
                self_kills=row.self_kills,
                team_kills=row.team_kills,
                team_gibs=row.team_gibs,
                time_played_pct=row.time_played_pct,
                xp=row.xp,
                kills=row.kills,
                deaths=row.deaths,
                revives=row.revives,
                medkits=row.medkits,
                ammopacks=row.team_medpacks
            )
            # Store some extra metadata for numeric deltas derived from pdata
            setattr(mock_unpacked, "_round_idx", row.round_index)
            # Mock the pdata reference for spawns/distance/stances
            mock_pdata = {
                "spawn_count": row.spawn_count,
                "distance_travelled_meters": row.distance_travelled_meters,
                "stance_stats_seconds": {
                    "in_crouch": row.crouched_seconds,
                    "in_prone": row.proned_seconds,
                    "in_lean": row.leaned_seconds
                }
            }
            setattr(mock_unpacked, "pdata_ref", mock_pdata)
            prev_unpacked_by_guid[guid] = mock_unpacked
        # Note: headshot_hits/shots_recorded are derived from existing if needed
        # For simplicity, we assume we want to recalculate totals correctly.

    # 2. PROCESS NEW PAYLOADS
    seen_indices = set()
    for i, body in enumerate(payloads):
        round_info = body.get("round_info") or {}
        # Support both 'round_index' (v2 migration) and 'round' (live Lua script)
        round_index = int(round_info.get("round_index") or round_info.get("round") or (i + 1))
        while round_index in seen_indices:
            round_index += 1
        seen_indices.add(round_index)
        
        print(f"DEBUG: Processing round index: {round_index}")
        player_stats = body.get("player_stats") or {}
        obituaries = round_info.get("obituaries")
        damage_stats = round_info.get("damageStats")
        gamelog = body.get("gamelog")
        
        # Track class timeline for precise weapon mapping during unpack
        class_tracker = ClassTimelineTracker(gamelog or [])

        team_by_guid: dict[str, int] = {}
        
        # ... later in the final total stats loop we'll use this
        for g, pdata in player_stats.items():
            g_norm = g.strip().upper()
            g_master = aliases.get(g_norm, g_norm)
            try:
                team_by_guid[g_master] = int(pdata.get("team") or 0)
            except (TypeError, ValueError):
                team_by_guid[g_master] = 0

        for guid_key, pdata in player_stats.items():
            guid = guid_key.strip().upper()
            # Resolve Alias
            guid = aliases.get(guid, guid)

            name_raw = str(pdata.get("name") or "")
            display = strip_quake_colors(name_raw) or guid[:8]
            display_normalized = normalize_nick(name_raw) or display

            team = int(pdata.get("team") or 0)
            if team not in (1, 2):
                continue

            if guid not in player_db_by_guid:
                player = db.query(Player).filter(Player.guid == guid).one_or_none()
                if not player:
                    player = Player(guid=guid, display_name=display, raw_name_last=name_raw)
                    db.add(player)
                    db.flush()
                else:
                    # Update with cleaned name unless it's empty OR name is locked
                    if not player.name_locked:
                        player.display_name = display_normalized or player.display_name
                    player.raw_name_last = name_raw or player.raw_name_last
                player_db_by_guid[guid] = player
            else:
                player = player_db_by_guid[guid]
            
            # Record both the original cleaned name and the normalized one as aliases
            from app.models import PlayerAlias
            for name_to_record in set([display, display_normalized]):
                if not name_to_record: continue
                existing_alias = db.query(PlayerAlias).filter(PlayerAlias.player_id == player.id, PlayerAlias.alias == name_to_record).first()
                if not existing_alias:
                    db.add(PlayerAlias(player_id=player.id, alias=name_to_record))
                else:
                    existing_alias.last_seen = datetime.utcnow()

            # Determine match-wide team identity
            # If they join in Round 2, their Engine Team is inverted relative to Round 1.
            effective_team_r1 = team
            if team in (1, 2) and round_index % 2 == 0:
                effective_team_r1 = 3 - team

            if guid not in total_stats_by_guid:
                total_stats_by_guid[guid] = TotalStat(name_raw, display, team)
                if team in (1, 2):
                    first_team_by_guid[guid] = effective_team_r1
            else:
                # Record the first team they joined in this match (usually Round 1)
                # to keep the "Total Score" view consistent after side-swaps.
                if guid not in first_team_by_guid and team in (1, 2):
                    first_team_by_guid[guid] = effective_team_r1
            
            ts = total_stats_by_guid[guid]
            # --- EXTRACT METRICS (Protocol Dependent) ---
            gamelog = body.get("gamelog") or round_info.get("gamelog")

            # A) Event-Based Metrics (Modern Path)
            em = compute_event_metrics(
                player_guid=guid,
                obituaries=obituaries,
                damage_stats=damage_stats,
                team_by_guid=team_by_guid,
                gamelog=gamelog,
                aliases=aliases
            )

            # B) Engine-Based Summary Metrics (Legacy Path & Validation)
            ws_raw = pdata.get("weaponStats") or []
            unpacked = None
            
            dg = 0; dr = 0; tdg = 0; tdr = 0; gibs = 0; sk = 0; tk = 0; tg = 0; tpct = 0.0; xp = 0;
            kills = 0; deaths = 0; revives = 0; medkits = 0; ammo_packs = 0;

            if ws_raw:
                try:
                    unpacked = unpack_weapon_stats(ws_raw)
                    if unpacked:
                        dg   = unpacked.damage_given
                        dr   = unpacked.damage_received
                        tdg  = unpacked.team_damage_given
                        tdr  = unpacked.team_damage_received
                        gibs = unpacked.gibs
                        sk   = unpacked.self_kills
                        tk   = unpacked.team_kills
                        tg   = unpacked.team_gibs
                        tpct = unpacked.time_played_pct
                        xp   = unpacked.xp
                        
                        kills = unpacked.kills
                        deaths = unpacked.deaths
                except Exception as e:
                    print(f"DEBUG: Error unpacking weapon stats for {guid}: {e}")
            
            if not isinstance(ws_raw, list):
                ws_raw = []
                
            # Determine the primary class for this round for accurate weapon labeling
            primary_class = class_tracker.get_class_at(guid, 99999999999) # gets last known class
            if primary_class == "unknown":
                switches = pdata.get("class_switches") or []
                if switches:
                    primary_class = switches[-1].get("toClass") or "unknown"
                    
            unpacked = unpack_weapon_stats(ws_raw, primary_class)

            em = compute_event_metrics(guid, obituaries, damage_stats, team_by_guid, gamelog, aliases=aliases)
            
            # ALIGNMENT: Prefer event-based stats if available, fall back to pdata for legacy
            kills_raw = em.kills if em.kills > 0 else int(pdata.get("kills") or 0)
            deaths_all_raw = em.deaths if em.deaths > 0 else int(pdata.get("deaths") or 0) # total deaths from engine
            
            # Derived Combat Deaths: Total Deaths - Self Kills - Team Deaths
            sk_raw = 0
            tk_rec_raw = 0
            
            if unpacked:
                sk_raw = unpacked.self_kills
            elif em:
                sk_raw = em.self_kills
            
            if em:
                tk_rec_raw = em.team_deaths_received
            
            combat_deaths = max(0, deaths_all_raw - sk_raw - tk_rec_raw)

            dg = dr = tdg = tdr = gibs = sk = tk = tg = 0
            tpct = 0.0
            xp = 0
            if unpacked:
                dg = unpacked.damage_given
                dr = unpacked.damage_received
                tdg = unpacked.team_damage_given
                tdr = unpacked.team_damage_received
                gibs = unpacked.gibs
                sk = unpacked.self_kills
                tk = unpacked.team_kills
                tg = unpacked.team_gibs
                tpct = unpacked.time_played_pct
                xp = unpacked.xp

                for w in unpacked.weapons:
                    if w.slot not in ts.weapons:
                        ts.weapons[w.slot] = {
                            "slot": w.slot,
                            "name": w.name,
                            "hits": 0,
                            "shots": 0,
                            "kills": 0,
                            "deaths": 0,
                            "headshots": 0,
                        }
                    mw = ts.weapons[w.slot]
                    mw["hits"] = max(mw["hits"], w.hits)
                    mw["shots"] = max(mw["shots"], w.shots)
                    mw["kills"] = max(mw["kills"], w.kills)
                    mw["deaths"] = max(mw["deaths"], w.deaths)
                    mw["headshots"] = max(mw["headshots"], w.headshots)

            # Prioritize the granular support keys from the gamelog events (EventMetrics)
            revives = em.revives
            medkits = em.team_medpacks
            ammo_packs = em.team_ammopacks

            # Fallback to Engine weapon statistics (Oksii logic)
            # Now natively class-aware inside unpack_weapon_stats!
            if unpacked:
                if revives == 0: revives = unpacked.revives
                if medkits == 0: medkits = unpacked.medkits
                if ammo_packs == 0: ammo_packs = unpacked.ammopacks

            # Final fallbacks to master JSON payload keys if still zero
            if revives == 0: revives = int(pdata.get("revives") or 0)
            if medkits == 0: medkits = int(pdata.get("medkits") or 0)
            if ammo_packs == 0: ammo_packs = int(pdata.get("ammopacks") or 0)

            eff, kdr = _eff_kdr(kills_raw, combat_deaths)
            # Unified Efficiency calculation for the round row
            # Self-kills weighted at 0.25
            u_points = kills_raw + (revives * 0.33) + (dg / 100.0) + (xp * 0.1)
            u_actions = u_points + combat_deaths + (sk_raw * 0.25)
            u_eff = round((u_points / max(1, u_actions)) * 100.0, 1)

            spam_kills = 0
            if unpacked:
                # Synchronized spam filter for ET: Legacy 2.76 / Oksii indices:
                # 8:Panzer, 9:Bazooka, 10:Flame, 12/13:Mortar, 14:Dyna, 15:Airstrike, 16:Arty, 18:RifleGrenade, 19:Landmine
                spam_slots = {8, 9, 10, 12, 13, 14, 15, 16, 18, 19}
                spam_kills = sum(w.kills for w in unpacked.weapons if w.slot in spam_slots)

            hs_acc = hs_accuracy(em.headshot_hits, em.shots_recorded)

            dist_m = float(pdata.get("distance_travelled_meters") or 0.0)
            dist_sa = float(pdata.get("distance_travelled_spawn_avg") or 0.0)
            
            stances = pdata.get("stance_stats_seconds") or {}
            crouch = int(stances.get("in_crouch") or 0)
            prone = int(stances.get("in_prone") or 0)
            lean = int(stances.get("in_lean") or 0)
            mg_time = int(stances.get("in_mg") or 0)
            sprint_time = int(stances.get("in_sprint") or 0)
            disguise_time = int(stances.get("in_disguise") or 0)
            downed_time = int(stances.get("is_downed") or 0)
            
            classes_played = pdata.get("class_switches") or []
            # Robust fallback: if class_switches is missing (new modular Lua scripts), 
            # harvest from the gamelog events if they exist.
            if not classes_played and gamelog:
                for ev in gamelog:
                    # Lua sends 'player' as the GUID key in gamelog events
                    ev_player_raw = str(ev.get("player") or "").strip().upper()
                    ev_player = aliases.get(ev_player_raw, ev_player_raw)
                    if ev_player == guid:
                        label = ev.get("label")
                        if label in ("spawn", "class_change"):
                            cname = ev.get("class")
                            if cname:
                                classes_played.append({
                                    "toClass": cname,
                                    "timestamp": int(ev.get("unixtime") or ev.get("leveltime") or 0)
                                })
            
            classes_json = json.dumps(classes_played) if classes_played else None

            # Objective extraction from player_stats maps
            objs_extracted = []
            for o_key in ["obj_planted", "obj_defused", "obj_destroyed", "obj_repaired", "obj_taken", "obj_secured", "obj_returned", "obj_carrierkilled", "obj_flagcaptured", "obj_misc", "obj_escort"]:
                o_map = pdata.get(o_key) or {}
                for lt, o_data in o_map.items():
                    objs_extracted.append({
                        "type": o_key,
                        "objective": o_data.get("objective") or o_data.get("flag") or "unknown",
                        "leveltime": int(lt),
                        "unixtime": int(o_data.get("timestamp_unix") or 0)
                    })
            objs_json = json.dumps(objs_extracted) if objs_extracted else None

            # Modular v2.x metrics
            spawn_count = int(pdata.get("spawn_count") or 0)
            spd = pdata.get("player_speed") or {}
            ups_avg = float(spd.get("ups_avg") or 0.0)
            ups_peak = float(spd.get("ups_peak") or 0.0)

            # --- DELTA CALCULATION for Round Row ---
            # We must subtract previous rounds from cumulative session stats
            p_unpacked = prev_unpacked_by_guid.get(guid)
            
            # Weapon stats deltas
            round_weapons = []
            if unpacked:
                prev_ws = {w.slot: w for w in p_unpacked.weapons} if p_unpacked else {}
                for w in unpacked.weapons:
                    pw = prev_ws.get(w.slot)
                    # Use deltas for the per-round row, handling engine resets
                    round_weapons.append({
                        "slot": w.slot,
                        "name": w.name,
                        "hits": _calc_delta(w.hits, pw.hits if pw else 0),
                        "shots": _calc_delta(w.shots, pw.shots if pw else 0),
                        "kills": _calc_delta(w.kills, pw.kills if pw else 0),
                        "deaths": _calc_delta(w.deaths, pw.deaths if pw else 0),
                        "headshots": _calc_delta(w.headshots, pw.headshots if pw else 0),
                    })
            
            # --- TRUTH TRACK BIFURCATION ---
            if gamelog:
                # MODERN: Discrete Event-Summing (Single Source of Truth)
                r_dg = em.damage_given if hasattr(em, "damage_given") else _calc_delta(dg, p_unpacked.damage_given if p_unpacked else 0)
                r_dr = em.damage_received if hasattr(em, "damage_received") else _calc_delta(dr, p_unpacked.damage_received if p_unpacked else 0)
                r_tdg = _calc_delta(tdg, p_unpacked.team_damage_given if p_unpacked else 0)
                r_tdr = _calc_delta(tdr, p_unpacked.team_damage_received if p_unpacked else 0)
                
                r_gibs = _calc_delta(gibs, p_unpacked.gibs if p_unpacked else 0)
                r_tg = _calc_delta(tg, p_unpacked.team_gibs if p_unpacked else 0)
                r_xp = _calc_delta(xp, p_unpacked.xp if p_unpacked else 0)
                
                # These tactical fields are the absolute source of truth in the gamelog
                r_sk = em.self_kills
                r_tk = em.team_kills
                r_revives = em.revives
                r_medkits = em.team_medpacks
                r_ammo_packs = em.team_ammopacks
                r_kills = em.kills
                r_total_deaths = em.deaths
                r_sk = em.self_kills
                r_tk_rec = em.team_deaths_received
                r_combat_deaths = max(0, r_total_deaths - r_sk - r_tk_rec)
                r_time_played_pct = _calc_delta(tpct, p_unpacked.time_played_pct if p_unpacked else 0.0)
            else:
                # LEGACY: Cumulative Engine Deltas
                r_dg = _calc_delta(dg, p_unpacked.damage_given if p_unpacked else 0)
                r_dr = _calc_delta(dr, p_unpacked.damage_received if p_unpacked else 0)
                r_tdg = _calc_delta(tdg, p_unpacked.team_damage_given if p_unpacked else 0)
                r_tdr = _calc_delta(tdr, p_unpacked.team_damage_received if p_unpacked else 0)
                r_gibs = _calc_delta(gibs, p_unpacked.gibs if p_unpacked else 0)
                r_sk = _calc_delta(sk, p_unpacked.self_kills if p_unpacked else 0)
                r_tk = _calc_delta(tk, p_unpacked.team_kills if p_unpacked else 0)
                r_tg = _calc_delta(tg, p_unpacked.team_gibs if p_unpacked else 0)
                r_xp = _calc_delta(xp, p_unpacked.xp if p_unpacked else 0)
                r_revives = em.revives # Fallback Syringe count calculated in EventMetrics
                r_medkits = em.team_medpacks
                r_ammo_packs = em.team_ammopacks
                r_kills = _calc_delta(kills_raw, p_unpacked.kills if p_unpacked else 0)
                # Engine total deaths delta
                r_total_deaths = _calc_delta(deaths_all_raw, p_unpacked.deaths if p_unpacked else 0)
                r_sk = _calc_delta(sk_raw, p_unpacked.self_kills if p_unpacked else 0)
                r_tk_rec = em.team_deaths_received # Event-based is always a delta
                r_combat_deaths = max(0, r_total_deaths - r_sk - r_tk_rec)
                r_time_played_pct = _calc_delta(tpct, p_unpacked.time_played_pct if p_unpacked else 0.0)
            
            p_prev_pdata = getattr(p_unpacked, "pdata_ref", None) if p_unpacked else None
            r_spawn_count = _calc_delta(spawn_count, int(p_prev_pdata.get("spawn_count") or 0) if p_prev_pdata else 0)
            
            # Stances and Distance deltas
            r_dist_m = _calc_delta(dist_m, float(p_prev_pdata.get("distance_travelled_meters") or 0.0) if p_prev_pdata else 0.0)
            r_crouch = _calc_delta(crouch, int((p_prev_pdata.get("stance_stats_seconds") or {}).get("in_crouch") or 0) if p_prev_pdata else 0)
            r_prone = _calc_delta(prone, int((p_prev_pdata.get("stance_stats_seconds") or {}).get("in_prone") or 0) if p_prev_pdata else 0)
            r_lean = _calc_delta(lean, int((p_prev_pdata.get("stance_stats_seconds") or {}).get("in_lean") or 0) if p_prev_pdata else 0)
            r_mg_seconds = _calc_delta(mg_time, int((p_prev_pdata.get("stance_stats_seconds") or {}).get("in_mg") or 0) if p_prev_pdata else 0)
            r_sprint_seconds = _calc_delta(sprint_time, int((p_prev_pdata.get("stance_stats_seconds") or {}).get("in_sprint") or 0) if p_prev_pdata else 0)
            r_disguise_seconds = _calc_delta(disguise_time, int((p_prev_pdata.get("stance_stats_seconds") or {}).get("in_disguise") or 0) if p_prev_pdata else 0)
            r_downed_seconds = _calc_delta(downed_time, int((p_prev_pdata.get("stance_stats_seconds") or {}).get("is_downed") or 0) if p_prev_pdata else 0)

            eff_round, kdr_round = _eff_kdr(r_kills, r_combat_deaths)
            u_eff_round = _calculate_unified_eff(r_kills, r_revives, r_dg, r_xp, r_combat_deaths, r_sk)

            pms_round = PlayerMatchStats(
                match_id=match_row.id,
                player_id=player.id,
                round_index=round_index,
                team=team, 
                kills=r_kills,
                deaths=r_combat_deaths,
                kdr=kdr_round,
                eff=eff_round,
                unified_eff=u_eff_round,
                damage_given=r_dg,
                damage_received=r_dr,
                team_damage_given=r_tdg,
                team_damage_received=r_tdr,
                headshots=em.headshot_hits, # Already a delta from EventMetrics
                gibs=r_gibs,
                self_kills=r_sk,
                team_kills=r_tk,
                team_deaths_received=r_tk_rec,
                team_gibs=r_tg,
                time_played_pct=r_time_played_pct,
                xp=r_xp,
                revives=r_revives,
                medkits=r_medkits,
                team_medpacks=r_ammo_packs,
                spam_kills=spam_kills, # round-specific
                distance_travelled_meters=r_dist_m,
                distance_travelled_spawn_avg=dist_sa, # session-avg typically
                spawn_count=r_spawn_count,
                speed_ups_avg=ups_avg,
                speed_ups_peak=ups_peak,
                crouched_seconds=r_crouch,
                proned_seconds=r_prone,
                leaned_seconds=r_lean,
                in_mg_seconds=r_mg_seconds,
                in_sprint_seconds=r_sprint_seconds,
                in_disguise_seconds=r_disguise_seconds,
                is_downed_seconds=r_downed_seconds,
                shoves_given=em.shoves_given,
                shoves_received=em.shoves_received,
                pickup_medkits=em.pickup_medkits,
                pickup_ammopacks=em.pickup_ammopacks,
                classes_played_json=classes_json,
                objectives_json=objs_json,
                hs_accuracy_event=hs_acc,
                nemesis_json=nemesis_to_json(em),
                weapon_breakdown_json=json.dumps(round_weapons) if round_weapons else None,
                name_raw=name_raw,
            )
            db.add(pms_round)
            
            # Store current state for next round's delta
            if unpacked:
                unpacked.kills = kills_raw
                unpacked.deaths = deaths_all_raw
                unpacked.pdata_ref = pdata # Store the whole dict for next round's stance/dist deltas
                unpacked.self_kills = sk_raw
                unpacked.revives = revives
                unpacked.medkits = medkits
                unpacked.ammopacks = ammo_packs
                setattr(unpacked, "pdata_ref", pdata) # hack to store raw pdata for numeric deltas
                prev_unpacked_by_guid[guid] = unpacked

            # Add to total (Cumulative Summation of Deltas)
            # This is robust to session resets/reconnections between rounds
            ts.damage_given += r_dg
            ts.damage_received += r_dr
            ts.team_damage_given += r_tdg
            ts.team_damage_received += r_tdr
            ts.gibs += r_gibs
            ts.self_kills += r_sk
            ts.team_kills += r_tk
            ts.team_gibs += r_tg
            ts.xp += r_xp
            ts.spawn_count += r_spawn_count
            ts.speed_ups_avg = max(ts.speed_ups_avg, ups_avg) # speed is session-wide peak usually
            ts.speed_ups_peak = max(ts.speed_ups_peak, ups_peak)
            ts.distance_travelled_spawn_avg = max(ts.distance_travelled_spawn_avg, dist_sa)
            ts.distance_travelled_meters += r_dist_m
            ts.crouched_seconds += r_crouch
            ts.proned_seconds += r_prone
            ts.leaned_seconds += r_lean
            
            ts.kills += r_kills
            ts.deaths += r_combat_deaths
            ts.revives += r_revives
            ts.medkits += r_medkits
            ts.team_medpacks += r_ammo_packs
            ts.team_deaths_received += r_tk_rec
            ts.headshot_hits += em.headshot_hits
            ts.shots_recorded += em.shots_recorded

            ts.in_mg_seconds += r_mg_seconds
            ts.in_sprint_seconds += r_sprint_seconds
            ts.in_disguise_seconds += r_disguise_seconds
            ts.is_downed_seconds += r_downed_seconds
            ts.shoves_given += em.shoves_given
            ts.shoves_received += em.shoves_received
            ts.pickup_medkits += em.pickup_medkits
            ts.pickup_ammopacks += em.pickup_ammopacks

            ts.spam_kills += spam_kills
            ts.classes_played_lists.extend(classes_played)
            ts.objectives_list.extend(objs_extracted)
            ts.time_played_pcts.append(tpct)

    # 3. WINNER is already determined and persisted at the start of ingest_match_payloads.
    # No further re-determination is needed here.

    # Insert totals
    performances: list[PlayerPerformance] = []

    for guid, ts in total_stats_by_guid.items():
        player = player_db_by_guid[guid]
        
        avg_time = sum(ts.time_played_pcts) / len(ts.time_played_pcts) if ts.time_played_pcts else 0.0
        eff, kdr = _eff_kdr(ts.kills, ts.deaths)
        u_eff = _calculate_unified_eff(ts.kills, ts.revives, ts.damage_given, ts.xp, ts.deaths, ts.self_kills)
        hs_acc = hs_accuracy(ts.headshot_hits, ts.shots_recorded)

        num_rounds = len(ts.time_played_pcts) if ts.time_played_pcts else 1
        
        pms_total = PlayerMatchStats(
            match_id=match_row.id,
            player_id=player.id,
            round_index=0,
            team=first_team_by_guid.get(guid, ts.team), # Use their Round 1 team for the Total view
            kills=ts.kills,
            deaths=ts.deaths,
            kdr=kdr,
            eff=eff,
            unified_eff=u_eff,
            damage_given=ts.damage_given,
            damage_received=ts.damage_received,
            team_damage_given=ts.team_damage_given,
            team_damage_received=ts.team_damage_received,
            team_deaths_received=ts.team_deaths_received,
            headshots=ts.headshot_hits,
            gibs=ts.gibs,
            self_kills=ts.self_kills,
            team_kills=ts.team_kills,
            team_gibs=ts.team_gibs,
            time_played_pct=avg_time,
            xp=ts.xp,
            revives=ts.revives,
            medkits=ts.medkits,
            team_medpacks=ts.team_medpacks,
            spam_kills=ts.spam_kills,
            distance_travelled_meters=ts.distance_travelled_meters,
            spawn_count=ts.spawn_count,
            speed_ups_avg=ts.speed_ups_avg / num_rounds,
            speed_ups_peak=ts.speed_ups_peak,
            distance_travelled_spawn_avg=ts.distance_travelled_spawn_avg / num_rounds,
            crouched_seconds=ts.crouched_seconds,
            proned_seconds=ts.proned_seconds,
            leaned_seconds=ts.leaned_seconds,
            classes_played_json=json.dumps(ts.classes_played_lists) if ts.classes_played_lists else None,
            hs_accuracy_event=hs_acc,
            nemesis_json=None,
            weapon_breakdown_json=_weapon_breakdown_json_from_dict(ts.weapons),
            name_raw=ts.name_raw,
        )
        db.add(pms_total)

        gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == player.id).one_or_none()
        mu = gr.mu if gr else 25.0
        sigma = gr.sigma if gr else 8.333

        # Weapon Accuracy: Total Hits / Total Shots fired for CORE weapons only
        core_weapon_slots = {2, 3, 4, 5, 6, 7, 22, 23, 24, 25, 26}
        total_hits = 0
        total_shots = 0
        for slot, w in ts.weapons.items():
            if slot in core_weapon_slots:
                total_hits += w.get("hits", 0)
                total_shots += w.get("shots", 0)
        
        weapon_acc = (total_hits / total_shots * 100.0) if total_shots > 0 else 0.0

        # Determine if primarily a medic (played Medic in any round)
        is_medic = any(str(c.get("toClass")) == "1" for c in ts.classes_played_lists)

        performances.append(
            PlayerPerformance(
                player_id=player.id,
                team=ts.team,
                xp=float(ts.xp),
                kills=ts.kills,
                damage_given=ts.damage_given,
                revives=float(ts.revives),
                deaths=ts.deaths,
                self_kills=ts.self_kills,
                mu=mu,
                sigma=sigma,
                is_medic=is_medic,
            )
        )

    rating_results = calculate_openskill_ratings(performances, winner_team)

    for res in rating_results:
        gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == res.player_id).one_or_none()
        if not gr:
            gr = PlayerGatherRating(player_id=res.player_id, current_rating=1500.0, mu=25.0, sigma=8.333)
            db.add(gr)
            db.flush()
        
        # Get match count (total including this one)
        m_count = db.query(PlayerMatchStats).filter(
            PlayerMatchStats.player_id == res.player_id, 
            PlayerMatchStats.round_index == 0
        ).count() + 1

        new_rating = compute_display_rating(res.new_mu, res.new_sigma, match_count=m_count)
        
        gr.mu = res.new_mu
        gr.sigma = res.new_sigma

        hist = PlayerGatherRatingHistory(
            player_id=res.player_id,
            match_id=match_row.id,
            rating=new_rating,
            delta=res.delta_rating,
            mu=res.new_mu,
            sigma=res.new_sigma,
        )
        db.add(hist)
        gr.current_rating = new_rating

    # Calculate MVP using the same Unified Efficiency logic as SR
    best_score = -1.0
    mvp_pid = None
    for res in rating_results:
        perf = next((p for p in performances if p.player_id == res.player_id), None)
        if perf:
            score = get_performance_score(perf)
            
            # Tiny bias for winners to break ties
            if winner_team > 0 and perf.team == winner_team:
                score += 0.01
            
            if score > best_score:
                best_score = score
                mvp_pid = res.player_id
    
    match_row.mvp_player_id = mvp_pid
    db.commit()
    db.refresh(match_row)
    return match_row


def recalculate_all_ratings(db: Session):
    """
    Clears all rating history and resets all player ratings to baseline,
    then iterates through all matches chronologically to rebuild the SR state.
    """
    # 1. Reset all player ratings to baseline (mu=25.0, sigma=8.333)
    db.query(PlayerGatherRating).update({
        "current_rating": 1500.0,
        "mu": 25.0,
        "sigma": 8.333
    })
    
    # 2. Delete all rating history
    db.query(PlayerGatherRatingHistory).delete()
    db.flush()

    # 3. Initialize match counts for hybrid sigma logic
    match_counts: dict[int, int] = defaultdict(int)

    # 4. Load all matches in chronological order
    matches = db.query(Match).order_by(Match.round_start_unix.asc()).all()

    for m in matches:
        # Get total performance rows (round_index=0) for this match
        stats_rows = db.query(PlayerMatchStats).filter(
            PlayerMatchStats.match_id == m.id,
            PlayerMatchStats.round_index == 0
        ).all()

        if not stats_rows:
            continue

        # Re-derive winner_team from stored MatchPayload rounds.
        # The m.winner_team field was historically set from Round 1 only (corrupt for SW matches).
        # By re-running _determine_winner_team with all stored rounds, we get the correct result.
        payload_rows = (
            db.query(MatchPayload)
            .filter(MatchPayload.match_id == m.id)
            .order_by(MatchPayload.round_number)
            .all()
        )
        if payload_rows:
            stored_payloads = [json.loads(pr.payload) for pr in payload_rows]
            derived_winner, d1, d2 = _determine_winner_team(stored_payloads)
        else:
            # No relational payloads: fall back to stored value (legacy matches)
            derived_winner = m.winner_team
            d1, d2 = None, None

        # Persist the corrected winner and durations so future recalcs are self-healing
        if derived_winner != m.winner_team or d1 != m.round1_duration or d2 != m.round2_duration:
            print(f"DEBUG: Correcting match {m.id}: winner_team={derived_winner}, d1={d1}, d2={d2}")
            m.winner_team = derived_winner
            m.round1_duration = d1
            m.round2_duration = d2

        # Engine Team ID -> Pinned Team ID mapping for this match.
        # Historically, we hardcoded {1:1, 2:2}, which flipped 50% of matches.
        # Now we use the round1_alpha_side metadata to correctly map.
        engine_to_pinned = {1: 1, 2: 2} # Default
        if payload_rows:
            p1 = json.loads(payload_rows[0].payload)
            p1_stats = p1.get("player_stats") or {}
            if p1_stats:
                # Sample one player to see their engine side
                sample_guid = next(iter(p1_stats))
                sample_pdata = p1_stats[sample_guid]
                engine_team = int(sample_pdata.get("team") or 0)
                engine_side = int(sample_pdata.get("side") or 0) # 1=Axis, 2=Allies
                
                if engine_team in (1, 2) and engine_side in (1, 2):
                    # We know this player's Engine Team and their Side in R1.
                    # We also know Alpha's Side in R1.
                    alpha_side_r1 = m.round1_alpha_side or 1 # Assume Alpha=Axis if missing
                    
                    if engine_side == alpha_side_r1:
                        # This Engine Team was Alpha
                        engine_to_pinned = {engine_team: 1, (3 - engine_team): 2}
                    else:
                        # This Engine Team was Beta
                        engine_to_pinned = {engine_team: 2, (3 - engine_team): 1}

        performances = []
        for row in stats_rows:
            gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == row.player_id).one_or_none()
            if not gr:
                gr = PlayerGatherRating(player_id=row.player_id, current_rating=1500.0, mu=25.0, sigma=8.333)
                db.add(gr)
                db.flush()
            
            # Weapon accuracy logic
            core_weapon_slots = {2, 3, 4, 5, 6, 7, 22, 23, 24, 25, 26}
            total_hits = 0
            total_shots = 0
            if row.weapon_breakdown_json:
                try:
                    wb = json.loads(row.weapon_breakdown_json)
                    if isinstance(wb, list):
                        for w in wb:
                            if w.get("slot") in core_weapon_slots:
                                total_hits += w.get("hits", 0)
                                total_shots += w.get("shots", 0)
                    elif isinstance(wb, dict):
                        for slot_s, w in wb.items():
                            if int(slot_s) in core_weapon_slots:
                                total_hits += w.get("hits", 0)
                                total_shots += w.get("shots", 0)
                except:
                    pass
            
            performances.append(PlayerPerformance(
                player_id=row.player_id,
                team=row.team, # Engine Team (1 or 2)
                xp=float(row.xp),
                kills=row.kills,
                damage_given=row.damage_given,
                revives=row.revives,
                deaths=row.deaths,
                self_kills=row.self_kills,
                mu=gr.mu,
                sigma=gr.sigma
            ))

        # Re-map the derived_winner (Engine) to Pinned (Alpha/Beta)
        # If derived_winner is Engine Team 1, and Engine Team 1 is Alpha, then final_winner is 1.
        final_winner = engine_to_pinned.get(derived_winner, derived_winner)
        
        # Persist corrected winner and durations
        if final_winner != m.winner_team or d1 != m.round1_duration or d2 != m.round2_duration:
            m.winner_team = final_winner
            m.round1_duration = d1
            m.round2_duration = d2

        rating_results = calculate_openskill_ratings(performances, derived_winner)

        for res in rating_results:
            gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == res.player_id).one()
            
            # Increment match count for hybrid sigma
            match_counts[res.player_id] += 1
            
            new_rating = compute_display_rating(res.new_mu, res.new_sigma, match_count=match_counts[res.player_id])
            delta = res.delta_rating
            
            gr.mu = res.new_mu
            gr.sigma = res.new_sigma
            gr.current_rating = new_rating

            hist = PlayerGatherRatingHistory(
                player_id=res.player_id,
                match_id=m.id,
                rating=new_rating,
                delta=delta,
                mu=res.new_mu,
                sigma=res.new_sigma,
            )
            db.add(hist)
        
        db.commit() # Commit after each match to avoid long transaction locks
    
    print(f"Global rating recalculation complete for {len(matches)} matches.")
