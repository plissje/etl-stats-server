import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Match,
    Player,
    PlayerGatherRating,
    PlayerGatherRatingHistory,
    PlayerMatchStats,
)
from app.parsers.events import compute_event_metrics, hs_accuracy, nemesis_to_json
from app.parsers.names import strip_quake_colors
from app.parsers.weapon_stats import UnpackedWeaponStats, revives_from_unpacked, unpack_weapon_stats
from app.rating import calculate_power_rating_deltas


def _weapon_breakdown_json(u: UnpackedWeaponStats | None) -> str | None:
    if not u or not u.weapons:
        return None
    rows = []
    for w in u.weapons:
        acc = None
        if w.shots > 0:
            acc = round(100.0 * w.hits / w.shots, 2)
        rows.append(
            {
                "slot": w.slot,
                "name": w.name,
                "hits": w.hits,
                "shots": w.shots,
                "kills": w.kills,
                "deaths": w.deaths,
                "headshots": w.headshots,
                "accuracy": acc,
            }
        )
    return json.dumps(rows)


def _eff_kdr(kills: int, deaths: int) -> tuple[float, float]:
    eff = round(100.0 * kills / max(1, kills + deaths), 1)
    kdr = round(kills / max(1, deaths), 2)
    return eff, kdr


def ingest_match_payload(db: Session, body: dict[str, Any], store_raw: bool = True) -> Match:
    player_stats = body.get("player_stats") or {}
    round_info = body.get("round_info") or {}

    match_id = str(round_info.get("matchID") or body.get("matchID") or "")
    if not match_id:
        raise ValueError("missing matchID")

    mapname = str(round_info.get("mapname") or "")
    winner_team = int(round_info.get("winnerteam") or 0)
    rs = int(round_info.get("round_start_unix") or 0)
    re = int(round_info.get("round_end_unix") or 0)

    obituaries = round_info.get("obituaries")
    damage_stats = round_info.get("damageStats")

    existing = db.query(Match).filter(Match.match_id == match_id).one_or_none()
    if existing:
        hists = (
            db.query(PlayerGatherRatingHistory)
            .filter(PlayerGatherRatingHistory.match_id == existing.id)
            .all()
        )
        for h in hists:
            gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == h.player_id).one_or_none()
            if gr:
                gr.current_rating = max(100.0, gr.current_rating - h.delta)
        db.query(PlayerGatherRatingHistory).filter(PlayerGatherRatingHistory.match_id == existing.id).delete()
        db.query(PlayerMatchStats).filter(PlayerMatchStats.match_id == existing.id).delete()
        existing.mapname = mapname
        existing.winner_team = winner_team
        existing.round_start_unix = rs
        existing.round_end_unix = re
        if store_raw:
            existing.raw_payload = json.dumps(body)
        match_row = existing
        db.flush()
    else:
        raw_str = json.dumps(body) if store_raw else None
        match_row = Match(
            match_id=match_id,
            mapname=mapname,
            winner_team=winner_team,
            round_start_unix=rs,
            round_end_unix=re,
            raw_payload=raw_str,
        )
        db.add(match_row)
        db.flush()

    team_by_guid: dict[str, int] = {}
    for g, pdata in player_stats.items():
        try:
            team_by_guid[g.strip().upper()] = int(pdata.get("team") or 0)
        except (TypeError, ValueError):
            team_by_guid[g.strip().upper()] = 0

    perf_for_rating: list[dict[str, float]] = []
    player_order: list[Player] = []

    for guid_key, pdata in player_stats.items():
        guid = guid_key.strip().upper()
        name_raw = str(pdata.get("name") or "")
        display = strip_quake_colors(name_raw) or guid[:8]

        player = db.query(Player).filter(Player.guid == guid).one_or_none()
        if not player:
            player = Player(guid=guid, display_name=display, raw_name_last=name_raw)
            db.add(player)
            db.flush()
        else:
            player.display_name = display or player.display_name
            player.raw_name_last = name_raw or player.raw_name_last

        ws_raw = pdata.get("weaponStats") or []
        if not isinstance(ws_raw, list):
            ws_raw = []
        unpacked = unpack_weapon_stats(ws_raw)

        em = compute_event_metrics(guid, obituaries, damage_stats, team_by_guid)
        kills, deaths = em.kills, em.deaths
        eff, kdr = _eff_kdr(kills, deaths)

        revives = revives_from_unpacked(unpacked)
        hs_acc = hs_accuracy(em.headshot_hits, em.shots_recorded)

        dg = dr = tdg = tdr = gibs = sk = tk = tg = 0
        tpct = 0.0
        xp = 0
        if unpacked:
            dg = unpacked.damage_given
            dr = unpacked.damage_received
            tdg = unpacked.team_damage_given
            tdr = unpacked.team_damage_received
            gibs = unpacked.gibs
            sk = unpacked.self_kills
            tk = unpacked.team_kills
            tg = unpacked.team_gibs
            tpct = unpacked.time_played_pct
            xp = unpacked.xp

        pms = PlayerMatchStats(
            match_id=match_row.id,
            player_id=player.id,
            team=int(pdata.get("team") or 0),
            kills=kills,
            deaths=deaths,
            kdr=kdr,
            eff=eff,
            damage_given=dg,
            damage_received=dr,
            team_damage_given=tdg,
            team_damage_received=tdr,
            headshots=em.headshot_hits,
            gibs=gibs,
            self_kills=sk,
            team_kills=tk,
            team_gibs=tg,
            time_played_pct=tpct,
            xp=xp,
            revives=revives,
            team_medpacks=em.team_medpacks,
            hs_accuracy_event=hs_acc,
            nemesis_json=nemesis_to_json(em.nemesis),
            weapon_breakdown_json=_weapon_breakdown_json(unpacked),
            name_raw=name_raw,
        )
        db.add(pms)

        perf_for_rating.append(
            {
                "kills": float(kills),
                "damage_given": float(dg),
                "revives": float(revives),
                "deaths": float(deaths),
            }
        )
        player_order.append(player)

    deltas = calculate_power_rating_deltas(perf_for_rating)
    for player, delta in zip(player_order, deltas, strict=True):
        gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == player.id).one_or_none()
        if not gr:
            gr = PlayerGatherRating(player_id=player.id, current_rating=1500.0)
            db.add(gr)
            db.flush()
        new_rating = max(100.0, min(4000.0, gr.current_rating + delta))
        hist = PlayerGatherRatingHistory(
            player_id=player.id,
            match_id=match_row.id,
            rating=new_rating,
            delta=delta,
        )
        db.add(hist)
        gr.current_rating = new_rating

    db.commit()
    db.refresh(match_row)
    return match_row
