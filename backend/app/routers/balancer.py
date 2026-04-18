from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Player, PlayerGatherRating
from sqlalchemy import or_
from app.services.player_stats import get_player_ratings_and_roles
from app.config import settings

router = APIRouter(prefix="/api/balancer", tags=["balancer"])

class PlayerIdentity(BaseModel):
    guid: str
    name: str
    slot: Optional[int] = None
    team: Optional[str] = None # Added for delta-based movement

class BalanceRequest(BaseModel):
    players: List[PlayerIdentity]
    variations: bool = False

class TeamPlayer(BaseModel):
    guid: str
    name: str
    rating: float
    slot: Optional[int] = None
    role: str = "Unknown"
    origin_team: Optional[str] = None # Preserve current team for delta logic

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
    
    # 1. Fetch ratings and roles from DB using the GUIDs
    guids = [p.guid for p in req.players]
    ratings_map, roles_map = get_player_ratings_and_roles(db, guids)
    
    # Process each player from the request, prioritizing the provided name
    team_players = []
    for p in req.players:
        guid_upper = p.guid.upper()
        # Check rating: Try GUID first, default 1500.0
        rating = ratings_map.get(guid_upper, 1500.0)
        role = roles_map.get(guid_upper, "Unknown")
        
        team_players.append(TeamPlayer(
            guid=p.guid,
            name=p.name, # ALWAYS use the name provided in the request
            rating=rating,
            slot=p.slot,
            role=role,
            origin_team=p.team
        ))
    
    if not team_players:
        raise HTTPException(status_code=400, detail="No players to balance")
    
    # 2. Simple balancing algorithm
    import math
    import random
    
    max_size = math.ceil(len(team_players) / 2)
    
    def get_role_priority(role: str) -> int:
        role_lower = role.lower() if role else ""
        if 'rifle' in role_lower or 'eng' in role_lower:
            return 0
        if 'field' in role_lower or 'fop' in role_lower:
            return 1
        return 2
    
    def get_effective_rating(rating: float) -> float:
        thresh = settings.balancer_dampening_threshold
        factor = settings.balancer_dampening_factor
        if rating <= thresh:
            return rating
        return thresh + (rating - thresh) * factor

    def get_split(noise=0):
        # Sort by Role Priority (0 first), then Rating + Noise (Descending)
        sorted_p = sorted(
            team_players, 
            key=lambda x: (get_role_priority(x.role), -(x.rating + random.uniform(-noise, noise)))
        )
        a, b = [], []
        for p in sorted_p:
            if len(a) >= max_size:
                b.append(p)
                continue
            if len(b) >= max_size:
                a.append(p)
                continue
            
            # Use Dampened (Effective) SR sums to guide the greedy placement
            if sum(get_effective_rating(x.rating) for x in a) <= sum(get_effective_rating(x.rating) for x in b):
                a.append(p)
            else:
                b.append(p)
        return a, b

    if req.variations:
        # Generate 20 randomized drafts to ensure variety, then pick the most balanced one
        best_diff = float('inf')
        alpha, beta = [], []
        for _ in range(25):
            cand_a, cand_b = get_split(noise=settings.balancer_noise)
            
            a_avg = sum(p.rating for p in cand_a) / len(cand_a) if cand_a else 0
            b_avg = sum(p.rating for p in cand_b) / len(cand_b) if cand_b else 0
            diff = abs(a_avg - b_avg)
            
            if diff < best_diff:
                best_diff = diff
                alpha, beta = cand_a, cand_b
                
        # 50% chance to swap Axis and Allies for even more variety
        if random.random() > 0.5:
            alpha, beta = beta, alpha
            
    else:
        # Deterministic draft
        alpha, beta = get_split(noise=0)
            
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
