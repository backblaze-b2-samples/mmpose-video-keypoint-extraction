"""Cheap, side-effect-free readiness probe for the MMPose engine.

`engine_available()` answers "can we actually run pose extraction here?" without
running any inference and without ever raising. `engine_status()` wraps it with
the resolved device and an actionable install hint for the UI/API.
"""

from __future__ import annotations

from app.engine.device import _torch, resolve_device

SETUP_HINT = (
    "The MMPose engine (torch + mmcv + mmdet + mmpose) is not installed. "
    "Install it with `pnpm run setup:mmpose-engine`, then re-run the extraction."
)


def engine_available() -> bool:
    """True only when the full pose stack imports cleanly. Never raises.

    Imports the real modules (not just `find_spec`) so a broken ABI — e.g. a
    numpy 2 / torch mismatch — reads as unavailable rather than falsely ready.
    The imports are cached in `sys.modules`, so the cost is paid at most once.
    """
    try:
        # Lazy, importability-only probe (hence the F401 suppressions).
        import mmcv  # noqa: F401
        import mmdet  # noqa: F401
        import mmpose  # noqa: F401
        import torch  # noqa: F401

        return True
    except Exception:
        return False


def engine_status(device_preference: str = "auto") -> dict:
    """Structured engine status for `GET /engine/status`.

    Cheap and side-effect free: it resolves the device and probes importability,
    but runs no inference and downloads no weights.
    """
    torch_mod = _torch()
    torch_installed = torch_mod is not None
    available = engine_available()
    device = resolve_device(device_preference)

    if available:
        detail = f"Engine ready. Inference will run on '{device}'."
    elif torch_installed:
        detail = (
            "torch is installed but mmcv/mmdet/mmpose are missing or failed to "
            f"import. {SETUP_HINT}"
        )
    else:
        detail = SETUP_HINT

    return {
        "available": available,
        "device": device,
        "torch_installed": torch_installed,
        "detail": detail,
    }
