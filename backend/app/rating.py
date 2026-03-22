import math
from dataclasses import dataclass


@dataclass
class RatingWeights:
    kills: float = 12.0
    damage: float = 0.02
    revives: float = 8.0
    deaths: float = -10.0


def _mean(xs: list[float]) -> float:
    if not xs:
        return 0.0
    return sum(xs) / len(xs)


def _std(xs: list[float], mu: float) -> float:
    if len(xs) < 2:
        return 1.0
    v = sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(v) if v > 1e-9 else 1.0


def _z(x: float, mu: float, sigma: float) -> float:
    return (x - mu) / sigma


def calculate_power_rating_deltas(
    performances: list[dict[str, float]],
    weights: RatingWeights | None = None,
) -> list[float]:
    """
    performances: one dict per player with keys kills, damage_given, revives, deaths.
    Returns delta rating per player (same order).
    """
    w = weights or RatingWeights()
    if not performances:
        return []

    kills = [float(p["kills"]) for p in performances]
    dmg = [float(p["damage_given"]) for p in performances]
    rev = [float(p["revives"]) for p in performances]
    dth = [float(p["deaths"]) for p in performances]

    mk, sk = _mean(kills), _std(kills, _mean(kills))
    md, sd = _mean(dmg), _std(dmg, _mean(dmg))
    mr, sr = _mean(rev), _std(rev, _mean(rev))
    mt, st = _mean(dth), _std(dth, _mean(dth))

    deltas: list[float] = []
    for i in range(len(performances)):
        z_k = _z(kills[i], mk, sk)
        z_d = _z(dmg[i], md, sd)
        z_r = _z(rev[i], mr, sr)
        z_t = _z(dth[i], mt, st)
        delta = w.kills * z_k + w.damage * z_d + w.revives * z_r + w.deaths * z_t
        deltas.append(round(delta, 3))
    return deltas
