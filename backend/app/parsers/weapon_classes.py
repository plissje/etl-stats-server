from typing import Optional

# Standard ET: Legacy Weapons Matrix based on Oksii's Mod Engine
# Since weaponStats (0-27) is fixed, we list all names correctly:
WS_SLOT_NAMES: list[str] = [
    "Knife",             # 0
    "Knife (KBar)",      # 1
    "Luger",             # 2
    "Colt",              # 3
    "MP40",              # 4
    "Thompson",          # 5
    "Sten",              # 6
    "FG42",              # 7
    "Panzerfaust",       # 8
    "Bazooka",           # 9
    "Flamethrower",      # 10
    "Hand Grenade",      # 11
    "Mortar (Allied)",   # 12
    "Mortar (Axis)",     # 13
    "Dynamite",          # 14
    "Airstrike",         # 15
    "Artillery",         # 16
    "Satchel",           # 17
    "Rifle Grenade",     # 18
    "Landmine",          # 19
    "MG42",              # 20
    "Browning",          # 21
    "Carbine (Allied)",  # 22
    "Kar98 (Axis)",      # 23
    "Garand",            # 24
    "K43",               # 25
    "MP34",              # 26
    "Syringe (Revives)", # 27
]

# Engine MOD (Means of Death) Mapping for Gamelog parsing
MOD_MAPPING = {
    6: "Luger",
    7: "Colt",
    8: "MP40",
    9: "Thompson",
    10: "Sten",
    15: "Panzerfaust",
    16: "Grenade Launcher",
    17: "Flamethrower",
    18: "Pineapple Grenade",
    19: "Map Mortar",
    22: "Dynamite",
    23: "Airstrike",
    24: "Syringe",
    25: "Ammo",
    26: "Artillery",
    37: "GPG40 (Axis Rifle Grenade)",
    38: "M7 (Allied Rifle Grenade)",
    39: "Landmine",
    40: "Satchel",
    51: "K43",
    54: "Mortar",
}

class ClassTimelineTracker:
    def __init__(self, gamelog: list[dict]):
        # Store segments of: (start_time, end_time, class_name)
        # gamelog is ordered by unixtime/leveltime
        self.tracker = {} # dict of guid -> list of (leveltime, class_name)
        
        for ev in gamelog:
            lbl = ev.get("label")
            group = ev.get("group")
            if group != "player": continue
            
            p = ev.get("player")
            if not p: continue
            
            if lbl in ("spawn", "class_change"):
                cname = ev.get("class")
                ltime = ev.get("leveltime") or ev.get("unixtime") or 0
                if cname:
                    if p not in self.tracker:
                        self.tracker[p] = []
                    self.tracker[p].append((ltime, cname))

    def get_class_at(self, guid: str, leveltime: int) -> str:
        history = self.tracker.get(guid)
        if not history:
            return "unknown"
            
        current_class = "unknown"
        for t, cname in history:
            if leveltime >= t:
                current_class = cname
            else:
                break
        return current_class

def get_support_type_from_mod(mod: int, killer_class: str) -> Optional[str]:
    """
    Decodes a damage MOD constant into a Support Item type.
    """
    if killer_class == "medic":
        if mod == 24: return "revives"  # SYRINGE
    elif killer_class == "fieldop":
        if mod == 25: return "ammo" # AMMO
    return None

def slot_to_support_item(slot: int, player_class: str) -> Optional[str]:
    """
    Decodes an ambiguous WS slot constant into a Support Item type.
    """
    if player_class == "medic":
        if slot == 27: return "revives"
        if slot == 19: return "medkit"
    elif player_class == "fieldop":
        if slot == 22 or slot == 12: return "ammo"
    return None
