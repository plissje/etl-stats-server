import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Player, PlayerGatherRating, PlayerGatherRatingHistory, PlayerMatchStats

router = APIRouter(prefix="/api/players", tags=["players"])


def _aggregate_weapons(stats_rows: list[PlayerMatchStats]) -> list[dict[str, Any]]:
    acc: dict[str, dict[str, float | int | str | None]] = {}
    for pms in stats_rows:
        if not pms.weapon_breakdown_json:
            continue
        try:
            parts = json.loads(pms.weapon_breakdown_json)
        except json.JSONDecodeError:
            continue
        for w in parts:
            key = str(w.get("name") or w.get("slot"))
            if key not in acc:
                acc[key] = {
                    "name": key,
                    "hits": 0,
                    "shots": 0,
                    "kills": 0,
                    "headshots": 0,
                }
            acc[key]["hits"] += int(w.get("hits") or 0)
            acc[key]["shots"] += int(w.get("shots") or 0)
            acc[key]["kills"] += int(w.get("kills") or 0)
            acc[key]["headshots"] += int(w.get("headshots") or 0)
    out = []
    for v in acc.values():
        shots = int(v["shots"])
        hits = int(v["hits"])
        pct = round(100.0 * hits / shots, 2) if shots > 0 else None
        out.append({**v, "accuracy_pct": pct})
    out.sort(key=lambda x: (-(x["accuracy_pct"] or 0), -int(x["kills"])))
    return out[:12]


@router.get("/{guid}")
def player_profile(guid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    g = guid.strip().upper()
    pl = db.query(Player).filter(Player.guid == g).one_or_none()
    if not pl and len(g) >= 8:
        pl = db.query(Player).filter(Player.guid.startswith(g[:8])).first()
    if not pl:
        raise HTTPException(404, "player not found")

    gr = db.query(PlayerGatherRating).filter(PlayerGatherRating.player_id == pl.id).one_or_none()
    rating = gr.current_rating if gr else 1500.0

    hist = (
        db.query(PlayerGatherRatingHistory)
        .filter(PlayerGatherRatingHistory.player_id == pl.id)
        .order_by(PlayerGatherRatingHistory.recorded_at.asc())
        .all()
    )
    rating_history = [
        {
            "match_id": h.match_id,
            "rating": h.rating,
            "delta": h.delta,
            "recorded_at": h.recorded_at.isoformat(),
        }
        for h in hist
    ]

    pms_list = db.query(PlayerMatchStats).filter(PlayerMatchStats.player_id == pl.id).all()
    top_weapons = _aggregate_weapons(pms_list)

    return {
        "guid": pl.guid,
        "display_name": pl.display_name,
        "current_rating": rating,
        "rating_history": rating_history,
        "top_weapons": top_weapons,
    }
