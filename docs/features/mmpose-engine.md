<!-- last_verified: 2026-08-20 -->
# Feature: MMPose Keypoint Extraction (primary)

## Purpose
Run the local MMPose engine on a session's frames to produce real 2D/3D
skeleton keypoints and skeleton-overlay images, written back to Backblaze B2.

## Used By
- UI: `/runs/[id]` — the Execute button and the overlay gallery
- API: `POST /runs/{run_id}/execute`, `GET /engine/status`
- Job: background extraction thread (`app/service/extraction.py::run_extraction`)

## Core Functions
- `services/api/app/engine/mmpose_runner.py` — `run_inference(...)`, lazy-imports `MMPoseInferencer`, `EngineUnavailableError`
- `services/api/app/engine/device.py` — `resolve_device`, `DEVICE_CHOICES`
- `services/api/app/engine/engine_status.py` — `engine_available()`, `engine_status()`
- `services/api/app/engine/keypoints.py` — `normalize_predictions`, `draw_overlay` (numpy/Pillow only)
- `services/api/app/service/extraction.py` — per-frame loop + B2 writes + summary

## Canonical Files
- Pattern exemplar: `services/api/app/engine/mmpose_runner.py`

## Inputs
- frame bytes: bytes (from B2, per session)
- model: `human | wholebody | hand | human3d` (from the run)
- device: `auto | cpu | cuda | mps` (from the run)
- kpt_thr: float 0–1 (from the run)

## Outputs
- normalized keypoints dict (per instance: `[x, y, score]`, plus `keypoints_3d` for the 3D lifter)
- side effects: per-frame keypoint JSON, overlay PNG, and `keypoints_index.jsonl` written to B2; the run manifest updated to `done`/`error`

## Flow
- `execute_run` gates on `engine_available()`. Engine absent → the run is saved as `error` and the API returns 503 (never a fabricated result).
- Engine present → the run is marked `running` and a background thread runs inference per frame.
- Each frame: `run_inference` → `normalize_predictions` → `draw_overlay`; keypoint JSON + overlay PNG uploaded to B2; a manifest line appended.
- On completion the run is marked `done` with a `RunSummary` (source vs derived bytes, amplification ratio); any failure is recorded as `error`.

## Device policy
`resolve_device(preference)`:
- torch absent → `cpu`
- `cpu` → `cpu`; `cuda` → CUDA if available else `cpu`; `mps` → MPS if available else `cpu` (explicit opt-in)
- `auto` (default) → CUDA if available else `cpu` — **MPS is deliberately skipped on `auto`** because mmcv/mmdet custom ops (the NMS and deform-conv used by the bundled RTMDet person detector) have no Apple MPS kernels and would crash mid-inference. Set device `mps` explicitly to try it.

CUDA override at install time: pass a CUDA wheel index to `scripts/setup-mmpose-engine.sh` (see the script header).

## Model zoo (finite Select on create + edit)
| Model | Keypoints | Notes |
|-------|-----------|-------|
| `human` (default) | 17 COCO body | CPU-friendly, recommended default |
| `wholebody` | 133 (body + feet + face + hands) | heavier |
| `hand` | 21 hand | |
| `human3d` | 3D lifted keypoints | `MMPoseInferencer(pose3d="human3d")` |

`MMPoseInferencer` downloads checkpoints from the OpenMMLab zoo on first use
(multi-minute cold). The execute path reports a `running` / "preparing model"
status so this never reads as a hang; the detail page auto-refreshes.

## Data & license
The default demo seed (`pnpm run seed`, `scripts/seed_pose.py`) fetches
**verified-license footage with visible human figures at seed time — never
committed to git**. It prefers **Blender open-movie CC-BY clips** (e.g. Sintel,
a realistic CGI humanoid) over real people, decodes a tiny frame set (≤16
frames) with `imageio_ffmpeg.get_ffmpeg_exe()`, and uploads it as a demo
session. If the CGI figure under-detects, the fallback is MMPose's own
Apache-2.0 demo images (`open-mmlab/mmpose` test fixtures), fetched at runtime.
The exact final source + license selected for the shipped demo is recorded in
the seed script header and the plan addendum. A `--synthetic` offline fallback
exercises the plumbing only and is documented as yielding zero keypoints.

## Edge Cases
- Engine not installed → `EngineUnavailableError` → 503, run saved as `error` with an install hint.
- A frame with no detectable person → zero keypoints for that frame (synthetic color-bar input never activates detection — hence the real-footage seed).
- Corrupt/undecodable frame → overlay falls back to re-encoding the frame; the run continues.

## UX States
- Empty: no runs / no overlays yet
- Loading: "Running — preparing model & extracting" alert; detail page polls
- Error: the run's `error` message shown in a destructive Alert
- Loaded: overlay gallery + per-frame keypoints table + summary

## Verification
- Test files: `services/api/tests/test_engine.py`, `services/api/tests/test_runs.py`
- Required cases: device policy (auto never picks MPS), engine-absent 503 gate, keypoint normalization + thresholding, overlay PNG output, execute lifecycle
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_engine.py tests/test_runs.py`
- Default pre-PR verify command: `pnpm verify` (runs green without the engine)
- Real-pose proof (engine installed + seeded footage): `pnpm run setup:mmpose-engine` then `pnpm run seed`, execute a run, and confirm non-zero keypoints, JSON + overlays + `keypoints_index.jsonl` in B2, and a derived>source amplification ratio on the dashboard.
- Pass criteria: `pnpm verify` green without the engine; a real run yields non-zero keypoints with the engine installed.

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Pose-extraction runs](pose-extraction-runs.md)
- [Keypoints manifest](keypoints-manifest.md)
- [docs/app-workflows.md](../app-workflows.md)
