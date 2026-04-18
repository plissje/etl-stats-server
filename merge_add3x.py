from app.database import SessionLocal
from app.models import Player, PlayerAlias, PlayerMatchStats, PlayerGatherRating, PlayerGatherRatingHistory, Match

TARGET_ID = 1
SOURCE_IDS = [48, 51]

db = SessionLocal()
try:
    print(f"Starting consolidation into Target ID {TARGET_ID}...")

    # 1. Transfer PlayerMatchStats
    res = db.query(PlayerMatchStats).filter(PlayerMatchStats.player_id.in_(SOURCE_IDS)).update(
        {PlayerMatchStats.player_id: TARGET_ID}, synchronize_session=False
    )
    print(f"Moved {res} PlayerMatchStats records.")

    # 2. Transfer PlayerAliases
    res = db.query(PlayerAlias).filter(PlayerAlias.player_id.in_(SOURCE_IDS)).update(
        {PlayerAlias.player_id: TARGET_ID}, synchronize_session=False
    )
    print(f"Moved {res} PlayerAlias records.")

    # 3. Transfer PlayerGatherRatingHistory
    res = db.query(PlayerGatherRatingHistory).filter(PlayerGatherRatingHistory.player_id.in_(SOURCE_IDS)).update(
        {PlayerGatherRatingHistory.player_id: TARGET_ID}, synchronize_session=False
    )
    print(f"Moved {res} PlayerGatherRatingHistory records.")

    # 4. Update Match Awards (MVP Player ID)
    res = db.query(Match).filter(Match.mvp_player_id.in_(SOURCE_IDS)).update(
        {Match.mvp_player_id: TARGET_ID}, synchronize_session=False
    )
    print(f"Updated {res} Match MVP references.")

    # 5. Delete redundant ratings and players
    del_ratings = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id.in_(SOURCE_IDS)).delete(synchronize_session=False)
    print(f"Deleted {del_ratings} redundant rating records.")

    del_players = db.query(Player).filter(Player.id.in_(SOURCE_IDS)).delete(synchronize_session=False)
    print(f"Deleted {del_players} redundant player records.")

    db.commit()
    print("Consolidation committed successfully.")

    # Final Verification
    final_matches = db.query(PlayerMatchStats.match_id).filter(PlayerMatchStats.player_id == TARGET_ID).distinct().count()
    print(f"Final unique match count for Add3X (ID {TARGET_ID}): {final_matches}")

finally:
    db.close()
