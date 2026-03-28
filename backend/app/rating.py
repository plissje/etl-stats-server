from dataclasses import dataclass
from typing import Any
from openskill.models import PlackettLuce

@dataclass
class PlayerPerformance:
    player_id: int
    team: int
    xp: float
    kills: int
    revives: int
    ammo_packs: int
    deaths: int
    self_kills: int
    mu: float
    sigma: float

@dataclass
class RatingResult:
    player_id: int
    new_mu: float
    new_sigma: float
    delta_rating: float  # Displayed delta, computed against (mu - 2*sigma)

def compute_display_rating(mu: float, sigma: float) -> float:
    # Default openskill mu=25, sigma=8.333
    # mu - 2*sigma = 25 - 16.666... = 8.333...
    # To start at exactly 1500, we subtract this default conservative rating (8.333...)
    # so that (25 - 16.666 - 8.333) * 100 + 1500 = 1500.
    conservative_rating = mu - (2.0 * sigma)
    default_conservative = 25.0 - (2.0 * 8.333333333333334)
    return max(100.0, 1500.0 + (conservative_rating - default_conservative) * 100.0)

def calculate_openskill_ratings(
    performances: list[PlayerPerformance],
    winner_team: int
) -> list[RatingResult]:
    """
    Computes ratings with an 80% weight on individual skill and 20% on team result.
    Incorporates accuracy (HSR), weapon efficiency (hits/shots), and efficiency.
    """
    if not performances:
        return []

    # Filter out spectators (team 3 or 0)
    playing = [p for p in performances if p.team in (1, 2)]
    
    if not playing:
        return [RatingResult(p.player_id, p.mu, p.sigma, 0.0) for p in performances]

    # Performance Score = (Efficiency * 5.0) + (HSR * 5.0) + (WeaponAcc * 5.0) + (XP/50)
    # Performance Score = (70% Efficiency) + (30% Support XP)
    # Support XP is normalized to 100 max (300 XP = 100 score)
    def get_score(p: PlayerPerformance) -> float:
        # Unified Contribution Points:
        # 1.0 per Kill/Revive
        # 0.25 per Ammo Pack
        # 0.10 per XP (Rewards Objectives, Repairs, etc.)
        total_points = p.kills + p.revives + (p.ammo_packs * 0.25) + (p.xp * 0.10)
        
        # Unified Efficiency: Points / (Points + Deaths + SelfKills)
        total_actions = total_points + p.deaths + p.self_kills
        unified_eff = (total_points / max(1, total_actions)) * 100.0
        
        # FINAL SR SCORE: Directly use the Unified Efficiency
        return max(1.0, unified_eff)

    match_scores = [get_score(p) for p in playing]
    match_avg_score = sum(match_scores) / len(match_scores) if match_scores else 0.0

    model = PlackettLuce()
    
    team1_perfs = [p for p in playing if p.team == 1]
    team2_perfs = [p for p in playing if p.team == 2]

    if not team1_perfs or not team2_perfs:
        return [RatingResult(p.player_id, p.mu, p.sigma, 0.0) for p in performances]

    team1_ratings = [model.rating(mu=p.mu, sigma=p.sigma) for p in team1_perfs]
    team2_ratings = [model.rating(mu=p.mu, sigma=p.sigma) for p in team2_perfs]

    ranks = [1, 2] if winner_team == 1 else ([2, 1] if winner_team == 2 else [1, 1])
    new_teams = model.rate([team1_ratings, team2_ratings], ranks=ranks)

    def compute_modified_team(
        old_perfs: list[PlayerPerformance],
        old_ratings: list[Any],
        new_ratings: list[Any],
        team_avg_score: float
    ) -> list[RatingResult]:
        results = []
        for p, old_r, new_r in zip(old_perfs, old_ratings, new_ratings):
            mu_delta_team = new_r.mu - old_r.mu
            
            # Individual Performance Boost (Relative to TEAM average)
            player_score = get_score(p)
            
            # Ratio: how much better/worse were they than the team average?
            ratio = player_score / max(1.0, team_avg_score)
            
            # Symmetric Boost logic: (Ratio - 1.0) * Sensitivity
            # A 20% better performance (+0.2 ratio) gives +0.2 * 1.5 = +0.3 mu boost
            # A 20% worse performance (-0.2 ratio) gives -0.2 * 1.5 = -0.3 mu penalty
            individual_performance_boost = (ratio - 1.0) * 1.5
            
            # 80/20 SPLIT BETWEEN TEAM RESULT AND INDIVIDUAL PERFORMANCE
            total_mu_change = (mu_delta_team * 0.2) + (individual_performance_boost * 0.8)
            
            # HARD BOUNDS: Prevent rating explosion (capped at +/- 2.0 mu per game)
            total_mu_change = max(-2.0, min(2.0, total_mu_change))

            sigma_delta = new_r.sigma - old_r.sigma
            final_mu = old_r.mu + total_mu_change
            final_sigma = old_r.sigma + sigma_delta

            results.append(
                RatingResult(
                    player_id=p.player_id,
                    new_mu=final_mu,
                    new_sigma=final_sigma,
                    delta_rating=0.0 # Will align absolutely in ingest.py
                )
            )
        return results

    # Calculate average scores per team
    t1_avg = sum(get_score(p) for p in team1_perfs) / len(team1_perfs) if team1_perfs else 0.0
    t2_avg = sum(get_score(p) for p in team2_perfs) / len(team2_perfs) if team2_perfs else 0.0

    res1 = compute_modified_team(team1_perfs, team1_ratings, new_teams[0], t1_avg)
    res2 = compute_modified_team(team2_perfs, team2_ratings, new_teams[1], t2_avg)

    # Combine back to original list format to preserve any spectators as 0 changes
    results_map = {r.player_id: r for r in res1 + res2}
    
    final_results = []
    for p in performances:
        if p.player_id in results_map:
            final_results.append(results_map[p.player_id])
        else:
            final_results.append(
                RatingResult(
                    player_id=p.player_id,
                    new_mu=p.mu,
                    new_sigma=p.sigma,
                    delta_rating=0.0
                )
            )

    return final_results
