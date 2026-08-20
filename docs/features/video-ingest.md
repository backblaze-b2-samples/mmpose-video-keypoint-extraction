<!-- last_verified: 2026-08-20 -->
# Feature: Video / Session Ingest

## Purpose
Get source frames into B2, organized by session, so extraction runs have
something to read.

## Used By
- UI: `/upload` (Ingest) — drag-and-drop upload to the bucket
- Script: `pnpm run seed` (`scripts/seed_pose.py`) — the primary demo ingest
- API: `POST /upload/presign`, `POST /upload/verify` (kept starter direct-to-B2 upload)

## Core Functions
- `scripts/seed_pose.py` — decode license-clean footage → frames → upload under `sessions/<session>/frames/`
- `services/api/app/service/upload.py`, `apps/web/src/components/upload/*` — direct-to-B2 upload (kept from the starter)
- `services/api/app/repo/runs.py::list_sessions`, `session_frames`

## Canonical Files
- Pattern exemplar: `scripts/seed_pose.py`

## Inputs
- a video/clip or frame files (upload), or the seed script's fetched footage
- env: `MMPOSE_DEMO_SESSION`, `MMPOSE_PREFIX`, `MMPOSE_USE_DEMO_DATA` (seed)

## Outputs
- `sessions/<session>/frames/<frame>.jpg` objects on B2
- side effect: sessions appear in the create-run Select and the Library explorer

## Flow
- **Seed (recommended demo path):** `pnpm run seed` fetches CC-BY footage, decodes a tiny frame set with `imageio_ffmpeg.get_ffmpeg_exe()`, and uploads frames under a session prefix. Dry-run by default; `--apply` writes.
- **Upload:** the Ingest page uploads files straight to B2 via presigned PUT (bytes never traverse the API), browsable in Files.

## Edge Cases
- No sessions yet → the create-run form shows a "no ingested sessions" hint pointing at `pnpm run seed`.
- `--synthetic` seed → uploads plumbing-only frames documented as yielding zero keypoints.

## UX States
- Empty / Loading / Error / Loaded per the upload component (kept from the starter).

## Verification
- Test files: `services/api/tests/test_upload_validation.py`, `services/api/tests/test_runs.py` (sessions endpoints)
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_runs.py`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: after seeding, `GET /sessions` lists the demo session with a frame count

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [File Upload](file-upload.md)
- [Session Library](session-library.md)
- [docs/app-workflows.md](../app-workflows.md)
