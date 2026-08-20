<!-- last_verified: 2026-08-20 -->
# App Workflows

User journeys inside the application.

## Ingest a Session

- User seeds a demo session with `pnpm run seed` (fetches license-clean footage, decodes ≤16 frames, uploads them under `sessions/<session>/frames/`), or uploads their own frames/clips at `/upload` (Ingest).
- Uploads go **directly from the browser to B2** (presigned PUT); the queue survives navigation and reports per-file progress.
- Ingested sessions then appear in the create-run session Select and in the Library.
- See: [Video / Session Ingest](features/video-ingest.md), [File Upload](features/file-upload.md)

## Create and Run an Extraction

- User navigates to `/runs` and clicks **New run**.
- The form uses Selects for finite-option fields: session (from `GET /sessions`, shown as `name (N frames)`), model (`human` default · `wholebody` · `hand` · `human3d`), device (`auto` default · `cpu` · `cuda` · `mps`); a bounded number input for `kpt_thr` (0–1, default 0.3); and a free-text label. Create-only hints describe each model and the safe defaults.
- Submitting creates a `pending` run (its `run.json` manifest is written to B2) and navigates to the run detail page.
- On the detail page the user clicks **Execute**. If the engine isn't installed the button is disabled with an install hint and the API would return 503 (recording an `error` run — never a fake result). Otherwise the run goes `running` and the page auto-refreshes while a background thread runs inference per frame and writes keypoints, overlays, and the manifest to B2.
- See: [Pose-Extraction Runs](features/pose-extraction-runs.md), [MMPose Keypoint Extraction](features/mmpose-engine.md)

## Inspect a Run

- User opens `/runs/[id]`.
- Header shows the label, a live status badge, and the config; a summary shows frames, instances, keypoints, source→derived bytes, and the amplification ratio.
- A skeleton-overlay gallery renders each frame's overlay (presigned inline URLs); a per-frame table lists instances/keypoints/mean score with an "Open JSON" link; buttons open `run.json` and `keypoints_index.jsonl`.
- The user can edit label/notes/tags (source session is fixed), re-run, or delete (prefix-scoped delete of all run artifacts).
- See: [Pose-Extraction Runs](features/pose-extraction-runs.md), [Keypoints Manifest](features/keypoints-manifest.md)

## Browse the Library (scoped) and Files (whole bucket)

- `/library` shows everything this sample wrote to B2 under `MMPOSE_PREFIX`, grouped by stage (sessions → runs) with per-stage counts and byte totals.
- `/files` is the kept full-bucket explorer: tree view, preview, download, delete — it browses the entire bucket, not just this sample's prefix.
- See: [Session Library](features/session-library.md), [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home).
- The write-amplification card leads: source bytes vs derived bytes and the ratio (every frame fans out into keypoint JSON + an overlay).
- Stat cards show extraction runs, frames processed, keypoints extracted, and the amplification ratio; a chart shows runs per day; a table lists recent runs linking to their detail pages.
- Empty state: "No runs yet".
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`.
- A banner states the page is mostly a demonstration: only Theme is wired up for real; the rest showcases what a settings page can look like when you adapt the kit.
- **Theme** (real) applies immediately and persists (`next-themes`); the header toggle drives the same state. Other fields are labelled "Demo field", persist to `localStorage` only, and drive no behaviour. Danger Zone actions are a demo.
- See: [Settings](features/settings.md)
