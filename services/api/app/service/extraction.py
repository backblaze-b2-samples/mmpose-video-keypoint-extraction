"""The per-frame extraction worker (runs on a background thread).

Split out of `service.runs` to keep each service module under the 300-line cap.
Orchestrates engine (compute) + repo (B2 I/O) only — no boto3, no torch at
module load.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.engine import draw_overlay, run_inference
from app.repo import runs as repo

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run_extraction(run_id: str) -> None:
    """Run inference for every frame in a run's session and persist to B2.

    Marks the run `done` with a computed summary, or `error` with a message.
    Never raises — the request that started it has already returned, so any
    failure must be recorded on the manifest rather than lost.
    """
    data = repo.load_manifest(run_id)
    if data is None:
        return
    session = data["session"]
    model = data["model"]
    device = data["device"]
    kpt_thr = float(data["kpt_thr"])
    frames = repo.session_frames(session)

    frame_records: list[dict] = []
    index_lines: list[str] = []
    source_bytes = derived_bytes = total_instances = total_keypoints = 0

    try:
        for f in frames:
            frame_name = f["frame"]
            source_key = f["key"]
            frame_bytes = repo.get_frame_bytes(source_key)
            source_bytes += len(frame_bytes)

            result = run_inference(
                frame_bytes, model=model, device=device, kpt_thr=kpt_thr
            )
            overlay_png = draw_overlay(frame_bytes, result, kpt_thr)

            kp_key = repo.keypoints_key(run_id, frame_name)
            ov_key = repo.overlay_key(run_id, frame_name)
            derived_bytes += repo.put_bytes(
                kp_key, json.dumps(result, indent=2).encode("utf-8"), "application/json"
            )
            derived_bytes += repo.put_bytes(ov_key, overlay_png, "image/png")

            n_inst = int(result["num_instances"])
            n_kpts = int(result["num_keypoints"])
            total_instances += n_inst
            total_keypoints += n_kpts

            frame_records.append({
                "frame": frame_name,
                "source_key": source_key,
                "keypoints_key": kp_key,
                "overlay_key": ov_key,
                "num_instances": n_inst,
                "num_keypoints": n_kpts,
                "mean_score": float(result["mean_score"]),
            })
            index_lines.append(json.dumps(frame_records[-1]))

        index_body = ("\n".join(index_lines) + "\n").encode("utf-8")
        derived_bytes += repo.put_bytes(
            repo.index_key(run_id), index_body, "application/x-ndjson"
        )

        data = repo.load_manifest(run_id) or data
        data["frames"] = frame_records
        data["summary"] = {
            "frame_count": len(frame_records),
            "total_instances": total_instances,
            "total_keypoints": total_keypoints,
            "source_bytes": source_bytes,
            "derived_bytes": derived_bytes,
            "amplification_ratio": (
                round(derived_bytes / source_bytes, 4) if source_bytes else 0.0
            ),
        }
        data["status"] = "done"
        data["error"] = None
        data["updated_at"] = _now_iso()
        repo.save_manifest(run_id, data)
        logger.info(
            "Run %s done: %d frames, %d instances, %d keypoints, %.2fx amplification",
            run_id, len(frame_records), total_instances, total_keypoints,
            data["summary"]["amplification_ratio"],
        )
    except Exception as exc:
        # Persist the failure on the run — this thread must not raise.
        logger.error("Run %s failed: %s", run_id, exc, exc_info=True)
        data = repo.load_manifest(run_id) or data
        data["status"] = "error"
        data["error"] = str(exc)
        data["updated_at"] = _now_iso()
        repo.save_manifest(run_id, data)
