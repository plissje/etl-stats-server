import json
from dataclasses import dataclass, field
from typing import Any

from app.parsers.weapon_classes import get_support_type_from_mod

WP_SYRINGE = 11
WP_AMMO = 12
WP_MEDKIT = 19

def _norm_guid(g: str) -> str:
    return (g or "").strip().upper()


def _same_player(a: str, b: str) -> bool:
    a, b = _norm_guid(a), _norm_guid(b)
    if not a or not b:
        return False
    return a == b


@dataclass
class EventMetrics:
    kills: int = 0
    deaths: int = 0
    headshot_hits: int = 0
    shots_recorded: int = 0
    team_medpacks: int = 0
    team_ammopacks: int = 0
    revives: int = 0
    nemesis_kills: dict[str, int] = field(default_factory=dict)
    nemesis_deaths: dict[str, int] = field(default_factory=dict)


def compute_event_metrics(
    player_guid: str,
    obituaries: list[dict[str, Any]] | None,
    damage_stats: list[dict[str, Any]] | None,
    team_by_guid: dict[str, int],
    gamelog: list[dict[str, Any]] | None = None,
    aliases: dict[str, str] | None = None,
) -> EventMetrics:
    m = EventMetrics()
    pg = _norm_guid(player_guid)
    # Ensure pg is the MASTER guid if it was passed as an alias
    if aliases:
        pg = aliases.get(pg, pg)

    def _get_master(g: str) -> str:
        g_norm = _norm_guid(g)
        if aliases:
            return aliases.get(g_norm, g_norm)
        return g_norm

    # Process legacy formats ONLY if the new granular gamelog is missing
    # This prevents 2x stat inflation (obits + gamelog providing the same data)
    if not gamelog:
        # Process legacy obituaries
        if obituaries:
            for ob in obituaries:
                atk = _get_master(str(ob.get("attacker") or ""))
                tgt = _get_master(str(ob.get("target") or ""))
                if _same_player(tgt, pg):
                    m.deaths += 1
                    if atk and not _same_player(atk, tgt):
                        m.nemesis_deaths[atk] = m.nemesis_deaths.get(atk, 0) + 1
                if _same_player(atk, pg) and atk and tgt and not _same_player(atk, tgt):
                    m.kills += 1
                    m.nemesis_kills[tgt] = m.nemesis_kills.get(tgt, 0) + 1

        # Process legacy damage_stats (Heads/Shots)
        if damage_stats:
            for d in damage_stats:
                atk = _get_master(str(d.get("attacker") or ""))
                tgt = _get_master(str(d.get("target") or ""))
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

                if _same_player(atk, pg) and not _same_player(atk, tgt):
                    t_team = team_by_guid.get(tgt, 0)
                    p_team = team_by_guid.get(pg, 0)
                    if t_team and p_team and t_team == p_team:
                        if mod_i == WP_MEDKIT:
                            m.team_medpacks += 1
                        elif mod_i == WP_AMMO:
                            m.team_ammopacks += 1
                        elif mod_i == WP_SYRINGE:
                            m.revives += 1

    # Process new gamelog format
    if gamelog:
        for ev in gamelog:
            label = ev.get("label")
            group = ev.get("group")
            if group != "player":
                continue

            if label in ("kill", "teamkill"):
                atk = _get_master(str(ev.get("killer") or ""))
                tgt = _get_master(str(ev.get("victim") or ""))
                if _same_player(tgt, pg):
                    m.deaths += 1
                    if label == "kill" and atk and not _same_player(atk, tgt):
                        m.nemesis_deaths[atk] = m.nemesis_deaths.get(atk, 0) + 1
                if _same_player(atk, pg) and atk and tgt and not _same_player(atk, tgt):
                    if label == "kill":
                        m.kills += 1
                        m.nemesis_kills[tgt] = m.nemesis_kills.get(tgt, 0) + 1

            elif label == "suicide":
                p = _get_master(str(ev.get("player") or ""))
                if _same_player(p, pg):
                    m.deaths += 1

            elif label == "damage":
                atk = _get_master(str(ev.get("killer") or ""))
                tgt = _get_master(str(ev.get("victim") or ""))
                mod = ev.get("weapon")
                try:
                    mod_i = int(mod) if mod is not None else -1
                except (TypeError, ValueError):
                    mod_i = -1
                hr = str(ev.get("hit_region") or "")

                if _same_player(atk, pg):
                    if hr == "HR_HEAD":
                        m.headshot_hits += 1
                    m.shots_recorded += 1


                if _same_player(atk, pg):
                    t_team = team_by_guid.get(tgt, 0)
                    p_team = team_by_guid.get(pg, 0)
                    # For medkits and ammo, the engine emits damage events where attacker == pg (usually themselves or team members)
                    if t_team and p_team and t_team == p_team:
                        killer_class = ev.get("killer_class", "")
                        support_type = get_support_type_from_mod(mod_i, killer_class)
                        if support_type == "revives":
                            m.revives += 1
                        elif support_type == "medkit":
                            m.team_medpacks += 1
                        elif support_type == "ammo":
                            m.team_ammopacks += 1
            elif label == "revive":
                p_guid = _get_master(str(ev.get("player") or "")) # Medic
                if _same_player(p_guid, pg):
                    m.revives += 1

            elif label == "medkit":
                p_guid = _get_master(str(ev.get("player") or ""))
                if _same_player(p_guid, pg):
                    m.team_medpacks += 1

            elif label == "ammopack":
                p_guid = _get_master(str(ev.get("player") or ""))
                if _same_player(p_guid, pg):
                    m.team_ammopacks += 1

    return m


def nemesis_to_json(m: EventMetrics, top_n: int = 5) -> str:
    res = {"kills": {}, "deaths": {}}
    
    if m.nemesis_kills:
        sorted_kills = sorted(m.nemesis_kills.items(), key=lambda x: -x[1])[:top_n]
        res["kills"] = dict(sorted_kills)
        
    if m.nemesis_deaths:
        sorted_deaths = sorted(m.nemesis_deaths.items(), key=lambda x: -x[1])[:top_n]
        res["deaths"] = dict(sorted_deaths)
        
    return json.dumps(res)


def hs_accuracy(headshots: int, shots: int) -> float | None:
    if shots <= 0:
        return None
    return round(100.0 * headshots / shots, 2)
