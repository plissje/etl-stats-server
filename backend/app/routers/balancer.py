from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import Player, PlayerGatherRating
from sqlalchemy import or_

router = APIRouter(prefix="/api/balancer", tags=["balancer"])

class PlayerIdentity(BaseModel):
    guid: str
    name: str
    slot: Optional[int] = None

class BalanceRequest(BaseModel):
    players: List[PlayerIdentity]

class TeamPlayer(BaseModel):
    guid: str
    name: str
    rating: float
    slot: Optional[int] = None

class BalanceResponse(BaseModel):
    alpha: List[TeamPlayer]
    beta: List[TeamPlayer]
    alpha_avg_sr: float
    beta_avg_sr: float
    diff: float

@router.post("/balance", response_model=BalanceResponse)
def balance_teams(req: BalanceRequest, db: Session = Depends(get_db)):
    if not req.players:
        raise HTTPException(status_code=400, detail="No players provided")
    
    # 1. Fetch ratings from DB using the GUIDs
    guids = [p.guid for p in req.players]
    names = [p.name for p in req.players] # For name-based resolution fallback
    
    found_players = (
        db.query(Player.guid, Player.display_name, PlayerGatherRating.current_rating)
        .outerjoin(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
        .filter(or_(
            Player.guid.in_(guids),
            Player.display_name.in_(names)
        ))
        .all()
    )
    
    # Map found ratings for lookup
    db_data = {} # guid/name -> rating
    for guid, display_name, rating in found_players:
        if guid: db_data[guid] = rating or 1500.0
        if display_name: db_data[display_name] = rating or 1500.0
    
    # Process each player from the request, prioritizing the provided name
    team_players = []
    for p in req.players:
        # Check rating: Try GUID first, then Name fallback
        rating = db_data.get(p.guid) or db_data.get(p.name) or 1500.0
        
        team_players.append(TeamPlayer(
            guid=p.guid,
            name=p.name, # ALWAYS use the name provided in the request
            rating=rating,
            slot=p.slot
        ))
    
    if not team_players:
        raise HTTPException(status_code=400, detail="No players to balance")
    
    # 2. Simple balancing algorithm (Greedy approach for now)
    # Sort by rating descending
    team_players.sort(key=lambda x: x.rating, reverse=True)
    
    alpha = []
    beta = []
    
    for p in team_players:
        # Sum current ratings
        alpha_sum = sum(x.rating for x in alpha)
        beta_sum = sum(x.rating for x in beta)
        
        # Add to the team with lower total rating
        # If lengths are very different, we might want to force balance count later
        # But for now, let's keep it simple as the user might provide odd numbers
        if alpha_sum <= beta_sum:
            alpha.append(p)
        else:
            beta.append(p)
            
    # 3. Calculate stats
    alpha_avg = sum(p.rating for p in alpha) / len(alpha) if alpha else 0
    beta_avg = sum(p.rating for p in beta) / len(beta) if beta else 0
    diff = abs(alpha_avg - beta_avg)
    
    return BalanceResponse(
        alpha=alpha,
        beta=beta,
        alpha_avg_sr=alpha_avg,
        beta_avg_sr=beta_avg,
        diff=diff
    )
