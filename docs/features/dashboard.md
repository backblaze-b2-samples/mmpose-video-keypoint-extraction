<!-- last_verified: 2026-08-20 -->
# Feature: Dashboard

## Purpose
Show the write-amplification headline and pose-extraction activity at a glance:
source vs derived bytes, frames and keypoints processed, and runs over time.

## Used By
- UI: `/` (dashboard home)
- API: `GET /stats/pose`, `GET /runs`

## Core Functions
- `apps/web/src/components/dashboard/pose-stats-cards.tsx` — runs, frames, keypoints, amplification cards
- `apps/web/src/components/dashboard/amplification-card.tsx` — source → derived bytes and ratio (the headline)
- `apps/web/src/components/dashboard/runs-activity-chart.tsx` — runs created per day
- `apps/web/src/components/dashboard/recent-runs-table.tsx` — most recent runs, linking to detail
- `services/api/app/service/pose_stats.py::get_pose_stats` — aggregation across run manifests
- `apps/web/src/lib/queries.ts` — `usePoseStats()`, `useRuns()`

## Canonical Files
- Dashboard aggregation: `services/api/app/service/pose_stats.py`
- Dashboard layout: `apps/web/src/app/page.tsx`

## Inputs
- None (loads automatically)

## Outputs
- `GET /stats/pose` → `PoseStats` (run counts, frames/keypoints processed, source/derived bytes, amplification ratio, per-day activity)
- `GET /runs` → `RunRecord[]` for the recent-runs table

## Flow
- Page loads → `usePoseStats()` reads every run manifest and aggregates done-run summaries; `useRuns()` feeds the recent-runs table.
- The amplification card shows `source_bytes_human → derived_bytes_human` and the ratio — the B2 write-amplification story every source frame creates.
- The activity chart plots runs created per day; the table links each run to `/runs/[id]`.

## Edge Cases
- API unavailable → inline ErrorState with retry.
- No runs yet → empty chart + "No runs yet" table state; amplification shows "—".
- Only pending/error runs → amplification stays "—" until a run completes with derived bytes.

## UX States
- Loading: an on-screen loading notice above the cards, with skeletons
- Empty: "No runs yet"
- Loaded: populated cards, amplification card, chart, and recent-runs table

## Verification
- Test files: `services/api/tests/test_runs.py::test_pose_stats`
- Required cases: stats with a done run (amplification computed), empty state, API error fallback
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_runs.py`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when the E2E/live prerequisites in [Verification](../verification.md#non-live-verification) are available
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Pose-extraction runs](pose-extraction-runs.md)
- [App Workflows](../app-workflows.md)
