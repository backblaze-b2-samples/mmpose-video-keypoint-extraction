<!-- last_verified: 2026-08-20 -->
# Feature: Pose-Extraction Runs (primary entity)

## Purpose
Manage the lifecycle of an Extraction Run — the primary entity that ties a
source session to a model configuration and its derived keypoint artifacts.

## Used By
- UI: `/runs` (list + create), `/runs/[id]` (detail: overlays, per-frame keypoints, edit, delete, execute)
- API: `GET/POST /runs`, `GET/PATCH/DELETE /runs/{run_id}`, `POST /runs/{run_id}/execute`

## Core Functions
- `services/api/app/types/runs.py` — `RunRecord`, `CreateRunRequest`, `UpdateRunRequest`, `FrameKeypoints`, `RunSummary`
- `services/api/app/service/runs.py` — CRUD + `execute_run` (engine gate, background thread)
- `services/api/app/repo/runs.py` — B2 manifest persistence (`save_manifest`, `load_manifest`, `delete_run`)
- `apps/web/src/components/runs/run-form.tsx` — `CreateRunForm` + `EditRunForm`
- `apps/web/src/components/runs/runs-list.tsx`, `run-detail.tsx`

## Canonical Files
- Pattern exemplar: `services/api/app/service/runs.py`

## Inputs
- CreateRunRequest: label, session, model, kpt_thr (0–1), device
- UpdateRunRequest: label?, notes?, tags? (the source session is fixed at create)

## Outputs
- RunRecord: id, label, session, model, device, kpt_thr, status, timestamps, notes, tags, manifest_key, error, frames, summary
- side effects: `runs/<id>/run.json` written to B2; execute also writes keypoints/overlays/index; delete removes the whole run prefix

## Flow
- **create** — `POST /runs` ← `CreateRunForm`. Validates the session has frames, writes a `pending` manifest.
- **read** — `GET /runs` (list) + `GET /runs/{id}` (detail).
- **edit** — `PATCH /runs/{id}` ← `EditRunForm` (label / notes / tags). Opens pre-filled, no-ops when not dirty.
- **delete** — `DELETE /runs/{id}` ← AlertDialog. Prefix-scoped delete of all run artifacts; source frames untouched.
- **run** — `POST /runs/{id}/execute` ← Execute button (the only heavy-engine path). See [MMPose engine](mmpose-engine.md).

`omitted_ui_verbs`: none — every verb is exposed in the UI.

## Edge Cases
- Create against a session with no frames → 422 `FramesNotFoundError`.
- Execute with the engine absent → 503 `EngineUnavailableError`; run recorded as `error`.
- Execute a `running` run → idempotent no-op (returns the running record).
- Get/patch/delete a missing run → 404 `RunNotFoundError`.
- Threshold outside 0–1 → 422 (Pydantic `Field(ge=0, le=1)`).

## UX States
- Empty: "No runs yet" empty state on `/runs`
- Loading: skeletons; running runs poll their detail page
- Error: destructive Alert on the detail page with the run's error
- Loaded: runs table; detail with summary, overlays, per-frame keypoints

## Verification
- Test files: `services/api/tests/test_runs.py`
- Required cases: create (+ 422), read/list, patch (+ 404), delete (+ 404), execute 503 (engine absent) + 404, threshold validation
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_runs.py`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [MMPose engine](mmpose-engine.md)
- [Keypoints manifest](keypoints-manifest.md)
- [docs/app-workflows.md](../app-workflows.md)
