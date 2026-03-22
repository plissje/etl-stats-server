from dataclasses import dataclass
from typing import Any

WS_SLOT_NAMES: list[str] = [
    "WS_KNIFE",
    "WS_KNIFE_KBAR",
    "WS_LUGER",
    "WS_COLT",
    "WS_MP40",
    "WS_THOMPSON",
    "WS_STEN",
    "WS_FG42",
    "WS_PANZERFAUST",
    "WS_BAZOOKA",
    "WS_FLAMETHROWER",
    "WS_GRENADE",
    "WS_MORTAR",
    "WS_MORTAR2",
    "WS_DYNAMITE",
    "WS_AIRSTRIKE",
    "WS_ARTILLERY",
    "WS_SATCHEL",
    "WS_GRENADELAUNCHER",
    "WS_LANDMINE",
    "WS_MG42",
    "WS_BROWNING",
    "WS_CARBINE",
    "WS_KAR98",
    "WS_GARAND",
    "WS_K43",
    "WS_MP34",
    "WS_SYRINGE",
]

WS_SYRINGE_SLOT = 27
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


def unpack_weapon_stats(raw: list[Any]) -> UnpackedWeaponStats | None:
    if not raw or len(raw) < 1 + TAIL_LEN:
        return None
    mask = _to_int(raw[0])
    body = raw[1:-TAIL_LEN]
    tail = raw[-TAIL_LEN:]
    idx = 0
    weapons: list[WeaponStatRow] = []
    for slot in range(len(WS_SLOT_NAMES)):
        if mask & (1 << slot):
            if idx + 5 > len(body):
                break
            weapons.append(
                WeaponStatRow(
                    slot=slot,
                    name=WS_SLOT_NAMES[slot],
                    hits=_to_int(body[idx]),
                    shots=_to_int(body[idx + 1]),
                    kills=_to_int(body[idx + 2]),
                    deaths=_to_int(body[idx + 3]),
                    headshots=_to_int(body[idx + 4]),
                )
            )
            idx += 5
    return UnpackedWeaponStats(
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
    )


def revives_from_unpacked(u: UnpackedWeaponStats | None) -> int:
    if not u:
        return 0
    for w in u.weapons:
        if w.slot == WS_SYRINGE_SLOT:
            return w.hits
    return 0
