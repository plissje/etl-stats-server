import sqlite3
import os
import sys

def migrate(db_path):
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    print(f"Migrating {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Checking for missing columns...")
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(player_match_stats)")
    columns = [row[1] for row in cursor.fetchall()]

    if "unified_eff" not in columns:
        print("Adding unified_eff column...")
        cursor.execute("ALTER TABLE player_match_stats ADD COLUMN unified_eff FLOAT DEFAULT 0.0")
    
    if "medkits" not in columns:
        print("Adding medkits column...")
        cursor.execute("ALTER TABLE player_match_stats ADD COLUMN medkits INTEGER DEFAULT 0")

    conn.commit()

    print("Backfilling Unified Efficiency for historical data...")
    
    # Selecting all rows to update
    cursor.execute("SELECT id, kills, revives, team_medpacks, xp, deaths, self_kills FROM player_match_stats")
    rows = cursor.fetchall()
    
    updates = []
    for row in rows:
        row_id, kills, revives, meds_ammo, xp, deaths, sk = row
        
        # Best guess for historical data:
        # We'll treat the existing team_medpacks as "support packs" (Ammo or Meds)
        points = kills + revives + (meds_ammo * 0.25) + (xp * 0.10)
        total_actions = points + deaths + sk
        
        u_eff = 0.0
        if total_actions > 0:
            u_eff = round((points / total_actions) * 100.0, 1)
            
        updates.append((u_eff, row_id))

    # Perform batch update
    print(f"Updating {len(updates)} records...")
    cursor.executemany("UPDATE player_match_stats SET unified_eff = ? WHERE id = ?", updates)
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        paths = ["etl_stats.db"]
    for p in paths:
        migrate(p)
    print("All migrations done!")
