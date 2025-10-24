from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..security import require_roles
from .schemas import AwardResult
from .service import AwardEngine, get_award_engine

router = APIRouter(prefix="/award", tags=["Award"])


@router.post(
    "/{rfq_id}/auto",
    response_model=AwardResult,
    dependencies=[Depends(require_roles("operations", "admin", action="award:execute", resource="award"))],
)
def auto_award(
    rfq_id: str,
    engine: AwardEngine = Depends(get_award_engine),
) -> AwardResult:
    try:
        return engine.auto_award(rfq_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
