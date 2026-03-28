import os
import glob
import json
# import httpx (unused)
from collections import defaultdict

from sqlalchemy import create_engine
from app.models import Base
from app.config import settings
from sqlalchemy.orm import sessionmaker
from app.services.ingest import ingest_match_payloads
import traceback

def reset_db():
    db_path = "etl_stats.db"
    if os.path.exists(db_path):
        print("Trashing old DB...")
        os.remove(db_path)
    
    print("Initializing new DB...")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    engine.dispose()

def ingest_files():
    db_path = "etl_stats.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Search in both refs/ and refs/gamestats/
    file_patterns = [
        "../refs/gamestats-*.json",
        "../refs/gamestats/*.json"
    ]
    
    all_files = []
    for pattern in file_patterns:
        all_files.extend(glob.glob(pattern))
    
    # Ensure uniqueness
    all_files = list(set(all_files))
    
    # Sort all files chronologically by filename timestamp to correctly identify round sequences
    def get_file_timestamp(f):
        # f looks like ...gamestats-1774298608-...
        base = os.path.basename(f)
        if base.startswith("gamestats-"):
            parts = base.split("-")
            if len(parts) > 1:
                return int(parts[1])
        return 0
        
    all_files.sort(key=get_file_timestamp)
    
    match_groups = [] # List of lists of payloads
    current_group = []
    last_map = None
    last_ts = 0

    for f in all_files:
        with open(f, "r") as fp:
            try:
                data = json.load(fp)
                rinfo = data.get("round_info", {})
                mid = rinfo.get("matchID") or data.get("matchID")
                this_ts = get_file_timestamp(f)
                mapname = rinfo.get("mapname") or "unknown"
                round_num = int(rinfo.get("round") or 1)
                
                # Should we start a new group?
                # New group if round 1, OR if map changed, OR if time gap > 1 hour
                is_new_match = (round_num == 1) or (mapname != last_map) or (this_ts - last_ts > 3600)
                
                p_item = {
                    "file": f,
                    "match_id": str(mid),
                    "start_time": int(this_ts),
                    "mapname": mapname,
                    "data": data
                }
                
                if is_new_match or not current_group:
                    if current_group:
                        match_groups.append(current_group)
                    current_group = [p_item]
                else:
                    current_group.append(p_item)
                
                last_map = mapname
                last_ts = this_ts
                
            except Exception as e:
                print(f"Error reading {f}: {e}")
                
    if current_group:
        match_groups.append(current_group)

    for i, group in enumerate(match_groups):
        mid = group[0]["match_id"] # Use the first round's matchID as the match-level ID
        mapname = group[0]["mapname"]
        print(f"Ingesting Match #{i+1} [Map: {mapname}] ({len(group)} rounds)...")
        
        try:
            # Pass all rounds in the group to the ingestion service
            ingest_match_payloads(db, [p["data"] for p in group])
            print(f"  -> OK")
        except Exception as e:
            print(f"  -> Exception: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    reset_db()
    ingest_files()
    print("Done!")
