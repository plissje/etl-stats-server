import os
import sys

# Add the parent directory to sys.path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import Match, PlayerMatchStats, Player
from sqlalchemy.orm import Session

def backfill_mvps():
    db: Session = SessionLocal()
    try:
        matches = db.query(Match).filter(Match.mvp_player_id == None).all()
        print(f"Found {len(matches)} matches to backfill.")
        
        for m in matches:
            # Re-using the logic from matches.py and ingest.py
            player_rows = (
                db.query(PlayerMatchStats, Player)
                .join(Player, Player.id == PlayerMatchStats.player_id)
                .filter(PlayerMatchStats.match_id == m.id)
                .filter(PlayerMatchStats.round_index == 0)
                .all()
            )
            
            best_score = -1.0
            mvp_id = None
            
            for pms, p in player_rows:
                score = pms.eff + (pms.xp / 10.0)
                if m.winner_team > 0 and pms.team == m.winner_team:
                    score += 0.01
                    
                if score > best_score:
                    best_score = score
                    mvp_id = p.id
            
            if mvp_id:
                m.mvp_player_id = mvp_id
                print(f"Match {m.id} ({m.mapname}): MVP set to player {mvp_id}")
        
        db.commit()
        print("Backfill complete.")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_mvps()
