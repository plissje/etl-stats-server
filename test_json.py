import sqlite3
import json

c = sqlite3.connect(":memory:")
c.execute("CREATE TABLE player_match_stats (id INTEGER, weapon_breakdown_json TEXT)")
c.execute("INSERT INTO player_match_stats VALUES (1, '[{\"slot\": 3, \"hits\": 5, \"shots\": 10}]')")
c.execute("INSERT INTO player_match_stats VALUES (1, '[{\"slot\": 3, \"hits\": 15, \"shots\": 30}]')")
c.execute("INSERT INTO player_match_stats VALUES (2, '[{\"slot\": 3, \"hits\": 9, \"shots\": 10}]')")

res = c.execute("""
    SELECT id, SUM(json_extract(weap.value, '$.hits')) * 100.0 / SUM(json_extract(weap.value, '$.shots')) as val
    FROM player_match_stats, json_each(weapon_breakdown_json) weap 
    WHERE json_extract(weap.value, '$.slot') IN (2, 3) 
    GROUP BY id
    ORDER BY val DESC
""").fetchall()

print(res)
