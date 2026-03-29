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
)
from app.parsers.events import compute_event_metrics, hs_accuracy, nemesis_to_json
from app.parsers.names import strip_quake_colors
from app.parsers.weapon_stats import UnpackedWeaponStats, revives_from_unpacked, unpack_weapon_stats
from app.rating import PlayerPerformance, calculate_openskill_ratings, compute_display_rating


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


def _eff_kdr(kills: int, deaths: int, self_kills: int = 0) -> tuple[float, float]:
    eff = round(100.0 * kills / max(1, kills + deaths + self_kills), 1)
    kdr = round(kills / max(1, deaths), 2)
    return eff, kdr


def _calculate_unified_eff(kills: int, revives: int, ammo: int, xp: int, deaths: int, self_kills: int) -> float:
    # Unified Points formula from rating.py
    points = kills + revives + (ammo * 0.25) + (xp * 0.10)
    total_actions = points + deaths + self_kills
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


def ingest_match_payloads(db: Session, payloads: list[dict[str, Any]], store_raw: bool = True) -> Match:
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

    match_id = str(metadata_primary.get("matchID") or round_info_primary.get("matchID") or primary.get("matchID") or "")
    if not match_id:
        raise ValueError("missing matchID")

    print(f"DEBUG: Ingesting payload for matchID: {match_id}")

    mapname = str(metadata_primary.get("mapname") or round_info_primary.get("mapname") or "")
    
    # Exclude certain maps from tracking
    if mapname.lower() in ("mp_sillyctf", "mp_valhalla"):
        print(f"DEBUG: Skipping matchID {match_id} because map '{mapname}' is in exclusion list.")
        # We need to return something that won't break the caller. 
        # Returning a dummy match or raising SkipMatch might be better.
        # For now, let's assume the caller handles Match objects.
        # A more robust way would be to return None and check in the router.
        return None

    # Winner determination logic
    winner_team = 0
    if len(payloads) == 2:
        # Stopwatch logic: compare durations of winning rounds
        r1 = payloads[0].get("round_info", {})
        r2 = payloads[1].get("round_info", {})
        w1 = int(r1.get("winnerteam") or 0)
        w2 = int(r2.get("winnerteam") or 0)
        
        # Calculate durations in seconds
        d1 = int(r1.get("round_end_unix") or 0) - int(r1.get("round_start_unix") or 0)
        d2 = int(r2.get("round_end_unix") or 0) - int(r2.get("round_start_unix") or 0)
        
        if w1 > 0 and w2 > 0 and w1 != w2:
            # Both teams won their round. Faster duration wins the match.
            if d1 > 0 and d2 > 0:
                winner_team = w1 if d1 <= d2 else w2
            else:
                winner_team = w2 # Fallback to last round if durations missing
        elif w1 > 0 and w2 <= 0:
            winner_team = w1
        elif w2 > 0:
            winner_team = w2
        else:
            winner_team = w2 # Fallback
    else:
        # Single round or more than 2 rounds: take the last known result
        winner_team = int(payloads[-1].get("round_info", {}).get("winnerteam") or round_info_primary.get("winnerteam") or 0)
    
    rs, _ = get_epoch(payloads[0])
    _, re = get_epoch(payloads[-1])

    # 1. Primary lookup by exact Match ID
    existing = db.query(Match).filter(Match.match_id == match_id).one_or_none()
    
    if not existing:
        # 2. Heuristic: Check for a recent match on the same map (within 30 mins)
        # This allows Round 2 to merge even if it was assigned a different Match ID.
        now_unix = int(datetime.utcnow().timestamp())
        recent_threshold = now_unix - (30 * 60)
        
        recent_match = (
            db.query(Match)
            .filter(Match.mapname == mapname)
            .filter(Match.round_end_unix > recent_threshold)
            .order_by(Match.round_end_unix.desc())
            .first()
        )
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
        
        # Delete only the rounds we are overwriting (plus the total row at round_index=0)
        db.query(PlayerMatchStats).filter(
            PlayerMatchStats.match_id == existing.id,
            PlayerMatchStats.round_index.in_([0] + processing_round_indices)
        ).delete()
        
        existing.mapname = mapname
        # Note: winner_team will be recalculated later if needed
        existing.round_start_unix = min(existing.round_start_unix, rs)
        existing.round_end_unix = max(existing.round_end_unix, re)
        match_row = existing
        db.flush()
    else:
        print(f"DEBUG: Creating new match record for matchID {match_id}")
        match_row = Match(
            match_id=match_id,
            mapname=mapname,
            winner_team=winner_team,
            round_start_unix=rs,
            round_end_unix=re,
            raw_payload=json.dumps(payloads),
        )
        db.add(match_row)
        db.flush()

    # To calculate total stats, we keep track of values per guid
    class TotalStat:
        def __init__(self, name_raw: str, display: str, team: int):
            self.name_raw = name_raw
            self.display = display
            self.team = team
            self.kills = 0
            self.deaths = 0
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
            self.classes_played_lists = []
            self.weapons: dict[int, dict] = {}

    # Map to accumulate totals across ALL rounds (existing in DB + new in payloads)
    total_stats_by_guid: dict[str, TotalStat] = {}
    player_db_by_guid: dict[str, Player] = {}
    # Map to track cumulative session state *immediately before* the current round
    prev_unpacked_by_guid: dict[str, UnpackedWeaponStats] = {}

    # 1. LOAD EXISTING STATS FROM DB (rounds we are NOT overwriting)
    existing_stats = db.query(PlayerMatchStats).filter(
        PlayerMatchStats.match_id == match_row.id,
        PlayerMatchStats.round_index > 0
    ).all()

    for row in existing_stats:
        p = row.player
        guid = p.guid
        player_db_by_guid[guid] = p
        if guid not in total_stats_by_guid:
            total_stats_by_guid[guid] = TotalStat(row.name_raw or "", p.display_name or "", row.team)
        
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
        if row.classes_played_json:
            ts.classes_played_lists.extend(json.loads(row.classes_played_json))
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
                xp=row.xp
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
    for i, body in enumerate(payloads):
        round_info = body.get("round_info") or {}
        # Support both 'round_index' (v2 migration) and 'round' (live Lua script)
        round_index = int(round_info.get("round_index") or round_info.get("round") or (i + 1))
        print(f"DEBUG: Processing round index: {round_index}")
        player_stats = body.get("player_stats") or {}
        obituaries = round_info.get("obituaries")
        damage_stats = round_info.get("damageStats")
        gamelog = body.get("gamelog")

        team_by_guid: dict[str, int] = {}
        first_team_by_guid: dict[str, int] = {} # Fix: Track the team they started the match with
        
        # ... later in the final total stats loop we'll use this
        for g, pdata in player_stats.items():
            try:
                team_by_guid[g.strip().upper()] = int(pdata.get("team") or 0)
            except (TypeError, ValueError):
                team_by_guid[g.strip().upper()] = 0

        for guid_key, pdata in player_stats.items():
            guid = guid_key.strip().upper()
            # Resolve Alias
            guid = aliases.get(guid, guid)

            name_raw = str(pdata.get("name") or "")
            display = strip_quake_colors(name_raw) or guid[:8]

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
                    player.display_name = display or player.display_name
                    player.raw_name_last = name_raw or player.raw_name_last
                player_db_by_guid[guid] = player
            else:
                player = player_db_by_guid[guid]
            
            # Record alias
            from app.models import PlayerAlias
            existing_alias = db.query(PlayerAlias).filter(PlayerAlias.player_id == player.id, PlayerAlias.alias == display).first()
            if not existing_alias:
                db.add(PlayerAlias(player_id=player.id, alias=display))
            else:
                existing_alias.last_seen = datetime.utcnow()

            # Determine match-wide team identity
            # We prioritize the current round's team from player_stats
            # but fall back to the generic map if needed.
            if guid not in total_stats_by_guid:
                total_stats_by_guid[guid] = TotalStat(name_raw, display, team)
                if team in (1, 2):
                    first_team_by_guid[guid] = team
            else:
                # Record the first team they joined in this match (usually Round 1)
                # to keep the "Total Score" view consistent after side-swaps.
                if guid not in first_team_by_guid and team in (1, 2):
                    first_team_by_guid[guid] = team
            
            ts = total_stats_by_guid[guid]

            ws_raw = pdata.get("weaponStats") or []
            if not isinstance(ws_raw, list):
                ws_raw = []
            unpacked = unpack_weapon_stats(ws_raw)

            em = compute_event_metrics(guid, obituaries, damage_stats, team_by_guid, gamelog, aliases=aliases)
            
            # ALIGNMENT: Prefer event-based stats if available, fall back to pdata for legacy
            kills = em.kills if em.kills > 0 else int(pdata.get("kills") or 0)
            deaths = em.deaths if em.deaths > 0 else int(pdata.get("deaths") or 0)

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

            eff, kdr = _eff_kdr(kills, deaths, sk)
            revives = em.revives
            medkits = em.team_medpacks
            ammo_packs = em.team_ammopacks

            # Fallbacks for legacy scripts where events might be missing
            if revives == 0 and not gamelog:
                revives = revives_from_unpacked(unpacked) or int(pdata.get("revives") or 0)
            if medkits == 0 and not gamelog:
                medkits = int(pdata.get("medkits") or 0)
            if ammo_packs == 0 and not gamelog:
                ammo_packs = int(pdata.get("team_medpacks") or 0) # Historical label
            
            # Unified Efficiency calculation for the round row (v4 logic)
            # (kills + revives + ammo*0.25 + meds*0.25? No, user says both are trackable, 
            # let's use the same point value for both support packs)
            u_points = kills + revives + (ammo_packs * 0.25) + (medkits * 0.25) + (xp * 0.10)
            u_actions = u_points + deaths + sk
            u_eff = round((u_points / max(1, u_actions)) * 100.0, 1)

            spam_kills = 0
            if unpacked:
                spam_slots = {8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
                spam_kills = sum(w.kills for w in unpacked.weapons if w.slot in spam_slots)

            hs_acc = hs_accuracy(em.headshot_hits, em.shots_recorded)

            dist_m = float(pdata.get("distance_travelled_meters") or 0.0)
            dist_sa = float(pdata.get("distance_travelled_spawn_avg") or 0.0)
            
            stances = pdata.get("stance_stats_seconds") or {}
            crouch = int(stances.get("in_crouch") or 0)
            prone = int(stances.get("in_prone") or 0)
            lean = int(stances.get("in_lean") or 0)
            
            classes_played = pdata.get("class_switches") or []
            # Robust fallback: if class_switches is missing (new modular Lua scripts), 
            # harvest from the gamelog events if they exist.
            if not classes_played and gamelog:
                for ev in gamelog:
                    # Lua sends 'player' as the GUID key in gamelog events
                    ev_player = str(ev.get("player") or "").strip().upper()
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
                    # Use deltas for the per-round row
                    round_weapons.append({
                        "slot": w.slot,
                        "name": w.name,
                        "hits": w.hits - (pw.hits if pw else 0),
                        "shots": w.shots - (pw.shots if pw else 0),
                        "kills": w.kills - (pw.kills if pw else 0),
                        "deaths": w.deaths - (pw.deaths if pw else 0),
                        "headshots": w.headshots - (pw.headshots if pw else 0),
                    })
            
            # Other session deltas (Damage, Gibs, XP)
            r_dg = dg - (p_unpacked.damage_given if p_unpacked else 0)
            r_dr = dr - (p_unpacked.damage_received if p_unpacked else 0)
            r_tdg = tdg - (p_unpacked.team_damage_given if p_unpacked else 0)
            r_tdr = tdr - (p_unpacked.team_damage_received if p_unpacked else 0)
            r_gibs = gibs - (p_unpacked.gibs if p_unpacked else 0)
            r_sk = sk - (p_unpacked.self_kills if p_unpacked else 0)
            r_tk = tk - (p_unpacked.team_kills if p_unpacked else 0)
            r_tg = tg - (p_unpacked.team_gibs if p_unpacked else 0)
            r_xp = xp - (p_unpacked.xp if p_unpacked else 0)
            r_revives = revives - (revives_from_unpacked(p_unpacked) if p_unpacked else 0)
            r_spawn_count = spawn_count - (int(p_prev_data.get("spawn_count") or 0) if (p_prev_data := getattr(p_unpacked, "pdata_ref", None)) else 0)
            
            # Stances and Distance deltas
            r_dist_m = dist_m - (float(p_prev_data.get("distance_travelled_meters") or 0.0) if (p_prev_data := getattr(p_unpacked, "pdata_ref", None)) else 0.0)
            r_crouch = crouch - (int((p_prev_data.get("stance_stats_seconds") or {}).get("in_crouch") or 0) if (p_prev_data := getattr(p_unpacked, "pdata_ref", None)) else 0)
            r_prone = prone - (int((p_prev_data.get("stance_stats_seconds") or {}).get("in_prone") or 0) if (p_prev_data := getattr(p_unpacked, "pdata_ref", None)) else 0)
            r_lean = lean - (int((p_prev_data.get("stance_stats_seconds") or {}).get("in_lean") or 0) if (p_prev_data := getattr(p_unpacked, "pdata_ref", None)) else 0)

            eff_round, kdr_round = _eff_kdr(kills, deaths, r_sk) # kills/deaths are already round-specific

            pms_round = PlayerMatchStats(
                match_id=match_row.id,
                player_id=player.id,
                round_index=round_index,
                team=team, # Use the round-specific team, not the match-accumulated one
                kills=kills, # round-specific
                deaths=deaths, # round-specific
                kdr=kdr_round,
                eff=eff_round,
                unified_eff=u_eff,
                damage_given=r_dg,
                damage_received=r_dr,
                team_damage_given=r_tdg,
                team_damage_received=r_tdr,
                headshots=em.headshot_hits,
                gibs=r_gibs,
                self_kills=r_sk,
                team_kills=r_tk,
                team_gibs=r_tg,
                time_played_pct=tpct - (p_unpacked.time_played_pct if p_unpacked else 0.0),
                xp=r_xp,
                revives=r_revives,
                medkits=medkits,
                team_medpacks=ammo_packs,
                spam_kills=spam_kills, # round-specific
                distance_travelled_meters=r_dist_m,
                distance_travelled_spawn_avg=dist_sa, # session-avg typically
                spawn_count=r_spawn_count,
                speed_ups_avg=ups_avg,
                speed_ups_peak=ups_peak,
                crouched_seconds=r_crouch,
                proned_seconds=r_prone,
                leaned_seconds=r_lean,
                classes_played_json=classes_json,
                hs_accuracy_event=hs_acc,
                nemesis_json=nemesis_to_json(em),
                weapon_breakdown_json=_weapon_breakdown_json_from_dict({w["slot"]: w for w in round_weapons}) if round_weapons else None,
                name_raw=name_raw,
            )
            db.add(pms_round)
            
            # Store current state for next round's delta
            if unpacked:
                setattr(unpacked, "pdata_ref", pdata) # hack to store raw pdata for numeric deltas
                prev_unpacked_by_guid[guid] = unpacked

            # Add to total (Cumulative Session Stats - using max)
            ts.damage_given = max(ts.damage_given, dg)
            ts.damage_received = max(ts.damage_received, dr)
            ts.team_damage_given = max(ts.team_damage_given, tdg)
            ts.team_damage_received = max(ts.team_damage_received, tdr)
            ts.gibs = max(ts.gibs, gibs)
            ts.self_kills = max(ts.self_kills, sk)
            ts.team_kills = max(ts.team_kills, tk)
            ts.team_gibs = max(ts.team_gibs, tg)
            ts.xp = max(ts.xp, xp)
            ts.spawn_count = max(ts.spawn_count, spawn_count)
            ts.speed_ups_avg = max(ts.speed_ups_avg, ups_avg)
            ts.speed_ups_peak = max(ts.speed_ups_peak, ups_peak)
            ts.distance_travelled_spawn_avg = max(ts.distance_travelled_spawn_avg, dist_sa)
            ts.distance_travelled_meters = max(ts.distance_travelled_meters, dist_m)
            ts.crouched_seconds = max(ts.crouched_seconds, crouch)
            ts.proned_seconds = max(ts.proned_seconds, prone)
            ts.leaned_seconds = max(ts.leaned_seconds, lean)
            
            # Add to total (Event-based or Delta-based Stats)
            if gamelog:
                ts.kills += em.kills
                ts.deaths += em.deaths
                ts.revives += em.revives
                ts.medkits += em.team_medpacks
                ts.team_medpacks += em.team_ammopacks # Now Ammo
                ts.headshots += em.headshot_hits
                ts.headshot_hits += em.headshot_hits
                ts.shots_recorded += em.shots_recorded
            else:
                # Legacy fallback: use max for session totals if we don't have a gamelog to aggregate
                ts.kills = max(ts.kills, kills)
                ts.deaths = max(ts.deaths, deaths)
                ts.revives = max(ts.revives, revives)
                ts.medkits = max(ts.medkits, medkits)
                ts.team_medpacks = max(ts.team_medpacks, ammo_packs)
                ts.headshots = max(ts.headshots, em.headshot_hits)
                ts.headshot_hits = max(ts.headshot_hits, em.headshot_hits)
                ts.shots_recorded = max(ts.shots_recorded, em.shots_recorded)

            ts.spam_kills += spam_kills
            if classes_played:
                ts.classes_played_lists.extend(classes_played)
            ts.time_played_pcts.append(tpct)

    # 3. RE-DETERMINE WINNER based on all rounds
    # (Optional: implement full Stopwatch logic across all rounds in DB if needed)
    match_row.winner_team = winner_team # Use the latest payload's winner as fallback

    # Insert totals
    performances: list[PlayerPerformance] = []

    for guid, ts in total_stats_by_guid.items():
        player = player_db_by_guid[guid]
        
        avg_time = sum(ts.time_played_pcts) / len(ts.time_played_pcts) if ts.time_played_pcts else 0.0
        eff, kdr = _eff_kdr(ts.kills, ts.deaths, ts.self_kills)
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
            unified_eff=_calculate_unified_eff(ts.kills, ts.revives, ts.team_medpacks + ts.medkits, ts.xp, ts.deaths, ts.self_kills),
            damage_given=ts.damage_given,
            damage_received=ts.damage_received,
            team_damage_given=ts.team_damage_given,
            team_damage_received=ts.team_damage_received,
            headshots=ts.headshots,
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

        performances.append(
            PlayerPerformance(
                player_id=player.id,
                team=ts.team,
                xp=float(ts.xp),
                kills=ts.kills,
                revives=float(ts.revives),
                ammo_packs=ts.team_medpacks,
                deaths=ts.deaths,
                self_kills=ts.self_kills,
                mu=mu,
                sigma=sigma,
            )
        )

    rating_results = calculate_openskill_ratings(performances, winner_team)

    for res in rating_results:
        gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == res.player_id).one_or_none()
        if not gr:
            gr = PlayerGatherRating(player_id=res.player_id, current_rating=1500.0, mu=25.0, sigma=8.333)
            db.add(gr)
            db.flush()
        
        new_rating = compute_display_rating(res.new_mu, res.new_sigma)
        
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

    # Calculate MVP
    best_score = -1.0
    mvp_pid = None
    for res in rating_results:
        perf = next((p for p in performances if p.player_id == res.player_id), None)
        if perf:
            # MVP Score matches the new get_score logic roughly
            tactical_eff = ((perf.kills + perf.revives) / max(1, perf.kills + perf.revives + perf.deaths + perf.self_kills)) * 100.0
            score = (tactical_eff * 0.7) + (min(100.0, perf.xp / 3.0) * 0.3)
            
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

    # 3. Load all matches in chronological order
    matches = db.query(Match).order_by(Match.round_start_unix.asc()).all()

    for m in matches:
        # Get total performance rows (round_index=0) for this match
        stats_rows = db.query(PlayerMatchStats).filter(
            PlayerMatchStats.match_id == m.id,
            PlayerMatchStats.round_index == 0
        ).all()

        if not stats_rows:
            continue

        performances = []
        for row in stats_rows:
            gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == row.player_id).one_or_none()
            if not gr:
                gr = PlayerGatherRating(player_id=row.player_id, current_rating=1500.0, mu=25.0, sigma=8.333)
                db.add(gr)
                db.flush()
            
            # Weapon accuracy logic (extracted from ingest_match_payloads)
            core_weapon_slots = {2, 3, 4, 5, 6, 7, 22, 23, 24, 25, 26}
            total_hits = 0
            total_shots = 0
            if row.weapon_breakdown_json:
                try:
                    wb = json.loads(row.weapon_breakdown_json)
                    # Support both list (unpacked) and dict (aggregated) formats
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
            weapon_acc = (total_hits / total_shots * 100.0) if total_shots > 0 else 0.0

            performances.append(PlayerPerformance(
                player_id=row.player_id,
                team=row.team,
                xp=float(row.xp),
                kills=row.kills,
                revives=row.revives,
                ammo_packs=row.team_medpacks,
                deaths=row.deaths,
                self_kills=row.self_kills,
                mu=gr.mu,
                sigma=gr.sigma
            ))

        rating_results = calculate_openskill_ratings(performances, m.winner_team)

        for res in rating_results:
            gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == res.player_id).one()
            
            new_rating = compute_display_rating(res.new_mu, res.new_sigma)
            delta = new_rating - gr.current_rating
            
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
        
        db.flush()
    
    db.commit()
