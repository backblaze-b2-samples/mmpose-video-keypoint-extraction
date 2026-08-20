"""Engine-readiness route. Cheap probe — never runs inference here."""

from fastapi import APIRouter

from app.service.runs import get_engine_status
from app.types import EngineStatus

router = APIRouter()


# Sync `def`: engine_available() may import the (heavy) engine modules, so keep
# it in Starlette's threadpool rather than on the event loop.
@router.get("/engine/status", response_model=EngineStatus)
def engine_status_endpoint(device: str = "auto") -> EngineStatus:
    return get_engine_status(device)
