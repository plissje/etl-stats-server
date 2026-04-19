import math

def get_score(kills, deaths, damage, xp, revives, self_kills):
    points = kills + (revives * 0.33) + (damage / 100.0) + (xp * 0.1)
    actions = points + deaths + (self_kills * 0.25)
    return (points / max(1, actions)) * 100.0

def calculate_delta(player_score, lobby_avg, winner, team_delta_mu=-0.2):
    ratio = player_score / lobby_avg
    indiv_boost = (ratio - 1.0) * 1.5
    
    total_mu = (team_delta_mu * 0.3) + (indiv_boost * 0.7)
    
    if winner:
        total_mu = max(0.005, total_mu)
        
    return total_mu * 100.0 # roughly SR change

# Match 253 Data (Approximations)
# Team 1 (Winners)
t1 = [
    {"name": "ERAN", "k": 26, "d": 12, "dmg": 2500, "xp": 100, "rev": 2}, # High
    {"name": "DrGuy", "k": 10, "d": 21, "dmg": 1000, "xp": 0, "rev": 0}, # Low
]
# Team 2 (Losers)
t2 = [
    {"name": "Athlon", "k": 24, "d": 9, "dmg": 2600, "xp": 150, "rev": 5}, # Carry
    {"name": "nWc", "k": 17, "d": 15, "dmg": 1500, "xp": 50, "rev": 1}, # "Positive but lose"
]

all_players = t1 + t2
scores = [get_score(p["k"], p["d"], p["dmg"], p["xp"], p["rev"], 0) for p in all_players]
lobby_avg = sum(scores) / len(scores)

print(f"Lobby Average Score: {lobby_avg:.2f}")

print("\nCurrent Logic (Lobby Average):")
for p in all_players:
    is_win = p in t1
    s = get_score(p["k"], p["d"], p["dmg"], p["xp"], p["rev"], 0)
    td = 0.2 if is_win else -0.2
    delta = calculate_delta(s, lobby_avg, is_win, td)
    print(f"  {p['name']:8}: Score {s:.1f} | Delta SR {delta:+.1f}")

baseline = 50.0
print(f"\nProposed Logic (Fixed Baseline {baseline}):")
for p in all_players:
    is_win = p in t1
    s = get_score(p["k"], p["d"], p["dmg"], p["xp"], p["rev"], 0)
    td = 0.2 if is_win else -0.2
    delta = calculate_delta(s, baseline, is_win, td)
    print(f"  {p['name']:8}: Score {s:.1f} | Delta SR {delta:+.1f}")

# Test Hybrid
hybrid_ref = (lobby_avg + baseline) / 2.0
print(f"\nProposed Logic (Hybrid Reference {hybrid_ref:.2f}):")
for p in all_players:
    is_win = p in t1
    s = get_score(p["k"], p["d"], p["dmg"], p["xp"], p["rev"], 0)
    td = 0.2 if is_win else -0.2
    delta = calculate_delta(s, hybrid_ref, is_win, td)
    print(f"  {p['name']:8}: Score {s:.1f} | Delta SR {delta:+.1f}")
