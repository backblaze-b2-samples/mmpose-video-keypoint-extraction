"""The local MMPose keypoint-extraction engine.

This package is deliberately import-cheap: nothing here imports torch / mmcv /
mmdet / mmpose at module load. The heavy stack is opt-in (see
`requirements-engine.txt` and `scripts/setup-mmpose-engine.sh`) and is imported
lazily inside function bodies, so the base app — and `pnpm verify` — run green
without it. `engine_available()` gates the one code path that needs it.
"""

from app.engine.device import DEVICE_CHOICES, resolve_device
from app.engine.engine_status import engine_available, engine_status
from app.engine.keypoints import draw_overlay, normalize_predictions
from app.engine.mmpose_runner import EngineUnavailableError, run_inference

__all__ = [
    "DEVICE_CHOICES",
    "EngineUnavailableError",
    "draw_overlay",
    "engine_available",
    "engine_status",
    "normalize_predictions",
    "resolve_device",
    "run_inference",
]
