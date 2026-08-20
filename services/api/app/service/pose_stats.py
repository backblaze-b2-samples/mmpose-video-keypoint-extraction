"""Dashboard and Library aggregates.

Split out of `service.runs` to stay under the 300-line cap. Reads run manifests
and prefix listings through the repo; no boto3 here.
"""

from __future__ import annotations

from app.repo import runs as repo
from app.service.runs import list_runs
from app.types import (
    LibraryStage,
    LibrarySummary,
    PoseStats,
    RunActivityPoint,
)
from app.types.formatting import humanize_bytes


def get_pose_stats() -> PoseStats:
    """The write-amplification headline plus run counts for the dashboard."""
    records = list_runs()
    done = [r for r in records if r.status == "done"]
    activity: dict[str, int] = {}
    for r in records:
        day = r.created_at.date().isoformat()
        activity[day] = activity.get(day, 0) + 1

    source_bytes = sum(r.summary.source_bytes for r in done)
    derived_bytes = sum(r.summary.derived_bytes for r in done)
    sessions = repo.list_sessions()
    return PoseStats(
        total_runs=len(records),
        runs_done=len(done),
        runs_running=sum(1 for r in records if r.status == "running"),
        runs_error=sum(1 for r in records if r.status == "error"),
        sessions=len(sessions),
        frames_available=sum(s["frame_count"] for s in sessions),
        frames_processed=sum(r.summary.frame_count for r in done),
        total_instances=sum(r.summary.total_instances for r in done),
        total_keypoints=sum(r.summary.total_keypoints for r in done),
        source_bytes=source_bytes,
        derived_bytes=derived_bytes,
        source_bytes_human=humanize_bytes(source_bytes),
        derived_bytes_human=humanize_bytes(derived_bytes),
        amplification_ratio=round(derived_bytes / source_bytes, 4) if source_bytes else 0.0,
        activity=[
            RunActivityPoint(date=d, runs=n) for d, n in sorted(activity.items())
        ],
    )


def get_library() -> LibrarySummary:
    """Objects under the sample prefix, grouped by pipeline stage."""
    stages = []
    total_objects = total_bytes = 0
    for stage, stage_prefix in (
        ("sessions", repo.sessions_prefix()),
        ("runs", repo.runs_prefix()),
    ):
        objects = repo.list_prefix(stage_prefix)
        count = len(objects)
        size = sum(o["Size"] for o in objects)
        total_objects += count
        total_bytes += size
        stages.append(LibraryStage(
            stage=stage,
            object_count=count,
            total_bytes=size,
            total_bytes_human=humanize_bytes(size),
        ))
    return LibrarySummary(
        prefix=repo.sessions_prefix().rsplit("sessions/", 1)[0],
        stages=stages,
        total_objects=total_objects,
        total_bytes=total_bytes,
        total_bytes_human=humanize_bytes(total_bytes),
    )
