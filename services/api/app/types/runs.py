"""Types for the primary entity: the Extraction Run.

A run is persisted entirely as a B2 JSON manifest (`runs/<id>/run.json`) — there
is no database. These Pydantic models are the boundary contract for every
`/runs` endpoint and the shape written into B2.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# MMPoseInferencer aliases the create form exposes as a finite Select.
ModelName = Literal["human", "wholebody", "hand", "human3d"]
DeviceChoice = Literal["auto", "cpu", "cuda", "mps"]
RunStatus = Literal["pending", "running", "done", "error"]


class FrameKeypoints(BaseModel):
    """One source frame and the artifacts extraction derived from it."""

    frame: str
    source_key: str
    keypoints_key: str | None = None
    overlay_key: str | None = None
    num_instances: int = 0
    num_keypoints: int = 0
    mean_score: float = 0.0


class RunSummary(BaseModel):
    """Aggregate metrics for a finished run — the write-amplification story."""

    frame_count: int = 0
    total_instances: int = 0
    total_keypoints: int = 0
    source_bytes: int = 0
    derived_bytes: int = 0
    # derived_bytes / source_bytes — every frame fans out into JSON + an overlay,
    # so this is > 1 on any real run and is the dashboard's headline number.
    amplification_ratio: float = 0.0


class RunRecord(BaseModel):
    """The full persisted run manifest."""

    id: str
    label: str
    session: str
    model: ModelName
    device: DeviceChoice
    kpt_thr: float
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    notes: str = ""
    tags: list[str] = Field(default_factory=list)
    manifest_key: str
    error: str | None = None
    frames: list[FrameKeypoints] = Field(default_factory=list)
    summary: RunSummary = Field(default_factory=RunSummary)


class CreateRunRequest(BaseModel):
    label: str
    session: str
    model: ModelName = "human"
    kpt_thr: float = Field(default=0.3, ge=0, le=1)
    device: DeviceChoice = "auto"


class UpdateRunRequest(BaseModel):
    """Re-config is a new run, so the source session is intentionally fixed."""

    label: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class SessionInfo(BaseModel):
    """Populates the create-form session Select."""

    session: str
    frame_count: int


class EngineStatus(BaseModel):
    available: bool
    device: str
    torch_installed: bool
    detail: str


class RunActivityPoint(BaseModel):
    date: str
    runs: int


class PoseStats(BaseModel):
    """Dashboard metrics — the write-amplification headline plus run counts."""

    total_runs: int = 0
    runs_done: int = 0
    runs_running: int = 0
    runs_error: int = 0
    sessions: int = 0
    frames_available: int = 0
    frames_processed: int = 0
    total_instances: int = 0
    total_keypoints: int = 0
    source_bytes: int = 0
    derived_bytes: int = 0
    source_bytes_human: str = "0.0 B"
    derived_bytes_human: str = "0.0 B"
    amplification_ratio: float = 0.0
    activity: list[RunActivityPoint] = Field(default_factory=list)


class LibraryStage(BaseModel):
    stage: str  # "sessions" | "runs"
    object_count: int
    total_bytes: int
    total_bytes_human: str


class LibrarySummary(BaseModel):
    """Scoped Library explorer: objects under the sample prefix, by stage."""

    prefix: str
    stages: list[LibraryStage] = Field(default_factory=list)
    total_objects: int = 0
    total_bytes: int = 0
    total_bytes_human: str = "0.0 B"
