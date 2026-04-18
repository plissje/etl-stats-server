from app.database import SessionLocal
from app.models import Player

overrides = {
    "B0AA00C8A5DE3016D9A744B235282894": "Destiny",
    "EA3261495DB06A8508E3438B41E18603": "Licious",
    "DFABFBB65F4535F92A0C9DA9FBAE0623": "Montage",
    "2427C735A3080D37B034539CE1BECAB4": "Athlon",
    "AAEBDA7D44ACB680A00942D4603B9F38": "Outraaa",
    "62B43BD76EFD896A6ED20A315362CD3F": "Puni",
    "9A29D716D1F1B2D1B0F294A8EADD001F": "Fragon",
    "4238FBDFCD8F07E6FFBDD3C0E8B3D032": "sAimon",
    "4C26EAC8AA2FF738DFE1A2A0A20CB2A2": "hero4",
    "2D98BF3C83055B445FA235C809A3F7F0": "nWccc",
    "7192A28F166903AEDEF4BD926246C345": "Enforcer",
    "21EC7122B50B214D359925D02A9097FA": "N[e]o",
    "DA75A66CB510367D986E8DAEDA0D721B": "zer4tul"
}

db = SessionLocal()
try:
    for guid, name in overrides.items():
        player = db.query(Player).filter(Player.guid == guid).first()
        if player:
            print(f"Updating {guid}: '{player.display_name}' -> '{name}'")
            player.display_name = name
        else:
            print(f"Player NOT FOUND: {guid}")
    db.commit()
    print("Bulk update complete.")
finally:
    db.close()
