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
from app.services.player_stats import get_player_ratings_and_roles

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
    from app.services.aliases import resolve_guid
    from app.services.player_stats import get_player_ratings_and_roles
    
    player_list = []
    guids_to_fetch = []
    
    # Temporary list to hold parsed data before resolution
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

    for raw in live_players:
        p_guid = str(raw.get("guid", "")).strip().upper()
        if not p_guid or p_guid == "UNKNOWN":
            continue
            
        # Resolve to Master GUID immediately
        master_guid = resolve_guid(p_guid)
            
        p_info = {
            "slot": int(raw.get("slot", 0)),
            "name": str(raw.get("name", "Unknown")),
            "team": int(raw.get("team", 0)),
            "guid": master_guid # Use Master GUID in the balancer
        }
        player_list.append(p_info)
        guids_to_fetch.append(master_guid)

    print(f"DEBUG: Total live players pre-rating: {len(live_players)}")

    if not live_players:
        return PlayerListResponse(players=[], count=0)
        
    # 4. Join with database ratings and roles precisely using GUID
    found_guids = [p['guid'].upper() for p in live_players]
    ratings_map, roles_map = get_player_ratings_and_roles(db, found_guids)

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
