"""Unit tests for the MMPose engine helpers (no heavy stack required)."""

import io
from types import SimpleNamespace

from app.engine import device, keypoints
from app.engine.engine_status import engine_available, engine_status


def _fake_torch(cuda: bool, mps: bool):
    return SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: cuda),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)),
    )


def test_resolve_device_without_torch_is_cpu(monkeypatch):
    monkeypatch.setattr(device, "_torch", lambda: None)
    for pref in device.DEVICE_CHOICES:
        assert device.resolve_device(pref) == "cpu"


def test_resolve_device_auto_prefers_cuda_never_mps(monkeypatch):
    # auto must pick CUDA when present and CPU otherwise — never MPS, because the
    # bundled detector's custom ops have no MPS kernels.
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch(cuda=True, mps=True))
    assert device.resolve_device("auto") == "cuda"
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch(cuda=False, mps=True))
    assert device.resolve_device("auto") == "cpu"


def test_resolve_device_explicit_preferences(monkeypatch):
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch(cuda=False, mps=True))
    assert device.resolve_device("mps") == "mps"  # opt-in honoured
    assert device.resolve_device("cuda") == "cpu"  # falls back, never raises
    assert device.resolve_device("cpu") == "cpu"


def test_engine_unavailable_on_base_install():
    # The heavy stack is not installed in the base venv verify runs against.
    assert engine_available() is False
    status = engine_status("auto")
    assert status["available"] is False
    assert status["device"] == "cpu"
    assert "setup:mmpose-engine" in status["detail"]


def test_normalize_predictions_counts_and_thresholds():
    instances = [
        {"keypoints": [[10, 20], [30, 40], [50, 60]], "keypoint_scores": [0.9, 0.1, 0.8]},
    ]
    norm = keypoints.normalize_predictions(instances, kpt_thr=0.5)
    assert norm["num_instances"] == 1
    assert norm["num_keypoints"] == 2  # only scores >= 0.5 count as visible
    assert norm["instances"][0]["num_keypoints"] == 3
    assert norm["instances"][0]["keypoints"][0] == [10.0, 20.0, 0.9]


def test_normalize_predictions_handles_3d():
    instances = [{"keypoints": [[1, 2, 3], [4, 5, 6]], "keypoint_scores": [0.9, 0.9]}]
    norm = keypoints.normalize_predictions(instances, kpt_thr=0.3)
    assert "keypoints_3d" in norm["instances"][0]
    assert norm["instances"][0]["keypoints_3d"][0] == [1.0, 2.0, 3.0]


def test_draw_overlay_returns_png_bytes():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (128, 128, 128)).save(buf, format="JPEG")
    normalized = {"instances": [{"keypoints": [[10, 10, 0.9], [20, 20, 0.9]]}]}
    out = keypoints.draw_overlay(buf.getvalue(), normalized, kpt_thr=0.3)
    assert out[:8] == b"\x89PNG\r\n\x1a\n"  # valid PNG signature
