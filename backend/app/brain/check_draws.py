import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Match, MatchPayload

# Update this path to your actual production DB path if it differs
DB_URL = "sqlite:///stats.db" 
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print(f"{'ID':>4} | {'Map':<20} | {'Winner':>6} | {'R1 Dur':>7} | {'R2 Dur':>7} | {'R1 Win':>6} | {'R2 Win':>6}")
print("-" * 80)

matches = db.query(Match).order_by(Match.id.desc()).limit(30).all()
for m in matches:
    payload_rows = db.query(MatchPayload).filter(MatchPayload.match_id == m.id).order_by(MatchPayload.round_number).all()
    
    r1_dur = 0
    r2_dur = 0
    r1_win = 0
    r2_win = 0
    
    if len(payload_rows) >= 1:
        p1 = json.loads(payload_rows[0].payload).get("round_info", {})
        r1_dur = int(p1.get("round_end_unix") or 0) - int(p1.get("round_start_unix") or 0)
        r1_win = int(p1.get("winnerteam") or 0)
        
    if len(payload_rows) >= 2:
        p2 = json.loads(payload_rows[1].payload).get("round_info", {})
        r2_dur = int(p2.get("round_end_unix") or 0) - int(p2.get("round_start_unix") or 0)
        r2_win = int(p2.get("winnerteam") or 0)
        
    print(f"{m.id:>4} | {m.mapname[:20]:<20} | {m.winner_team:>6} | {r1_dur:>7} | {r2_dur:>7} | {r1_win:>6} | {r2_win:>6}")

db.close()
