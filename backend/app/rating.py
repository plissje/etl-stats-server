from dataclasses import dataclass
from typing import Any
from openskill.models import PlackettLuce

@dataclass
class PlayerPerformance:
    player_id: int
    team: int
    xp: float
    kills: int
    damage_given: int
    revives: int
    deaths: int
    self_kills: int
    mu: float
    sigma: float
    is_medic: bool = False

@dataclass
class RatingResult:
    player_id: int
    new_mu: float
    new_sigma: float
    delta_rating: float  # Displayed delta, computed against (mu - k*sigma)

def get_performance_score(p: PlayerPerformance) -> float:
    """
    Unified Contribution Score (0-100).
    
    Class-Aware Balancing:
    - Medics: Revives are weighted at 0.20. XP is weighted at 0.05 (to avoid double-dipping).
    - Others: XP is weighted at 0.30 (to reward objective play like dynamite plants).
    """
    xp_weight = 0.05 if p.is_medic else 0.30
    revive_weight = 0.20 # Standardized for all, primarily impacts medics
    
    # Kills are weighted at 1.2 to reward the primary carries. 
    # Revives, Damage, and XP provide the "Objective" foundation.
    total_points = (p.kills * 1.2) + (p.revives * revive_weight) + (p.damage_given / 100.0) + (p.xp * xp_weight)
    
    # Deaths are weighted at 1.25 in the denominator to balance "feeding" vs "grinding".
    # Self-kills are penalized at 0.50 to discourage reckless play.
    total_actions = total_points + (p.deaths * 1.25) + (p.self_kills * 0.50)
    return max(1.0, (total_points / max(1, total_actions)) * 100.0)

def compute_display_rating(mu: float, sigma: float, match_count: int = 0) -> float:
    # Hybrid Sigma multiplier: 2.0 for new players, 3.0 for settled veterans.
    k = 2.0 + (1.0 * min(max(0, match_count - 10), 10) / 10.0)
    
    # Starting baseline (mu=25, sigma=8.33) ensures a new player starts at exactly 1500.
    default_conservative = 25.0 - (k * 8.333333333333334)
    
    conservative_rating = mu - (k * sigma)
    return max(100.0, 1500.0 + (conservative_rating - default_conservative) * 100.0)

def calculate_openskill_ratings(
    performances: list[PlayerPerformance],
    winner_team: int
) -> list[RatingResult]:
    """
    TRUE 70/30 SR formula for random-team gather balancing.

    SR change = (70% x personal performance signal) + (30% x team outcome signal)

    The personal performance signal is based on how far above/below lobby average
    a player performed, completely independent of whether their team won or lost.
    
    We use Class-Aware scoring to prevent Medics from dominating the leaderboard:
    - Non-medics get 6x more weight on XP (objective play) than medics.
    - Medics have Revive weight reduced to 0.20 (down from 0.33).
    """
    if not performances:
        return []

    # Filter out spectators (team 3 or 0)
    playing = [p for p in performances if p.team in (1, 2)]
    
    if not playing:
        return [RatingResult(p.player_id, p.mu, p.sigma, 0.0) for p in performances]

    # --- LOBBY REFERENCE ---
    # Use the raw lobby average as the ONLY reference point.
    # At exactly lobby average, ratio=1.0 \u2192 perf_mu_delta=0 \u2192 no upward drift.
    all_scores = [get_performance_score(p) for p in playing]
    lobby_avg = sum(all_scores) / len(all_scores) if all_scores else 50.0

    # --- OPENSKILL (for sigma management and 30% team signal) ---
    model = PlackettLuce()
    team1_perfs = [p for p in playing if p.team == 1]
    team2_perfs = [p for p in playing if p.team == 2]

    if not team1_perfs or not team2_perfs:
        return [RatingResult(p.player_id, p.mu, p.sigma, 0.0) for p in performances]

    team1_ratings = [model.rating(mu=p.mu, sigma=p.sigma) for p in team1_perfs]
    team2_ratings = [model.rating(mu=p.mu, sigma=p.sigma) for p in team2_perfs]

    ranks = [1, 2] if winner_team == 1 else ([2, 1] if winner_team == 2 else [1, 1])
    new_teams = model.rate([team1_ratings, team2_ratings], ranks=ranks)

    # --- TUNING CONSTANTS ---
    # MAX_PERF_MU: max mu change per game from personal performance (75-80% weight).
    # Increased to 1.15 to allow "Heroic Losses" to result in neutral or positive SR.
    MAX_PERF_MU = 1.15

    # TEAM_WEIGHT: fraction of OpenSkill team signal applied (20-25% weight).
    # Set to 0.25 to ensure team outcome is a validator, but performance is the driver.
    TEAM_WEIGHT = 0.25

    def compute_player(p: PlayerPerformance, old_r: Any, new_r: Any) -> RatingResult:
        # --- 75%: PERSONAL PERFORMANCE SIGNAL ---
        player_score = get_performance_score(p)
        ratio = player_score / max(1.0, lobby_avg)
        ratio = max(0.1, min(3.0, ratio))  # clamp outliers

        # Performance delta is now constant magnitude, regardless of sigma.
        perf_delta_raw = max(-1.0, min(1.0, ratio - 1.0))
        perf_mu_delta = perf_delta_raw * MAX_PERF_MU

        # --- 25%: TEAM OUTCOME SIGNAL ---
        # We use sqrt of sigma_scale to reduce the 'cementing' of veteran ranks,
        # ensuring they still gain/lose meaningful amounts on team outcomes.
        sigma_scale_raw = min(1.0, old_r.sigma / 8.333)
        sigma_scale = sigma_scale_raw ** 0.5 
        team_mu_delta = (new_r.mu - old_r.mu) * TEAM_WEIGHT * sigma_scale

        # --- COMBINE ---
        total_mu_change = perf_mu_delta + team_mu_delta

        # HARD BOUNDS: Cap at \u00b11.0 mu per game (~100 SR in display)
        # HARD BOUNDS: Cap at ±1.0 mu per game (~100 SR in display)
        total_mu_change = max(-1.0, min(1.0, total_mu_change))

        # SIGMA: OpenSkill's update (uncertainty reduction).
        # Clamp at -0.5/game to smooth new-player jumps.
        sigma_delta = new_r.sigma - old_r.sigma
        sigma_delta = max(sigma_delta, -0.5)
        final_sigma = max(old_r.sigma + sigma_delta, 2.0)  # never below 2.0
        
        # --- COMPUTE DISPLAY SR ---
        # Leaderboard SR still uses the conservative mu - k*sigma approach.
        total_mu = old_r.mu + total_mu_change
        
        # Match Delta is now purely based on the Skill (Mu) change.
        # This prevents new players from 'winning' the SR race via sigma drops.
        # It ensures that the MVP of the match always shows the highest +SR.
        delta = total_mu_change * 100.0

        return RatingResult(p.player_id, total_mu, final_sigma, delta)

    results_map: dict[int, RatingResult] = {}
    for p, old_r, new_r in zip(team1_perfs, team1_ratings, new_teams[0]):
        results_map[p.player_id] = compute_player(p, old_r, new_r)
    for p, old_r, new_r in zip(team2_perfs, team2_ratings, new_teams[1]):
        results_map[p.player_id] = compute_player(p, old_r, new_r)

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
