import sqlite3
import json

conn = sqlite3.connect('etl_stats.db')
cursor = conn.cursor()

# Get Match row for 110 (match_id='99f24b1512')
# Note: I need the actual database id if possible, but 110 is likely the match_id field
cursor.execute("SELECT id FROM matches WHERE match_id='99f24b1512'")
m_id = cursor.fetchone()
if not m_id:
    print("Match 99f24b1512 not found")
    exit()
m_id = m_id[0]

# Query eranmil's stats for round 0 (total)
# eranmil guid part: 512CAB0B
cursor.execute("""
    SELECT pms.kills, pms.deaths, pms.self_kills, pms.team_deaths_received, pms.eff, pms.unified_eff, pl.display_name, pms.team
    FROM player_match_stats pms
    JOIN players pl ON pms.player_id = pl.id
    WHERE pms.match_id = ? AND pms.round_index = 0 AND pl.guid LIKE '%512CAB0B%'
""", (m_id,))

row = cursor.fetchone()
if row:
    kills, deaths, sk, tk_rec, eff, u_eff, name, team = row
    print(f"Player: {name} (Team {team})")
    print(f"Kills: {kills}, Deaths (Scoreboard): {deaths}, SK: {sk}, TK Rec: {tk_rec}")
    print(f"Efficiency (Scoreboard): {eff}%")
    print(f"Unified Efficiency (SR): {u_eff}%")
else:
    print("eranmil not found in Match 110")

conn.close()
