import json
from dataclasses import dataclass, field
from typing import Any

WP_MEDKIT = 19


def _norm_guid(g: str) -> str:
    return (g or "").strip().upper()


def _same_player(a: str, b: str) -> bool:
    a, b = _norm_guid(a), _norm_guid(b)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 8 and len(b) >= 8 and a[:8] == b[:8]:
        return True
    return False


@dataclass
class EventMetrics:
    kills: int = 0
    deaths: int = 0
    headshot_hits: int = 0
    shots_recorded: int = 0
    team_medpacks: int = 0
    nemesis: dict[str, int] = field(default_factory=dict)


def compute_event_metrics(
    player_guid: str,
    obituaries: list[dict[str, Any]] | None,
    damage_stats: list[dict[str, Any]] | None,
    team_by_guid: dict[str, int],
) -> EventMetrics:
    m = EventMetrics()
    pg = _norm_guid(player_guid)

    if obituaries:
        for ob in obituaries:
            atk = _norm_guid(str(ob.get("attacker") or ""))
            tgt = _norm_guid(str(ob.get("target") or ""))
            if _same_player(tgt, pg):
                m.deaths += 1
            if _same_player(atk, pg) and atk and tgt and not _same_player(atk, tgt):
                m.kills += 1
                m.nemesis[tgt] = m.nemesis.get(tgt, 0) + 1

    if damage_stats:
        for d in damage_stats:
            atk = _norm_guid(str(d.get("attacker") or ""))
            tgt = _norm_guid(str(d.get("target") or ""))
            mod = d.get("meansOfDeath")
            try:
                mod_i = int(mod) if mod is not None else -1
            except (TypeError, ValueError):
                mod_i = -1
            hr = str(d.get("hitRegion") or "")

            if _same_player(atk, pg):
                if hr == "HR_HEAD":
                    m.headshot_hits += 1
                m.shots_recorded += 1

            if _same_player(atk, pg) and mod_i == WP_MEDKIT and not _same_player(atk, tgt):
                t_team = next((v for k, v in team_by_guid.items() if _same_player(k, tgt)), 0)
                p_team = next((v for k, v in team_by_guid.items() if _same_player(k, pg)), 0)
                if t_team and p_team and t_team == p_team:
                    m.team_medpacks += 1

    return m


def nemesis_to_json(nemesis: dict[str, int], top_n: int = 5) -> str:
    if not nemesis:
        return "{}"
    sorted_pairs = sorted(nemesis.items(), key=lambda x: -x[1])[:top_n]
    return json.dumps(dict(sorted_pairs))


def hs_accuracy(headshots: int, shots: int) -> float | None:
    if shots <= 0:
        return None
    return round(100.0 * headshots / shots, 2)
