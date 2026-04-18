from app.database import SessionLocal
from app.models import Player, PlayerAlias, PlayerMatchStats
from sqlalchemy import func

guids = [
    "9320EBBCB68C77056EBA5B540569ADDC",
    "38B3BB21CBE5845A71637EEFDDD3245A",
    "7AD1870CEB0408C07BF6F1293A7B087F"
]

db = SessionLocal()
try:
    for guid in guids:
        p = db.query(Player).filter(Player.guid == guid).first()
        if not p:
            print(f"GUID {guid}: NOT FOUND")
            continue
            
        print(f"\n--- GUID: {guid} ---")
        print(f"Display Name: {p.display_name}")
        print(f"Raw Name Last: {p.raw_name_last}")
        
        # Check aliases
        aliases = db.query(PlayerAlias.alias, func.count(PlayerAlias.id)).filter(PlayerAlias.player_id == p.id).group_by(PlayerAlias.alias).all()
        print(f"Aliases: {aliases}")
        
        # Check match count
        match_count = db.query(PlayerMatchStats).filter(PlayerMatchStats.player_id == p.id).count()
        print(f"Matches: {match_count}")
        
        # Check IPs (if available in logs or similar, but for now just see if aliases share patterns)
finally:
    db.close()
