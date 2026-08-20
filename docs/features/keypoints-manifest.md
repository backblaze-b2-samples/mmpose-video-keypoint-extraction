<!-- last_verified: 2026-08-20 -->
# Feature: Keypoints Manifest (dataset index)

## Purpose
Produce a one-line-per-frame `keypoints_index.jsonl` that maps each source frame
to its derived keypoint JSON and overlay, so a training pipeline reads the whole
dataset straight from B2 by streaming a single manifest.

## Used By
- UI: `/runs/[id]` — "Open keypoints_index.jsonl"
- API: written by `POST /runs/{run_id}/execute`; served via presigned GET (`/files-by-key/preview`)

## Core Functions
- `services/api/app/service/extraction.py::run_extraction` — appends one line per frame, uploads the JSONL
- `services/api/app/repo/runs.py::index_key` / `put_bytes`

## Canonical Files
- Pattern exemplar: `services/api/app/service/extraction.py`

## Inputs
- per-frame results (frame, source_key, keypoints_key, overlay_key, counts, mean_score)

## Outputs
- `runs/<id>/keypoints_index.jsonl` on B2, content type `application/x-ndjson`
- side effect: also referenced by the `RunRecord.frames` list in the manifest

## Flow
- During execution each processed frame appends a JSON object to an in-memory list.
- After the last frame, the joined NDJSON is uploaded once as `keypoints_index.jsonl`.
- Consumers list `runs/<id>/` or read the manifest, then stream the JSONL and fetch each `keypoints_key` / `overlay_key` over the S3 API.

## Edge Cases
- A run with zero frames writes no index (nothing to map).
- Re-running overwrites the index for that run id.

## UX States
- Not applicable (data artifact); surfaced via the run detail "Open" buttons.

## Verification
- Test files: `services/api/tests/test_runs.py` (execute path), `services/api/tests/test_engine.py`
- Required cases: index shape mirrors `FrameKeypoints`; content type `application/x-ndjson`
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_runs.py`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: with the engine installed, `keypoints_index.jsonl` lands in B2 with one line per processed frame

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Pose-extraction runs](pose-extraction-runs.md)
- [MMPose engine](mmpose-engine.md)
- [docs/app-workflows.md](../app-workflows.md)
