from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Player, PlayerGatherRating, PlayerMatchStats
from sqlalchemy import desc
import re
import asyncio
import json
from collections import Counter
from app.services.rcon import send_rcon_command

router = APIRouter(prefix="/api/server", tags=["server"])

class ServerPlayer(BaseModel):
    slot: int
    name: str
    team: str
    guid: str
    rating: float
    main_role: str = "Unknown"

class PlayerListResponse(BaseModel):
    players: List[ServerPlayer]
    count: int
    
class PlayerMove(BaseModel):
    slot: int
    team: str # "Axis" or "Allies"

class BatchMoveRequest(BaseModel):
    moves: List[PlayerMove]

class MoveResponse(BaseModel):
    success: bool
    commands_sent: int
    details: str

@router.get("/players", response_model=PlayerListResponse)
async def get_players(db: Session = Depends(get_db)):
    # 1. Trigger the custom Lua API to refresh the cache
    try:
        await send_rcon_command("api_live_players", timeout=2.0)
    except Exception as e:
        print(f"Trigger failed: {e}")
        pass
        
    # 2. Read 10 chunks in parallel for robustness and speed
    try:
        commands = [send_rcon_command(f"etl_live_api_{i}", timeout=2.0) for i in range(1, 11)]
        raw_responses = await asyncio.gather(*commands)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with RCON: {str(e)}")

    def extract_cvar(raw, name):
        if not raw: return ""
        # Match "name" is: "value" - uses non-greedy match to handle potential nested quotes safely
        match = re.search(f'"{name}" is: "(.*?)"', raw)
        return match.group(1) if match else ""

    combined_entries = []
    for i, raw in enumerate(raw_responses):
        chunk_str = extract_cvar(raw, f"etl_live_api_{i+1}")
        if chunk_str:
            entries = [e for e in chunk_str.split(";") if e]
            combined_entries.extend(entries)
            print(f"DEBUG: Chunk {i+1} parsed {len(entries)} players")
        else:
            print(f"DEBUG: Chunk {i+1} was empty")

    if not combined_entries:
        print("DEBUG: No players found in any chunk")
        return PlayerListResponse(players=[], count=0)
    
    # 3. Parse compact format: slot|guid|team|name
    print(f"DEBUG RAW CHunks: {combined_entries}") # Log raw data for verification
    live_players = []
    for entry in combined_entries:
        if "|" not in entry:
            continue
        parts = entry.split("|")
        if len(parts) < 4:
            continue
        try:
            live_players.append({
                "slot": int(parts[0]),
                "guid": parts[1].upper(),
                "team": int(parts[2]),
                "name": parts[3]
            })
        except:
            continue

    print(f"DEBUG: Total live players pre-rating: {len(live_players)}")

    if not live_players:
        return PlayerListResponse(players=[], count=0)
        
    # 4. Join with database ratings and roles precisely using GUID
    found_guids = [p['guid'].upper() for p in live_players]
    ratings_map = {}
    roles_map = {}
    
    if found_guids:
        # Fetch ratings
        db_ratings = (
            db.query(Player.guid, PlayerGatherRating.current_rating)
            .join(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
            .filter(Player.guid.in_(found_guids))
            .all()
        )
        ratings_map = {guid.upper(): rating for guid, rating in db_ratings}

        # role_map = {
        #     "Medic": "Medic",
        #     "Engineer": "Rifle/Eng" or "Engineer",
        #     "Field Ops": "Field Ops",
        # }
        
        # To keep it performant, we'll fetch stats for these players
        stats_rows = (
            db.query(Player.guid, PlayerMatchStats.classes_played_json, PlayerMatchStats.weapon_breakdown_json)
            .join(Player, Player.id == PlayerMatchStats.player_id)
            .filter(Player.guid.in_(found_guids))
            .order_by(desc(PlayerMatchStats.id))
            .limit(1000) # Bulk fetch recent stats
            .all()
        )

        # Aggregate roles and weapons in memory
        player_class_times = {} # guid -> Counter
        player_weapon_kills = {} # guid -> Counter
        
        # Identification sets for Rifles vs SMGs
        RIFLE_WEAPONS = {"WS_K43", "WS_GARAND", "WS_KAR98", "WS_M1_GARAND", "WS_K43_RIFLE", "WS_SVT40", "WS_GPG40", "WS_M7"}
        SMG_WEAPONS = {"WS_THOMPSON", "WS_MP40", "WS_STEN"}

        for guid, classes_json, weapons_json in stats_rows:
            guid = guid.upper()
            if guid not in player_class_times:
                player_class_times[guid] = Counter()
                player_weapon_kills[guid] = Counter()

            # 1. Classes - Calculate duration between timestamps
            if classes_json:
                try:
                    classes = json.loads(classes_json)
                    # Sort by timestamp to ensure we can calculate differences
                    classes.sort(key=lambda x: x.get('timestamp', 0))
                    
                    for i, c in enumerate(classes):
                        class_name = c.get('toClass', 'unknown').lower()
                        start_time = c.get('timestamp', 0)
                        
                        # Use the next timestamp to calculate duration, or a default 10min if it's the only/last one
                        if i + 1 < len(classes):
                            duration = max(0, classes[i+1].get('timestamp', 0) - start_time)
                        else:
                            # For the last class or single-class players, give it a significant base weight (600s)
                            # so they are correctly identified even with one entry.
                            duration = 600
                        
                        player_class_times[guid][class_name] += duration
                except: pass

            # 2. Weapons
            if weapons_json:
                try:
                    weapons = json.loads(weapons_json)
                    for w in weapons:
                        w_name = w.get('name', '')
                        kills = w.get('kills', 0)
                        if w_name in RIFLE_WEAPONS or w_name in SMG_WEAPONS:
                            player_weapon_kills[guid][w_name] += kills
                except: pass

        for guid, counts in player_class_times.items():
            if not counts: continue
            
            # Apply Tactical Weighting: Prioritize Engineer and Field Ops over Medic
            # This ensures that if a player plays both roughly equally, we show the more 
            # tactically significant role for balancing.
            weighted_counts = Counter(counts)
            weighted_counts['engineer'] = int(weighted_counts['engineer'] * 1.5)
            weighted_counts['fieldop'] = int(weighted_counts['fieldop'] * 1.3)
            
            # Find dominant class from weighted counts
            top_class = weighted_counts.most_common(1)[0][0]
            
            # Map ET classes to roles
            role = "Medic" # Default fallback
            if top_class == "medic":
                role = "Medic"
            elif top_class == "fieldop":
                role = "Field Ops"
            elif top_class == "engineer":
                # Check for Rifle vs SMG preference for Engineers
                w_kills = player_weapon_kills.get(guid, Counter())
                rifle_kills = sum(w_kills[w] for w in RIFLE_WEAPONS)
                smg_kills = sum(w_kills[w] for w in SMG_WEAPONS)
                
                if rifle_kills > smg_kills:
                    role = "Rifle/Eng"
                else:
                    role = "Engineer"
            
            roles_map[guid] = role

    # 5. Format output
    final_players = []
    for p in live_players:
        team_map = {1: "Axis", 2: "Allies", 3: "Spectator"}
        team_str = team_map.get(p['team'], "Active")
        guid = p['guid'].upper()
        
        final_players.append(ServerPlayer(
            slot=p['slot'],
            name=p['name'],
            team=team_str,
            guid=guid,
            rating=ratings_map.get(guid, 1500.0),
            main_role=roles_map.get(guid, "Unknown")
        ))

    return PlayerListResponse(
        players=final_players,
        count=len(final_players)
    )

@router.post("/move-players", response_model=MoveResponse)
async def move_players(req: BatchMoveRequest):
    if not req.moves:
        return MoveResponse(success=True, commands_sent=0, details="No moves requested")
    
    tasks = []
    for move in req.moves:
        # User feedback: putteam doesn't work, use ref putaxis/putallies
        sub_cmd = "putaxis" if move.team == "Axis" else "putallies"
        cmd = f"ref {sub_cmd} {move.slot}"
        tasks.append(send_rcon_command(cmd))
    
    try:
        # Execute all moves in parallel
        await asyncio.gather(*tasks)
        return MoveResponse(
            success=True, 
            commands_sent=len(req.moves), 
            details=f"Successfully issued {len(req.moves)} movement commands."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RCON move failed: {str(e)}")
