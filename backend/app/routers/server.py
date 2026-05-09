from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Player, PlayerGatherRating, PlayerMatchStats
from sqlalchemy import desc
import os
import re
import logging
import asyncio
import json

# Allowed base commands for /change-map.
# Override via RCON_ALLOWED_MAP_COMMANDS env var (comma-separated, e.g. "ref map,map_restart,map")
_DEFAULT_ALLOWED_MAP_COMMANDS = {"ref", "map_restart", "map"}
_env_cmds = os.getenv("RCON_ALLOWED_MAP_COMMANDS", "")
ALLOWED_MAP_COMMANDS: set[str] = (
    {c.strip() for c in _env_cmds.split(",") if c.strip()}
    if _env_cmds
    else _DEFAULT_ALLOWED_MAP_COMMANDS
)

logger = logging.getLogger(__name__)
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
    tag: Optional[str] = None # Optional colored tag to prepend to name
    origin_team: Optional[str] = None # Current team before the move

class BatchMoveRequest(BaseModel):
    moves: List[PlayerMove]

class MoveResponse(BaseModel):
    success: bool
    commands_sent: int
    details: str

class MapChangeRequest(BaseModel):
    map_name: str
    command: Optional[str] = None

@router.get("/players", response_model=PlayerListResponse)
async def get_players(db: Session = Depends(get_db)):
    # 1. Trigger the custom Lua API to refresh the cache
    try:
        await send_rcon_command("api_live_players", timeout=2.0)
    except Exception as e:
        logger.debug("api_live_players trigger failed: %s", e)
        
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
            logger.debug("[Players] Chunk %d parsed %d players", i + 1, len(entries))
        else:
            logger.debug("[Players] Chunk %d was empty", i + 1)

    if not combined_entries:
        logger.debug("[Players] No players found in any chunk")
        return PlayerListResponse(players=[], count=0)
    
    # 3. Parse compact format: slot|guid|team|name
    logger.debug("[Players] Raw chunks: %s", combined_entries)
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

    logger.debug("[Players] Total live players pre-rating: %d", len(player_list))

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
    
    # 1. APPLY TAGS FIRST (Always run tags, even if no moves are needed)
    for move in req.moves:
        if move.tag and move.name:
            # Sanitize name to prevent RCON command injection via quotes or semicolons
            safe_name = move.name.replace('"', "'").replace(";", "").strip()
            full_name = f"{move.tag}{safe_name}"
            if len(full_name) > 35:
                full_name = full_name[:35]
            rename_cmd = f'api_set_tag {move.slot} "{move.tag}" "{full_name}"'
            try:
                await send_rcon_command(rename_cmd, timeout=0.8)
                logger.info("[RCON] Smart Tag: Slot %d -> %s", move.slot, full_name)
                await asyncio.sleep(0.05)
                commands_sent += 1
            except Exception as e:
                logger.error("[RCON ERROR] Rename failed for slot %d: %s", move.slot, str(e))

    if not delta_moves:
        # Still need to announce who is on which team even if nobody moved
        axis_names = [m.name for m in req.moves if m.team == "Axis" and m.name]
        allies_names = [m.name for m in req.moves if m.team == "Allies" and m.name]
    else:
        to_axis = [m for m in delta_moves if m.team == "Axis"]
        to_allies = [m for m in delta_moves if m.team == "Allies"]
        to_spec = [m for m in delta_moves if m.team == "Spectator"]
        
        # Interleave moves to maintain headcount balance during transition
        interleaved_delta = []
        
        # CLEAR SPECTATORS FIRST
        interleaved_delta.extend(to_spec)
        
        for i in range(max(len(to_axis), len(to_allies))):
            if i < len(to_axis): interleaved_delta.append(to_axis[i])
            if i < len(to_allies): interleaved_delta.append(to_allies[i])

        # 2. APPLY TEAM MOVES (With safety delays)
        for move in interleaved_delta:
            if move.team == "Axis": sub_cmd = "putaxis"
            elif move.team == "Allies": sub_cmd = "putallies"
            elif move.team == "Spectator": sub_cmd = "remove"
            else: continue

            cmd = f"ref {sub_cmd} {move.slot}"
            try:
                response = await send_rcon_command(cmd, timeout=0.8)
                logger.info("[RCON] Move: %s -> %s", cmd, response.strip() if response else "OK")
                # 250ms delay between every move to let the engine breathe
                await asyncio.sleep(0.25)
                commands_sent += 1
            except Exception as e:
                logger.error("[RCON ERROR] %s failed: %s", cmd, str(e))

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
        
    if req.command:
        # Validate the base command against the allowlist before sending to RCON
        base_cmd = req.command.split()[0].lower()
        if base_cmd not in ALLOWED_MAP_COMMANDS:
            raise HTTPException(
                status_code=400,
                detail=f"Command '{base_cmd}' is not in the allowed list: {sorted(ALLOWED_MAP_COMMANDS)}"
            )
        cmd = req.command
    else:
        # Default to standard map change
        cmd = f"ref map {req.map_name}"
    try:
        response = await send_rcon_command(cmd, timeout=2.0)
        return {"success": True, "details": f"Map change command issued: {cmd}", "rcon_response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to issue map change: {str(e)}")

@router.post("/clear-tags")
async def clear_tags():
    """Reset the tag enforcement on the Lua script."""
    try:
        await send_rcon_command("api_clear_tags", timeout=1.0)
        return {"success": True, "message": "Tags cleared on server"}
    except Exception as e:
        logger.error("[RCON ERROR] Failed to clear tags: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

