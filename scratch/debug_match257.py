from dataclasses import dataclass
from typing import Any
from openskill.models import PlackettLuce

@dataclass
class PlayerPerformance:
    player_id: int
    team: int
    eff: float
    mu: float
    sigma: float

@dataclass
class RatingResult:
    player_id: int
    new_mu: float
    new_sigma: float

def calculate_test(playing, winner_team):
    def get_score(p): return p.eff
    
    match_scores = [get_score(p) for p in playing]
    lobby_avg = sum(match_scores) / len(match_scores) if match_scores else 0.0
    
    model = PlackettLuce()
    team1_perfs = [p for p in playing if p.team == 1]
    team2_perfs = [p for p in playing if p.team == 2]
    
    team1_ratings = [model.rating(mu=p.mu, sigma=p.sigma) for p in team1_perfs]
    team2_ratings = [model.rating(mu=p.mu, sigma=p.sigma) for p in team2_perfs]
    
    ranks = [1, 2] if winner_team == 1 else ([2, 1] if winner_team == 2 else [1, 1])
    print(f"DEBUG: Winner Team {winner_team} -> Ranks {ranks}")
    new_teams = model.rate([team1_ratings, team2_ratings], ranks=ranks)
    
    def compute_mod(old_perfs, old_ratings, new_ratings, is_winner):
        res = []
        for p, old_r, new_r in zip(old_perfs, old_ratings, new_ratings):
            mu_delta_team = new_r.mu - old_r.mu
            ratio = p.eff / lobby_avg
            indiv_boost = (ratio - 1.0) * 1.5
            total_mu_change = (mu_delta_team * 0.3) + (indiv_boost * 0.7)
            
            if is_winner:
                total_mu_change = max(0.005, total_mu_change)
            
            final_mu = old_r.mu + total_mu_change
            res.append((p.player_id, final_mu, new_r.sigma, total_mu_change))
        return res

    res1 = compute_mod(team1_perfs, team1_ratings, new_teams[0], winner_team == 1)
    res2 = compute_mod(team2_perfs, team2_ratings, new_teams[1], winner_team == 2)
    return res1, res2

# Match 257 Data
# Winners (Axis, Team 1)
axis = [
    PlayerPerformance(1, 1, 64.9, 25.0, 8.33), # RoNN
    PlayerPerformance(2, 1, 53.7, 25.0, 8.33), 
    PlayerPerformance(3, 1, 43.9, 25.0, 8.33),
    PlayerPerformance(4, 1, 40.9, 25.0, 8.33),
    PlayerPerformance(5, 1, 45.1, 25.0, 8.33)
]
# Losers (Allies, Team 2)
allies = [
    PlayerPerformance(6, 2, 50.0, 25.0, 8.33),
    PlayerPerformance(7, 2, 53.3, 25.0, 8.33),
    PlayerPerformance(8, 2, 49.0, 25.0, 8.33),
    PlayerPerformance(9, 2, 44.6, 25.0, 8.33),
    PlayerPerformance(10, 2, 47.3, 25.0, 8.33)
]

r1, r2 = calculate_test(axis + allies, 1)

print("\nRESULTS FOR WINNERS (Axis):")
for pid, mu, sig, delta in r1:
    print(f"  PID {pid}: Delta Mu {delta:+.4f}")

print("\nRESULTS FOR LOSERS (Allies):")
for pid, mu, sig, delta in r2:
    print(f"  PID {pid}: Delta Mu {delta:+.4f}")
