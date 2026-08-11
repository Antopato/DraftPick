from fastapi import APIRouter, HTTPException, Query

from ..services.analysis_service import AnalysisError, get_or_compute_analysis

router = APIRouter(prefix="/api")


@router.get("/analysis/{token}")
async def get_analysis(token: str, game: int | None = Query(default=None, ge=1)) -> dict:
    """Post-draft analysis for a completed game (defaults to the latest one).

    Read-only, so every token role — including spectators — may call it. Data
    problems degrade inside the payload (available/stale flags), never to 5xx.
    """
    try:
        return await get_or_compute_analysis(token, game)
    except AnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
