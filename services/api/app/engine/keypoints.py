"""Base-safe keypoint helpers: JSON serialization + skeleton-overlay rendering.

Deliberately imports only numpy and Pillow — never torch / mmcv / mmpose — so
the base app (and `pnpm verify`, with no engine installed) can normalize stored
predictions and re-render overlays from them. The heavy engine produces raw
predictions; everything downstream of that is done here.
"""

from __future__ import annotations

import io
from typing import Any

# COCO-17 body skeleton (0-based indices), used to connect keypoints when an
# instance has at least the 17 body joints. Wholebody/hand/3d models emit more
# (or differently ordered) points; we still plot every point as a dot and only
# add these body edges when the indices are present, so nothing ever crashes on
# an unexpected keypoint count.
COCO17_SKELETON: tuple[tuple[int, int], ...] = (
    (15, 13), (13, 11), (16, 14), (14, 12), (11, 12),
    (5, 11), (6, 12), (5, 6), (5, 7), (6, 8),
    (7, 9), (8, 10), (1, 2), (0, 1), (0, 2),
    (1, 3), (2, 4), (3, 5), (4, 6),
)


def _as_floats(values: Any) -> list[float]:
    return [float(v) for v in values]


def normalize_predictions(instances: list[dict], kpt_thr: float = 0.3) -> dict:
    """Normalize one frame's raw MMPose instances into a JSON-safe summary.

    `instances` is the per-frame list MMPoseInferencer yields under
    `predictions`. Each entry carries `keypoints` (2 or 3 coords each) and
    `keypoint_scores`. Returns counts + a compact per-instance keypoint list
    where every keypoint is `[x, y, score]` (plus `keypoints_3d` when the model
    is a 3D lifter). "Visible" means score >= `kpt_thr`.
    """
    norm_instances: list[dict] = []
    total_visible = 0
    score_accum = 0.0
    score_n = 0

    for inst in instances:
        raw_kpts = inst.get("keypoints") or []
        scores = inst.get("keypoint_scores")
        if scores is None:
            scores = [1.0] * len(raw_kpts)
        scores = _as_floats(scores)

        kpts_2d: list[list[float]] = []
        kpts_3d: list[list[float]] = []
        is_3d = False
        for point, score in zip(raw_kpts, scores, strict=False):
            coords = _as_floats(point)
            if len(coords) >= 3:
                is_3d = True
                kpts_3d.append([coords[0], coords[1], coords[2]])
                x, y = coords[0], coords[1]
            else:
                x, y = [*coords, 0.0, 0.0][:2]
            kpts_2d.append([x, y, score])
            if score >= kpt_thr:
                total_visible += 1
            score_accum += score
            score_n += 1

        mean_score = round(sum(s for *_, s in kpts_2d) / len(kpts_2d), 6) if kpts_2d else 0.0
        entry: dict = {
            "keypoints": [[round(x, 3), round(y, 3), round(s, 6)] for x, y, s in kpts_2d],
            "num_keypoints": len(kpts_2d),
            "mean_score": mean_score,
        }
        if is_3d:
            entry["keypoints_3d"] = [[round(c, 4) for c in p] for p in kpts_3d]
        norm_instances.append(entry)

    return {
        "num_instances": len(norm_instances),
        "num_keypoints": total_visible,
        "mean_score": round(score_accum / score_n, 6) if score_n else 0.0,
        "kpt_thr": kpt_thr,
        "instances": norm_instances,
    }


def _draw_skeleton(draw, keypoints: list[list[float]], kpt_thr: float) -> None:
    n = len(keypoints)
    # Edges first so joints paint on top.
    if n >= 17:
        for a, b in COCO17_SKELETON:
            if a >= n or b >= n:
                continue
            xa, ya, sa = keypoints[a]
            xb, yb, sb = keypoints[b]
            if sa >= kpt_thr and sb >= kpt_thr:
                draw.line([(xa, ya), (xb, yb)], fill=(46, 204, 113), width=3)
    for x, y, s in keypoints:
        if s < kpt_thr:
            continue
        r = 4
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(231, 76, 60))


def draw_overlay(frame_bytes: bytes, normalized: dict, kpt_thr: float = 0.3) -> bytes:
    """Composite a skeleton overlay onto the source frame and return PNG bytes.

    Pure Pillow — usable by the engine path (to render its result) and by the
    preview path (to re-render an overlay from stored keypoints without the
    heavy stack). Falls back to returning the frame re-encoded as PNG if the
    image can't be decoded, so a serve path never 500s on a bad frame.
    """
    from PIL import Image, ImageDraw  # lazy import; Pillow is a base dependency

    try:
        img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
    except Exception:
        # Last-resort 1x1 so callers always get valid PNG bytes.
        img = Image.new("RGB", (1, 1), (0, 0, 0))

    draw = ImageDraw.Draw(img)
    for inst in normalized.get("instances", []):
        _draw_skeleton(draw, inst.get("keypoints", []), kpt_thr)

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
