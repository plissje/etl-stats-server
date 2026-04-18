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
    team: str # Target team: "Axis" or "Allies"
    name: Optional[str] = None
    origin_team: Optional[str] = None # Current team before the move

class BatchMoveRequest(BaseModel):
    moves: List[PlayerMove]

class MoveResponse(BaseModel):
    success: bool
    commands_sent: int
    details: str

class MapChangeRequest(BaseModel):
    map_name: str

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

    print(f"DEBUG: Total live players pre-rating: {len(player_list)}")

    if not player_list:
        return PlayerListResponse(players=[], count=0)
        
    # 4. Join with database ratings and roles precisely using GUID
    found_guids = guids_to_fetch
    ratings_map, roles_map = get_player_ratings_and_roles(db, found_guids)

    # 5. Format output
    final_players = []
    for p in player_list:
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
    commands_sent = 0
    if not req.moves:
        return MoveResponse(success=True, commands_sent=0, details="No moves requested")
    
    tasks = []
    
    # Filter to only players who ACTUALLY need to move
    delta_moves = [m for m in req.moves if m.origin_team != m.team]
    
    if not delta_moves:
        # Still need to announce who is on which team even if nobody moved
        axis_names = [m.name for m in req.moves if m.team == "Axis" and m.name]
        allies_names = [m.name for m in req.moves if m.team == "Allies" and m.name]
    else:
        to_axis = [m for m in delta_moves if m.team == "Axis"]
        to_allies = [m for m in delta_moves if m.team == "Allies"]
        
        # Interleave moves to maintain headcount balance during transition
        interleaved_delta = []
        for i in range(max(len(to_axis), len(to_allies))):
            if i < len(to_axis): interleaved_delta.append(to_axis[i])
            if i < len(to_allies): interleaved_delta.append(to_allies[i])
            
        for move in interleaved_delta:
            sub_cmd = "putaxis" if move.team == "Axis" else "putallies"
            cmd = f"ref {sub_cmd} {move.slot}"
            try:
                # 150ms delay between every move to let the engine breathe and update headcount
                await send_rcon_command(cmd, timeout=0.8)
                await asyncio.sleep(0.15)
                commands_sent += 1
            except Exception:
                pass

        # Prep names for announcement (use all requested players, not just moved ones)
        axis_names = [m.name for m in req.moves if m.team == "Axis" and m.name]
        allies_names = [m.name for m in req.moves if m.team == "Allies" and m.name]

    # Announcements
    def chunked_names(names, n=4):
        return [names[i:i + n] for i in range(0, len(names), n)]
                
    if axis_names:
        for chunk in chunked_names(axis_names):
            try:
                msg = f'qsay ^1AXIS^7: {", ".join(chunk)}'
                await send_rcon_command(msg, timeout=0.8)
                await asyncio.sleep(0.15)
                commands_sent += 1
            except Exception:
                pass
            
    if allies_names:
        for chunk in chunked_names(allies_names):
            try:
                msg = f'qsay ^4ALLIES^7: {", ".join(chunk)}'
                await send_rcon_command(msg, timeout=0.8)
                await asyncio.sleep(0.15)
                commands_sent += 1
            except Exception:
                pass
    
    return MoveResponse(
        success=True, 
        commands_sent=commands_sent, 
        details=f"Issued {commands_sent} RCON commands ({len(delta_moves)} players moved) with 150ms spacing."
    )


@router.post("/change-map", response_model=dict)
async def change_map(req: MapChangeRequest):
    if not req.map_name:
        raise HTTPException(status_code=400, detail="Map name is required")
        
    cmd = f"ref map {req.map_name}"
    try:
        response = await send_rcon_command(cmd, timeout=2.0)
        return {"success": True, "details": f"Map change command issued: {cmd}", "rcon_response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to issue map change: {str(e)}")

