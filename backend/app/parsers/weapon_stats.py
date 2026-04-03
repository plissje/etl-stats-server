from dataclasses import dataclass
from typing import Any

from app.parsers.weapon_classes import WS_SLOT_NAMES, slot_to_support_item

TAIL_LEN = 10


def _to_int(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        return int(x)
    s = str(x).strip()
    if not s:
        return 0
    return int(float(s))


def _to_float(x: Any) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return 0.0
    return float(s)


@dataclass
class WeaponStatRow:
    slot: int
    name: str
    hits: int
    shots: int
    kills: int
    deaths: int
    headshots: int


@dataclass
class UnpackedWeaponStats:
    mask: int
    weapons: list[WeaponStatRow]
    damage_given: int
    damage_received: int
    team_damage_given: int
    team_damage_received: int
    gibs: int
    self_kills: int
    team_kills: int
    team_gibs: int
    time_played_pct: float
    xp: int
    kills: int = 0
    deaths: int = 0
    revives: int = 0
    medkits: int = 0
    ammopacks: int = 0


def unpack_weapon_stats(raw: list[Any], primary_class: str = "unknown") -> UnpackedWeaponStats | None:
    if not raw or len(raw) < 1 + TAIL_LEN:
        return None
    mask = _to_int(raw[0])
    body = raw[1:-TAIL_LEN]
    tail = raw[-TAIL_LEN:]
    idx = 0
    weapons: list[WeaponStatRow] = []
    
    _medkits = 0
    _ammopacks = 0
    _revives = 0
    
    for slot in range(len(WS_SLOT_NAMES)):
        if mask & (1 << slot):
            if idx + 5 > len(body):
                break
            support_nm = slot_to_support_item(slot, primary_class)
            final_name = WS_SLOT_NAMES[slot]
            hits = _to_int(body[idx])
            
            if support_nm:
                if final_name not in support_nm.capitalize():
                    final_name = f"{final_name} / {support_nm.capitalize()}"
                
                if support_nm == "medkit":
                    _medkits += hits
                elif support_nm == "ammo":
                    _ammopacks += hits
                elif support_nm == "revives":
                    _revives += hits
            
            weapons.append(
                WeaponStatRow(
                    slot=slot,
                    name=final_name,
                    hits=hits,
                    shots=_to_int(body[idx + 1]),
                    kills=_to_int(body[idx + 2]),
                    deaths=_to_int(body[idx + 3]),
                    headshots=_to_int(body[idx + 4]),
                )
            )
            idx += 5
    res = UnpackedWeaponStats(
        mask=mask,
        weapons=weapons,
        damage_given=_to_int(tail[0]),
        damage_received=_to_int(tail[1]),
        team_damage_given=_to_int(tail[2]),
        team_damage_received=_to_int(tail[3]),
        gibs=_to_int(tail[4]),
        self_kills=_to_int(tail[5]),
        team_kills=_to_int(tail[6]),
        team_gibs=_to_int(tail[7]),
        time_played_pct=_to_float(tail[8]),
        xp=_to_int(tail[9]),
        revives=_revives,
        medkits=_medkits,
        ammopacks=_ammopacks,
    )
    return res


def revives_from_unpacked(u: UnpackedWeaponStats | None) -> int:
    if not u:
        return 0
    return u.revives
