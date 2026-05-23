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
    
    from app.routers.admin import get_ghost_boosts
    
    # --- TEMPORARY BALANCER BOOSTS ---
    # Used for strong players who don't have enough games to reflect their true SR.
    # This boost only affects team balancing, not the public leaderboard.
    try:
        GHOST_BOOSTS = get_ghost_boosts()
    except Exception:
        GHOST_BOOSTS = {}

    # Process each player from the request, prioritizing the provided name
    team_players = []
    for p in req.players:
        guid_upper = p.guid.upper()
        # Check rating: Try GUID first, default 1500.0
        rating = ratings_map.get(guid_upper, 1500.0)
        role = roles_map.get(guid_upper, "Unknown")
        
        if guid_upper in GHOST_BOOSTS:
            rating += GHOST_BOOSTS[guid_upper]
        
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
        # 1. Identify previous team setup to prevent identical partitions
        prev_axis = {p.guid.upper() for p in team_players if p.origin_team == 'Axis'}
        prev_allies = {p.guid.upper() for p in team_players if p.origin_team == 'Allies'}
        has_prev_setup = len(prev_axis) > 0 or len(prev_allies) > 0

        # 2. Generate 50 candidate splits with random SR noise
        candidates = []
        for _ in range(50):
            cand_a, cand_b = get_split(noise=settings.balancer_noise)
            
            a_avg = sum(p.rating for p in cand_a) / len(cand_a) if cand_a else 0
            b_avg = sum(p.rating for p in cand_b) / len(cand_b) if cand_b else 0
            diff = abs(a_avg - b_avg)
            
            # Check similarity
            cand_a_guids = {p.guid.upper() for p in cand_a}
            cand_b_guids = {p.guid.upper() for p in cand_b}
            is_identical = False
            if has_prev_setup:
                is_identical = (
                    (cand_a_guids == prev_axis and cand_b_guids == prev_allies) or
                    (cand_a_guids == prev_allies and cand_b_guids == prev_axis)
                )
                
            candidates.append({
                "alpha": cand_a,
                "beta": cand_b,
                "diff": diff,
                "is_identical": is_identical
            })
            
        # 3. Filter out identical combinations if other options exist
        non_identical = [c for c in candidates if not c["is_identical"]]
        pool = non_identical if non_identical else candidates
        
        # 4. Filter into pools based on our target max SR diff constraint
        acceptable = [c for c in pool if c["diff"] <= settings.balancer_max_diff]
        
        # 5. Select the final combination from the top 3 best variations in the appropriate pool
        if acceptable:
            acceptable.sort(key=lambda x: x["diff"])
            best_pool = acceptable[:min(3, len(acceptable))]
        else:
            pool.sort(key=lambda x: x["diff"])
            best_pool = pool[:min(3, len(pool))]
            
        selected = random.choice(best_pool)
        alpha, beta = selected["alpha"], selected["beta"]
        
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
