from typing import List, Optional, Any
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Player, PlayerGatherRating
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import re
import asyncio
from app.services.rcon import send_rcon_command

router = APIRouter(prefix="/api/server", tags=["server"])

class ServerPlayer(BaseModel):
    slot: int
    name: str
    team: str
    guid: str
    rating: float

class PlayerListResponse(BaseModel):
    players: List[ServerPlayer]
    count: int

@router.get("/players", response_model=PlayerListResponse)
async def get_players(db: Session = Depends(get_db)):
    # 1. Trigger the custom Lua API to refresh the cache
    try:
        await send_rcon_command("api_live_players", timeout=2.0)
    except Exception as e:
        print(f"Trigger failed: {e}")
        pass
        
    # 2. Read chunks (we use 2 chunks to handle up to ~20 players safely)
    try:
        raw1 = await send_rcon_command("etl_live_api_1", timeout=2.0)
        raw2 = await send_rcon_command("etl_live_api_2", timeout=2.0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with RCON: {str(e)}")

    def extract_cvar(raw, name):
        if not raw: return ""
        match = re.search(f'"{name}" is: "(.*)"', raw)
        return match.group(1) if match else ""

    chunk1 = extract_cvar(raw1, "etl_live_api_1")
    chunk2 = extract_cvar(raw2, "etl_live_api_2")
    
    combined = chunk1
    if chunk2 and chunk2 != "":
        combined = combined + ";" + chunk2

    if not combined or combined == "":
        return PlayerListResponse(players=[], count=0)
        
    # 3. Parse compact format: slot|guid|team|name;
    live_players = []
    for entry in combined.split(";"):
        if not entry or "|" not in entry:
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

    if not live_players:
        return PlayerListResponse(players=[], count=0)
        
    # 4. Join with database ratings precisely using GUID
    found_guids = [p['guid'].upper() for p in live_players]
    ratings_map = {}
    
    if found_guids:
        db_ratings = (
            db.query(Player.guid, PlayerGatherRating.current_rating)
            .join(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
            .filter(Player.guid.in_(found_guids))
            .all()
        )
        ratings_map = {guid.upper(): rating for guid, rating in db_ratings}

    # 3. Format output
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
            rating=ratings_map.get(guid, 1500.0)
        ))

    return PlayerListResponse(
        players=final_players,
        count=len(final_players)
    )
