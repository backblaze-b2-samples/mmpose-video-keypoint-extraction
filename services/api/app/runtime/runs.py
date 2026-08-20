"""Routes for sessions, the Extraction Run entity, dashboard stats, and Library.

Handlers hold no business logic: they translate service exceptions into HTTP
status codes and delegate everything else to `app.service.runs`. Sync `def` so
the blocking B2 I/O runs in Starlette's threadpool (see runtime/files.py).
"""

import logging

from fastapi import APIRouter, HTTPException

from app.service.pose_stats import get_library, get_pose_stats
from app.service.runs import (
    EngineUnavailableError,
    FramesNotFoundError,
    RunNotFoundError,
    create_run,
    delete_run,
    execute_run,
    get_run,
    get_session_frames,
    list_runs,
    list_sessions,
    update_run,
)
from app.types import (
    CreateRunRequest,
    LibrarySummary,
    PoseStats,
    RunRecord,
    SessionInfo,
    UpdateRunRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: like the Files/Upload routes, these are intentionally
# UNAUTHENTICATED and bucket-wide (single-tenant demo stance — see
# docs/SECURITY.md). A multi-tenant clone must add auth and scope run ids to the
# caller.


# ---- Sessions ------------------------------------------------------------

@router.get("/sessions", response_model=list[SessionInfo])
def list_sessions_endpoint():
    return list_sessions()


@router.get("/sessions/{session}/frames", response_model=list[str])
def session_frames_endpoint(session: str):
    try:
        return get_session_frames(session)
    except FramesNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


# ---- Run CRUD ------------------------------------------------------------

@router.get("/runs", response_model=list[RunRecord])
def list_runs_endpoint():
    return list_runs()


@router.post("/runs", response_model=RunRecord, status_code=201)
def create_run_endpoint(req: CreateRunRequest):
    try:
        return create_run(
            label=req.label,
            session=req.session,
            model=req.model,
            kpt_thr=req.kpt_thr,
            device=req.device,
        )
    except FramesNotFoundError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


@router.get("/runs/{run_id}", response_model=RunRecord)
def get_run_endpoint(run_id: str):
    try:
        return get_run(run_id)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.patch("/runs/{run_id}", response_model=RunRecord)
def update_run_endpoint(run_id: str, req: UpdateRunRequest):
    try:
        return update_run(
            run_id, label=req.label, notes=req.notes, tags=req.tags
        )
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.delete("/runs/{run_id}")
def delete_run_endpoint(run_id: str):
    try:
        delete_run(run_id)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    logger.info("Run deleted: id=%s", run_id)
    return {"deleted": True, "id": run_id}


@router.post("/runs/{run_id}/execute", response_model=RunRecord)
def execute_run_endpoint(run_id: str):
    try:
        return execute_run(run_id)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except FramesNotFoundError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    except EngineUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from None


# ---- Dashboard + Library -------------------------------------------------

@router.get("/stats/pose", response_model=PoseStats)
def pose_stats_endpoint():
    return get_pose_stats()


@router.get("/library", response_model=LibrarySummary)
def library_endpoint():
    return get_library()
