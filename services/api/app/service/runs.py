"""Business logic for sessions and the Extraction Run primary entity.

Orchestrates the engine (pure compute) and the repo (B2 I/O). No boto3 here —
all storage goes through `app.repo.runs`; no torch/mmpose at module load — the
engine is imported cheaply and only actually runs inside the execute path.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from threading import Thread

from app.engine import engine_available, engine_status
from app.engine.mmpose_runner import EngineUnavailableError
from app.repo import runs as repo
from app.service.extraction import run_extraction
from app.types import EngineStatus, RunRecord, SessionInfo

logger = logging.getLogger(__name__)

__all__ = [
    "EngineUnavailableError",
    "FramesNotFoundError",
    "RunNotFoundError",
    "create_run",
    "delete_run",
    "execute_run",
    "get_engine_status",
    "get_run",
    "get_session_frames",
    "list_runs",
    "list_sessions",
    "update_run",
]


class RunNotFoundError(Exception):
    def __init__(self, run_id: str):
        self.run_id = run_id
        super().__init__(f"Run '{run_id}' not found")


class FramesNotFoundError(Exception):
    def __init__(self, session: str):
        self.session = session
        super().__init__(f"Session '{session}' has no ingested frames")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ---- Engine + sessions ---------------------------------------------------

def get_engine_status(device_preference: str = "auto") -> EngineStatus:
    return EngineStatus(**engine_status(device_preference))


def list_sessions() -> list[SessionInfo]:
    return [SessionInfo(**s) for s in repo.list_sessions()]


def get_session_frames(session: str) -> list[str]:
    frames = repo.session_frames(session)
    if not frames:
        raise FramesNotFoundError(session)
    return [f["frame"] for f in frames]


# ---- Run CRUD ------------------------------------------------------------

def list_runs() -> list[RunRecord]:
    records = []
    for run_id in repo.list_run_ids():
        data = repo.load_manifest(run_id)
        if data is not None:
            records.append(RunRecord(**data))
    records.sort(key=lambda r: r.created_at, reverse=True)
    return records


def get_run(run_id: str) -> RunRecord:
    data = repo.load_manifest(run_id)
    if data is None:
        raise RunNotFoundError(run_id)
    return RunRecord(**data)


def create_run(
    *, label: str, session: str, model: str, kpt_thr: float, device: str
) -> RunRecord:
    # Source session is fixed at create — a re-config is a new run — so validate
    # it has frames now rather than failing later at execute time.
    if not repo.session_frames(session):
        raise FramesNotFoundError(session)
    run_id = _new_id()
    now = _now_iso()
    record = {
        "id": run_id,
        "label": label,
        "session": session,
        "model": model,
        "device": device,
        "kpt_thr": kpt_thr,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "notes": "",
        "tags": [],
        "manifest_key": repo.manifest_key(run_id),
        "error": None,
        "frames": [],
        "summary": {},
    }
    repo.save_manifest(run_id, record)
    return RunRecord(**record)


def update_run(
    run_id: str,
    *,
    label: str | None = None,
    notes: str | None = None,
    tags: list[str] | None = None,
) -> RunRecord:
    data = repo.load_manifest(run_id)
    if data is None:
        raise RunNotFoundError(run_id)
    if label is not None:
        data["label"] = label
    if notes is not None:
        data["notes"] = notes
    if tags is not None:
        data["tags"] = tags
    data["updated_at"] = _now_iso()
    repo.save_manifest(run_id, data)
    return RunRecord(**data)


def delete_run(run_id: str) -> None:
    if repo.load_manifest(run_id) is None:
        raise RunNotFoundError(run_id)
    repo.delete_run(run_id)


# ---- Execute (the only heavy-engine path) --------------------------------

def execute_run(run_id: str) -> RunRecord:
    """Start pose extraction for a run.

    Gates on `engine_available()` and never fabricates a result: with the engine
    absent the run is recorded as `error` and `EngineUnavailableError` is raised
    (the route maps it to 503). Otherwise the run is marked `running` and the
    per-frame work happens on a background thread so the request returns
    immediately — the UI polls `GET /runs/{id}` for `done`/`error`.
    """
    data = repo.load_manifest(run_id)
    if data is None:
        raise RunNotFoundError(run_id)
    if data.get("status") == "running":
        return RunRecord(**data)

    if not engine_available():
        status = engine_status(data.get("device", "auto"))
        data["status"] = "error"
        data["error"] = status["detail"]
        data["updated_at"] = _now_iso()
        repo.save_manifest(run_id, data)
        raise EngineUnavailableError(status["detail"])

    frames = repo.session_frames(data["session"])
    if not frames:
        raise FramesNotFoundError(data["session"])

    data["status"] = "running"
    data["error"] = None
    data["updated_at"] = _now_iso()
    repo.save_manifest(run_id, data)

    Thread(
        target=run_extraction,
        args=(run_id,),
        name=f"mmpose-extract:{run_id}",
        daemon=True,
    ).start()
    return RunRecord(**data)
