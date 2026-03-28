import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Player
from app.config import settings

def debug_player(guid):
    engine = create_engine("sqlite:///./etl_stats.db")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    g = guid.strip().upper()
    print(f"Searching for GUID: '{g}'")
    pl = db.query(Player).filter(Player.guid == g).one_or_none()
    if pl:
        print(f"Found player: {pl.display_name} (ID: {pl.id})")
    else:
        print("Player not found.")
        # Check all players to see if there's a mismatch
        all_pls = db.query(Player).limit(5).all()
        print("First 5 players in DB:")
        for p in all_pls:
            print(f"  - '{p.guid}' (len: {len(p.guid)})")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_player(sys.argv[1])
    else:
        debug_player("6C143D430742E81EC875A60BB63605BB")
