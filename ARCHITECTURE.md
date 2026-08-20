<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard: write-amplification headline, frames/keypoints processed, runs over time
  - Ingest (`/upload`), Runs (`/runs`, `/runs/[id]`), scoped Library (`/library`)
  - Full-bucket File browser (`/files`) — kept from the starter, non-negotiable
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for sessions, the Extraction Run entity (CRUD + execute), stats, library
  - B2 S3 integration via boto3 (frames in; keypoints/overlays/manifest out)
  - The MMPose engine (opt-in, lazy-imported) under `app/engine/`
  - Health check, structured JSON logging, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (RunRecord, PoseStats, …)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, RunRecord, PoseStats, …)
    config/                Settings loaded from environment
    repo/                  B2 S3 client + run/session persistence (data access)
    service/               Business logic (files, upload, runs, extraction, pose_stats)
    engine/                MMPose engine — opt-in, lazy-imported (device, runner, keypoints)
    runtime/               FastAPI route handlers
  tests/                   pytest tests (structural + integration)
```

### The MMPose engine (`app/engine/`)

The engine is compute, not a layer: it takes frame bytes + a config and returns
keypoints, with no B2 or FastAPI knowledge. It is import-cheap — nothing under
`app/engine/` imports torch/mmcv/mmdet/mmpose at module load; those live in the
**opt-in** `requirements-engine.txt` group and are imported lazily inside
function bodies. So the base app, `pnpm verify`, and CI all run green without the
engine installed. `engine_status.engine_available()` gates the one path that
needs it (`service.runs.execute_run`), which records an `error` run and raises
`EngineUnavailableError` (→ 503) rather than fabricating a result. `service/`
orchestrates repo (B2 I/O) + engine (compute); the engine never imports repo.
Device selection auto-detects CUDA → CPU (Apple MPS is opt-in only — the bundled
detector's custom ops have no MPS kernels); see
[docs/features/mmpose-engine.md](docs/features/mmpose-engine.md).

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. The listing cache also owns the only background thread in the app: a stale entry is served immediately while that thread re-scans (stale-while-revalidate), and `main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. Each service's versioned config sits at its own root —
  `railway.json` and `services/api/railway.json` — the default path Railway
  discovers, so a one-click template deploy inherits the same build, start, and
  health behavior with nothing to configure by hand. The human-approved
  staging/production contract lives in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store
  - No application database — the Extraction Run entity is a B2 JSON manifest
  - The regional S3 endpoint is **derived** from `B2_REGION`
    (`https://s3.<B2_REGION>.backblazeb2.com`); no region is hardcoded in source
  - The single boto3 client in `repo/b2_client.py` carries the custom user agent
    `b2ai-mmpose-video-keypoint-extraction` (`user_agent_extra`); all B2 access —
    including run/session persistence in `repo/runs.py` — reuses it

### B2 key layout (under `MMPOSE_PREFIX`, default `mmpose-video-keypoint-extraction/`)

```
mmpose-video-keypoint-extraction/
  sessions/<session>/frames/<frame>.jpg        # ingested source frames
  runs/<run_id>/run.json                        # RunRecord manifest (the entity)
  runs/<run_id>/keypoints/<frame>.json          # per-frame keypoint JSON
  runs/<run_id>/overlays/<frame>.png            # skeleton-overlay images
  runs/<run_id>/keypoints_index.jsonl           # per-frame dataset manifest
```

### Two explorers

- **Full-bucket File Explorer** (`/files`) — the kept starter surface; browses
  the whole bucket. Non-negotiable.
- **Scoped Library** (`/library`) — objects under `MMPOSE_PREFIX` grouped by
  stage (sessions → runs). The two coexist by design.

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Ingest**: `pnpm run seed` (or the Ingest upload) writes frames to `sessions/<session>/frames/` on B2
- **Create run**: Browser -> `POST /runs` -> service validates the session has frames -> writes a `pending` `run.json`
- **Execute** (heavy path): Browser -> `POST /runs/{id}/execute` -> `engine_available()` gate -> run marked `running` -> background thread runs inference per frame -> keypoint JSON + overlay PNG + `keypoints_index.jsonl` written to B2 -> run marked `done` with a summary. Engine absent -> run `error`, API returns 503.
- **Read**: Browser -> `GET /runs` / `GET /runs/{id}` -> service reads manifests from B2
- **Delete**: Browser -> `DELETE /runs/{id}` -> repo prefix-scoped delete of all run artifacts (source frames untouched)
- **File browser / library**: `GET /files` (whole bucket) and `GET /library` (scoped counts) -> repo `list_objects_v2`

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Layered API handler: `services/api/app/runtime/runs.py`
- Service orchestration: `services/api/app/service/runs.py`, `service/extraction.py`
- MMPose engine: `services/api/app/engine/mmpose_runner.py`, `engine/device.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`, `repo/runs.py`
- Pydantic models: `services/api/app/types/` (`runs.py`, `files.py`, `upload.py`, `stats.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- OpenAPI contract: `docs/api/openapi.json`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [MMPose Keypoint Extraction](docs/features/mmpose-engine.md)
- [Pose-Extraction Runs](docs/features/pose-extraction-runs.md)
- [Keypoints Manifest](docs/features/keypoints-manifest.md)
- [Video / Session Ingest](docs/features/video-ingest.md)
- [Session Library](docs/features/session-library.md)
- [Dashboard](docs/features/dashboard.md)
- [File Browser](docs/features/file-browser.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
