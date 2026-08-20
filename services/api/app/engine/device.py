"""Runtime device selection for the MMPose engine.

Auto-detects the best available accelerator, defaulting safely to CPU. torch is
imported lazily (it is part of the opt-in engine group), so this module is
import-cheap and never fails on a base install without the engine.
"""

from __future__ import annotations

DEVICE_CHOICES = ("auto", "cpu", "cuda", "mps")


def _torch():
    """Return the imported torch module, or None when the engine isn't installed."""
    try:
        # Lazy: torch is part of the opt-in engine group, absent on a base install.
        import torch

        return torch
    except ImportError:
        return None


def _cuda_available(torch_mod) -> bool:
    try:
        return bool(torch_mod.cuda.is_available())
    except Exception:
        return False


def _mps_available(torch_mod) -> bool:
    try:
        return bool(torch_mod.backends.mps.is_available())
    except Exception:
        return False


def resolve_device(preference: str = "auto") -> str:
    """Resolve a device *preference* to a concrete torch device string.

    Policy (matches the OpenMMLab-on-macOS-arm64 build constraint: mmcv/mmdet
    custom ops — the NMS and deform-conv the bundled RTMDet person detector
    relies on — have no MPS kernels, so `auto` never picks MPS):

    - torch absent            → "cpu"
    - "cpu"                   → "cpu"
    - "cuda"                  → "cuda" if available else "cpu"
    - "mps"                   → "mps" if available else "cpu"  (explicit opt-in)
    - "auto" (the default)    → "cuda" if available else "cpu"  (MPS skipped)

    Never raises and never hard-requires a GPU: an unknown preference falls
    through to the safe auto path.
    """
    torch_mod = _torch()
    if torch_mod is None:
        return "cpu"

    if preference == "cpu":
        return "cpu"
    if preference == "cuda":
        return "cuda" if _cuda_available(torch_mod) else "cpu"
    if preference == "mps":
        # Opt-in only — the user explicitly asked to try Apple MPS.
        return "mps" if _mps_available(torch_mod) else "cpu"

    # "auto" and any unknown value: CUDA if present, else CPU. MPS is
    # deliberately excluded from auto because the bundled detector's custom ops
    # lack MPS kernels and would crash mid-inference.
    return "cuda" if _cuda_available(torch_mod) else "cpu"
