from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import Player, PlayerGatherRating
from sqlalchemy import or_

router = APIRouter(prefix="/api/balancer", tags=["balancer"])

class BalanceRequest(BaseModel):
    player_identifiers: List[str]  # Can be GUIDs or exact names

class TeamPlayer(BaseModel):
    guid: str
    name: str
    rating: float

class BalanceResponse(BaseModel):
    alpha: List[TeamPlayer]
    beta: List[TeamPlayer]
    alpha_avg_sr: float
    beta_avg_sr: float
    diff: float

@router.post("/balance", response_model=BalanceResponse)
def balance_teams(req: BalanceRequest, db: Session = Depends(get_db)):
    if not req.player_identifiers:
        raise HTTPException(status_code=400, detail="No players provided")
    
    # 1. Fetch players and their ratings
    # We support both GUIDs and names for flexibility (especially for manual paste)
    found_players = (
        db.query(Player, PlayerGatherRating.current_rating)
        .outerjoin(PlayerGatherRating, Player.id == PlayerGatherRating.player_id)
        .filter(or_(
            Player.guid.in_(req.player_identifiers),
            Player.display_name.in_(req.player_identifiers)
        ))
        .all()
    )
    
    # Map found players for easy lookup
    found_map = {}
    for p, rating in found_players:
        found_map[p.guid] = (p.display_name, rating or 1500.0)
        found_map[p.display_name] = (p.display_name, rating or 1500.0)

    # Combine with original request to include everyone
    team_players = []
    seen_guids = set()
    
    for identifier in req.player_identifiers:
        if identifier in found_map:
            name, rating = found_map[identifier]
            # Avoid duplicates if both GUID and Name were provided for same player
            # (Though in practice we just use what's provided)
            team_players.append(TeamPlayer(
                guid=identifier,
                name=name,
                rating=rating
            ))
        else:
            # Not found in DB, use default name and SR
            team_players.append(TeamPlayer(
                guid=identifier,
                name=identifier,
                rating=1500.0
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
