import sqlite3
import os

def run_migration():
    db_path = "/home/kostya/dev/personal/etl-stats-server/backend/etl_stats.db"
    
    # In docker or different paths, we might need to adjust, but based on local env:
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, trying relative path...")
        db_path = "etl_stats.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def add_column(table, column, type_def):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_def}")
            print(f"Added column {column} to {table}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {column} already exists in {table}")
            else:
                print(f"Error adding column {column} to {table}: {e}")

    print("Checking schema updates...")
    
    # Match table updats
    add_column("matches", "raw_payload", "TEXT")
    
    # player_match_stats updates
    add_column("player_match_stats", "unified_eff", "FLOAT DEFAULT 0.0")
    add_column("player_match_stats", "medkits", "INTEGER DEFAULT 0")

    conn.commit()
    conn.close()
    print("Database migration complete.")

if __name__ == "__main__":
    run_migration()
