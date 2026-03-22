from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import verify_stats_token
from app.schemas import SubmitStatsBody
from app.services.ingest import ingest_match_payload

router = APIRouter(prefix="/api", tags=["stats"])


@router.post("/submit-stats", dependencies=[Depends(verify_stats_token)])
def submit_stats(body: SubmitStatsBody, db: Session = Depends(get_db)) -> dict:
    try:
        payload = body.model_dump(exclude_none=True)
        match_row = ingest_match_payload(db, payload)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"ok": True, "match_db_id": match_row.id, "match_id": match_row.match_id}
