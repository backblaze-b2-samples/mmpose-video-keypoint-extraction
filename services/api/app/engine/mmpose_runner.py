"""Real MMPose inference — lazy-imported so the base app never loads it.

`run_inference` runs the actual `MMPoseInferencer` on a single frame and returns
normalized keypoints. It NEVER fabricates a result: if the engine isn't
installed it raises `EngineUnavailableError`, and the caller
(`service.runs.execute_run`) records an `error` run rather than a fake-green one.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from threading import Lock

from app.engine.device import resolve_device
from app.engine.engine_status import SETUP_HINT
from app.engine.keypoints import normalize_predictions

logger = logging.getLogger(__name__)


class EngineUnavailableError(RuntimeError):
    """Raised when pose inference is requested but the engine isn't installed."""


# Model alias → how to construct MMPoseInferencer. 2D top-down models take the
# alias as the positional `pose2d` arg (and bundle an RTMDet person detector);
# the 3D lifter takes `pose3d`.
_MODEL_ALIASES = ("human", "wholebody", "hand", "human3d")

# One inferencer per (model, device): construction downloads checkpoints from
# the OpenMMLab zoo (multi-minute cold) and loads weights, so it must not repeat
# per frame. Guarded because runs execute in Starlette's threadpool.
_inferencer_cache: dict[tuple[str, str], object] = {}
_cache_lock = Lock()


def _build_inferencer(model: str, device: str):
    # Lazy, heavy import — only reached when the engine actually runs.
    from mmpose.apis import MMPoseInferencer

    if model == "human3d":
        return MMPoseInferencer(pose3d="human3d", device=device)
    return MMPoseInferencer(model, device=device)


def _get_inferencer(model: str, device: str):
    key = (model, device)
    with _cache_lock:
        cached = _inferencer_cache.get(key)
        if cached is not None:
            return cached
    # Build outside the lock: construction is slow (weights download) and we do
    # not want to serialize unrelated first-run requests behind one another.
    inferencer = _build_inferencer(model, device)
    with _cache_lock:
        _inferencer_cache.setdefault(key, inferencer)
        return _inferencer_cache[key]


def _frame_instances(result: dict) -> list[dict]:
    """Pull one frame's instance list out of a MMPoseInferencer result."""
    preds = result.get("predictions") or []
    if not preds:
        return []
    frame = preds[0]
    # Some pipelines nest one extra level ([[{...}]]); flatten it.
    if frame and isinstance(frame[0], list):
        frame = frame[0]
    return list(frame)


def run_inference(
    frame_bytes: bytes,
    *,
    model: str = "human",
    device: str = "auto",
    kpt_thr: float = 0.3,
) -> dict:
    """Run MMPose on one frame and return normalized keypoints.

    Raises `EngineUnavailableError` (with an install hint) when the engine's
    modules can't be imported. Any other inference failure propagates as a plain
    exception for the caller to record on the run.
    """
    if model not in _MODEL_ALIASES:
        raise ValueError(f"Unknown model {model!r}; expected one of {_MODEL_ALIASES}")

    resolved = resolve_device(device)

    try:
        inferencer = _get_inferencer(model, resolved)
    except ImportError as exc:
        raise EngineUnavailableError(SETUP_HINT) from exc

    fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(frame_bytes)
        # We render overlays ourselves (engine.keypoints.draw_overlay), so no
        # visualization is requested here — keeps inference lean.
        result_gen = inferencer(tmp_path, return_vis=False)
        result = next(result_gen)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    normalized = normalize_predictions(_frame_instances(result), kpt_thr=kpt_thr)
    normalized["model"] = model
    normalized["device"] = resolved
    return normalized
