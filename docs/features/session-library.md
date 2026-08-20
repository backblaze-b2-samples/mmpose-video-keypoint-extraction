<!-- last_verified: 2026-08-20 -->
# Feature: Session Library (scoped explorer)

## Purpose
A sample-scoped view of everything this app has written to B2 — grouped by
pipeline stage (sessions → runs) with per-stage object counts and byte totals —
sitting alongside the non-negotiable full-bucket File Explorer.

## Used By
- UI: `/library`
- API: `GET /library`

## Core Functions
- `apps/web/src/components/library/library-explorer.tsx` — Accordion by stage
- `apps/web/src/lib/sample-prefix.ts` — `SAMPLE_PREFIX` (mirrors `settings.sample_prefix`)
- `services/api/app/service/pose_stats.py::get_library`
- `services/api/app/repo/runs.py::list_prefix`

## Canonical Files
- Pattern exemplar: `apps/web/src/components/library/library-explorer.tsx`

## Inputs
- none (reads objects under the sample prefix)

## Outputs
- `LibrarySummary`: prefix, per-stage `{object_count, total_bytes}`, totals

## Flow
- `get_library` lists objects under `sessions/` and `runs/` (both under `MMPOSE_PREFIX`), sums counts and bytes per stage.
- The Accordion shows each stage with its counts; the whole-bucket view stays at `/files`.

## Edge Cases
- Empty prefix → an empty state pointing at ingest + run.
- Large object counts → listing is prefix-scoped and paginated in the repo.

## UX States
- Empty / Loading / Error / Loaded (Accordion of stages).

## Verification
- Test files: `services/api/tests/test_runs.py::test_library`
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_runs.py`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: `GET /library` returns per-stage counts/bytes that sum to the totals

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [File Browser](file-browser.md)
- [docs/app-workflows.md](../app-workflows.md)
