import os
import sys

# Add the project root to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from app.database import SessionLocal
    from app.models import Player
    from app.parsers.names import normalize_nick
except ImportError:
    from database import SessionLocal
    from models import Player
    from parsers.names import normalize_nick

def main():
    db = SessionLocal()
    try:
        players = db.query(Player).all()
        print(f"Checking {len(players)} players for name normalization...")
        
        updated_count = 0
        for p in players:
            original = p.display_name
            # Source of truth is the raw name with colors/tags
            source = p.raw_name_last or original
            normalized = normalize_nick(source)
            
            if normalized != original and normalized:
                print(f"Updating: '{original}' -> '{normalized}' (from '{source}')")
                p.display_name = normalized
                updated_count += 1
        
        if updated_count > 0:
            db.commit()
            print(f"Successfully updated {updated_count} player names.")
        else:
            print("No names required normalization.")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
