# Build plan — `mmpose-video-keypoint-extraction`

Source of truth for the starter tree: `.claude/scratch/vcsk-843ba220-8a4b-4963-bcbe-7d76a47ed2d3/`
(cloned fresh in Phase 0). This plan is the contract for the builder and reviewer.

The proven precedent is the shipped sibling `mmdetection3d-lidar-dataset` — same OpenMMLab
family, verified to install and run **natively on macOS arm64 CPU** (no container). The engine
recipe below is copied from that sibling's `setup-mmdet3d-engine.sh` / `requirements-engine.txt`
and adapted `mmdet3d → mmpose`. The builder does NOT need to read any sibling checkout; everything
needed is in this plan.

---

## 1. Purpose

`mmpose-video-keypoint-extraction` is a B2-backed sample for **sports-science teams and
fitness-app developers** who need to extract 2D/3D skeleton keypoints from large video libraries
(match footage, gym sessions, motion capture) to train pose classifiers, rep-counting models, and
biomechanical pipelines. Source frames are ingested to a B2 bucket organized by session; a local
**MMPose** engine runs per frame, producing per-frame keypoint JSON (joint coordinates +
confidence) and a skeleton-overlay PNG, both written back to B2; a `keypoints_index.jsonl` manifest
maps every frame to its derived artifacts; training/analytics pipelines read keypoints and overlays
straight from B2 via the S3-compatible API using the manifest as a dataset index. The headline B2
story is **write amplification**: every source frame fans out into a JSON + an overlay image (plus
an optional summary clip per run), so a 50 GB archive expands to 150+ GB of derived artifacts — B2
is the durable storage layer for the whole workflow, accessed with a custom user-agent over
standard `B2_*` env vars. Runs entirely on local OSS; **B2 credentials are the only keys** (no
second API key, no external provider).

---

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling — strip what pose extraction doesn't need, keep the reusable B2
scaffolding, add the MMPose engine + entity.

### KEEP (as-is — starter contract, do not strip/rename)
- Whole `apps/web/src/components/ui/` shadcn kit + design tokens in `globals.css` + `/design` page.
- **Full-bucket File Explorer** — `/files` route, `apps/web/src/app/files/`,
  `apps/web/src/components/files/*`, its sidebar entry. **Non-negotiable — never removable.**
- **Upload** — `/upload` route + `apps/web/src/components/upload/*` + sidebar entry (repurposed as
  session/video *Ingest*).
- Backend layering `types → config → repo → service → runtime`; the structural tests
  (`test_boto3_only_in_repo`, `test_no_backward_imports`, `test_all_layers_exist`,
  300-line file cap); the single memoized `get_s3_client()` in `repo/b2_client.py`; the
  full-bucket listing cache (`repo/list_cache.py`); rate-limit/timing/CORS middleware order;
  fail-fast B2-config startup check in `main.py`; the OpenAPI contract gate
  (`docs/api/openapi.json` + `api-contract.test.ts`); `pnpm verify` / `check:agent-docs`.
- Agent surface: `AGENTS.md` (authoritative) + thin shims `CLAUDE.md`, `GEMINI.md`,
  `.github/copilot-instructions.md`; `scripts/check-agent-docs.mjs`.

### TRIM / TRANSFORM
- **Dashboard** (`/` + `components/dashboard/*`) — rewrite from generic upload stats to
  pose-extraction metrics (§4). This is the one screen designed to be rewritten.
- **Env var conversion (b2-doctor standard).** The starter ships legacy names
  (`B2_KEY_ID`, `B2_ENDPOINT`, `B2_PUBLIC_URL`). Convert to the standardized set everywhere:
  `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`,
  `B2_PUBLIC_URL_BASE` (last one optional/commented). Derive the endpoint from region:
  `f"https://s3.{settings.b2_region}.backblazeb2.com"` — **no hardcoded region anywhere**.
  Touch: `config/settings.py`, `main.py` `REQUIRED_B2_SETTINGS`/`PLACEHOLDER_VALUES`,
  `repo/b2_client.py`, `.env.example`, `services/api/tests/*`, and every doc that names them.
- **`user_agent_extra` + `utm_content` token** → the single token `b2ai-mmpose-video-keypoint-extraction`
  (check:agent-docs enforces one token across both surfaces).
- **Metadata-extraction** (`service/metadata.py`, `docs/features/metadata-extraction.md`) — keep
  the generic file-detail path (harmless, used by the Files explorer preview); do not expand it.
- Remove the starter's marketing dashboard copy / demo-preference bits that only make sense for a
  file-management template.

### ADD (new for this sample)
- **MMPose engine module** `services/api/app/engine/` (§ engine recipe below): `device.py`
  (`resolve_device`, `DEVICE_CHOICES`), `engine_status.py` (`engine_available()`,
  `engine_status()`), `mmpose_runner.py` (`EngineUnavailableError`, lazy `run_inference`), and a
  base-safe `keypoints.py` (numpy/Pillow-only helpers: keypoint→JSON serialization, overlay-PNG
  compositing that works without the heavy stack for previews).
- **Primary entity = Extraction Run** — `runtime/runs.py`, `service/runs.py`, `repo/runs.py`,
  `types/runs.py`. Persisted as B2 JSON manifest, no database (§ entity below).
- **Sample-scoped "Library" explorer** — `/library` route +
  `apps/web/src/components/library/library-explorer.tsx`: an Accordion grouping objects under
  `SAMPLE_PREFIX` by pipeline stage (`sessions` → `runs`), per-stage counts + byte totals. This is
  the required scoped explorer that sits ALONGSIDE the kept full-bucket Files explorer.
  `SAMPLE_PREFIX = "mmpose-video-keypoint-extraction/"` in `apps/web/src/lib/sample-prefix.ts`,
  mirroring `settings.sample_prefix` (`MMPOSE_PREFIX`).
- **Runs UI** — `/runs` (list) + `/runs/[id]` (detail: overlay gallery, per-frame keypoints,
  manifest download) + `components/runs/run-form.tsx` (`CreateRunForm` + `EditRunForm`).
- **Ingest** — repurpose `/upload` to upload/select a source video or frame session; a seed script
  populates 1–2 demo sessions.
- Engine setup: `scripts/setup-mmpose-engine.sh` + `pnpm run setup:mmpose-engine`; seed:
  `scripts/seed_pose.py` + `pnpm run seed`.

**Bucket-explorer tension note:** none — both explorers coexist as required (full-bucket Files kept
verbatim; scoped Library added).

---

## 3. B2 surface (S3 operations)

All via boto3 S3-compatible API (S3-only; **no b2-native** calls). Confined to `repo/`.
- `put_object` — source frames, per-frame keypoint JSON, overlay PNGs, `keypoints_index.jsonl`
  (`application/x-ndjson`), the `run.json` manifest, optional `summary.mp4`.
- `get_object` — read frames for inference; read results/overlays for serving.
- `list_objects_v2` — full-bucket explorer, scoped Library, manifest build, dashboard stats.
- `head_object` — object metadata.
- `delete_object` — prefix-scoped run deletion.
- `generate_presigned_url` (GET) — download/inline-preview overlays, JSON, manifest.
Custom UA `b2ai-mmpose-video-keypoint-extraction` set once in `get_s3_client()` (and in
`scripts/setup_b2_cors.py` if the presigned-upload path ships one). **No b2-native usage to
justify.**

### B2 key layout (primary entity is the sole store — no DB)
```
mmpose-video-keypoint-extraction/
  sessions/<session>/frames/<frame>.jpg        # ingested source frames
  runs/<run_id>/run.json                        # RunRecord manifest (the entity)
  runs/<run_id>/keypoints/<frame>.json          # per-frame keypoint JSON
  runs/<run_id>/overlays/<frame>.png            # skeleton-overlay images
  runs/<run_id>/keypoints_index.jsonl           # per-frame manifest (dataset index)
  runs/<run_id>/summary.mp4                      # optional stitched overlay clip
```

---

## 4. Key features (seed README + `docs/features/*.md`)

1. **Video/session ingest** → B2, organized by session (`video-ingest` feature).
2. **MMPose keypoint extraction** (primary; `deployment: local`) — per-frame 2D/3D pose via the
   local engine; real keypoint JSON + overlay PNG written to B2.
3. **Write-amplification dashboard** — the headline metric: source bytes vs derived bytes and the
   amplification ratio, frames processed, total instances + keypoints extracted, runs over time.
4. **`keypoints_index.jsonl` dataset manifest** — one line per frame mapping source→JSON→overlay,
   the index training pipelines read (`keypoints-manifest` feature).
5. **Sample-scoped Library explorer** (sessions → runs) alongside the full-bucket Files explorer.
6. **Extraction-run lifecycle** — full CRUD + run on the primary entity (§ entity).

### External API provider
**None.** MMPose is a local OSS engine; the sample's whole point is the on-device engine, so per
`api-provider-selection.md` step 1 the primary feature is **`deployment: local`** (CPU default,
GPU auto-detect). No external provider, no second key, **$0 per demo run** (B2 storage only). The
description names no Genblaze/`genblaze-*` stack → **no Genblaze**; provider-orchestration rule does
not apply.

Per-feature deployment:
- Video/session ingest — `deployment: local` (B2 I/O only).
- MMPose keypoint extraction — **`deployment: local`** (engine on-device; CUDA→CPU auto-detect,
  CPU default; MPS opt-in only — see device policy).
- Dashboard / manifest / explorers — `deployment: local` (B2 reads).

### Primary-entity lifecycle (mandatory)
**Primary entity: the Extraction Run.** All five verbs are user-accessible and Phase 2 builds each:
- **create** — `POST /runs` ← `CreateRunForm` (pick session, model, threshold, device; label).
- **read** — `GET /runs` (list page) + `GET /runs/{id}` (detail: overlay gallery, per-frame
  keypoints table, manifest download).
- **edit** — `PATCH /runs/{id}` ← `EditRunForm` (label / notes / tags; source session is fixed at
  create — a re-config is a new run).
- **delete** — `DELETE /runs/{id}` ← AlertDialog in the runs list/detail (prefix-scoped delete of
  all run artifacts).
- **run** — `POST /runs/{id}/execute` ← "Execute" button (the only heavy-engine path).

**`omitted_ui_verbs`: none.** Every verb the app supports is exposed in the UI.

### Form UX conventions (`components/runs/run-form.tsx`)
Finite-option fields → `Select` (never free text), on BOTH create and edit:
- `model` — `Select`: `human` (default) · `wholebody` · `hand` · `human3d`.
- `device` — `Select`: `auto` (default) · `cpu` · `cuda` · `mps`.
- `session` — `Select` populated from `GET /sessions` (`{session} ({frame_count} frames)`).
Free text: `label` (Input); `kpt_thr` is a bounded number input (0–1).
CREATE-only safe-default hints as `FormDescription` (never an autofill button):
- model hints: "human — 17 COCO body keypoints, CPU-friendly, recommended default",
  "wholebody — 133 keypoints (body+feet+face+hands)", "hand — 21 hand keypoints",
  "human3d — 3D lifted keypoints".
- threshold hint: "Keypoint confidence cutoff, 0–1. Default 0.3."
- device hint: "auto → CUDA if present, else CPU."
Edit form opens pre-filled from the stored run and no-ops when not dirty. Exemplar to match:
starter's `components/settings/settings-form.tsx`.

### Pydantic types (`types/runs.py`)
```python
ModelName   = Literal["human", "wholebody", "hand", "human3d"]  # MMPoseInferencer aliases
DeviceChoice= Literal["auto", "cpu", "cuda", "mps"]
RunStatus   = Literal["pending", "running", "done", "error"]
```
- `FrameKeypoints` — frame, source_key, keypoints_key, overlay_key, num_instances,
  num_keypoints, mean_score.
- `RunSummary` — frame_count, total_instances, total_keypoints, source_bytes, derived_bytes,
  amplification_ratio.
- `RunRecord` — id, label, session, model, device, kpt_thr, status, created_at, updated_at,
  notes, tags, manifest_key, frames: list[FrameKeypoints], summary: RunSummary.
- `CreateRunRequest` — label, session, model, kpt_thr (Field ge=0 le=1 default 0.3), device.
- `UpdateRunRequest` — label?, notes?, tags? (no session).
- `SessionInfo` — session, frame_count (populates the create-form Select).
- `EngineStatus` — available, device, torch_installed, detail.

### Endpoints (`runtime/runs.py`)
`GET /engine/status`, `GET /sessions`, `GET /sessions/{session}/frames`, `GET /runs`,
`POST /runs`, `GET /runs/{run_id}`, `PATCH /runs/{run_id}`, `DELETE /runs/{run_id}`,
`POST /runs/{run_id}/execute`. Handlers hold no business logic; map `RunNotFoundError`→404,
`EngineUnavailableError`→503, `FramesNotFoundError`→422. Every route change re-exports
`docs/api/openapi.json` and updates `lib/api-client.ts` + `lib/queries.ts`; backend-only routes go
in `SERVER_ONLY_OPERATIONS`.

---

## MMPose engine recipe (copy verbatim, adapt mmdet3d→mmpose)

### Requirements split (three files)
**`services/api/requirements.txt`** (base, `>=` only, locked): starter base **plus** keep
`numpy>=1.26.0,<2.0.0` (ABI-compatible with the engine group), `Pillow>=11.0.0`, and add
`imageio-ffmpeg>=0.5.0` (license-clean frame extraction at seed time — resolves ffmpeg via
`imageio_ffmpeg.get_ffmpeg_exe()`, no system ffmpeg needed). No mm*/torch/opencv in base.

**`services/api/requirements-engine.txt`** (opt-in, NOT installed by `pnpm run setup`, NOT locked;
loose ranges validated at verify):
```
numpy<2
torch>=2.1.0,<2.4.0
torchvision>=0.16.0,<0.19.0
openmim>=0.3.9
mmengine>=0.10.3
mmcv>=2.1.0,<2.2.0
mmdet>=3.0.0,<3.4.0
mmpose>=1.3.0,<1.4.0
# transitive pins the mim source-build resolver / mmpose setup tends to miss
platformdirs>=3.5
ftfy>=6.1.0
regex>=2023.0.0
json_tricks>=3.16.0
munkres>=1.1.4
xtcocotools>=1.14
opencv-python-headless>=4.8,<4.12   # 5.x forces numpy 2 — hold to 4.x
matplotlib>=3.7,<3.10               # MMPose visualization backend
```
**`services/api/requirements.lock`** — base only (Python 3.12), regenerated from a clean venv.
mm*/torch stay out of the lock.

### `scripts/setup-mmpose-engine.sh` (mirror the sibling's ordering — load-bearing)
1. `pip install "numpy<2" "openmim>=0.3.9" "torch>=2.1.0,<2.4.0" "torchvision>=0.16.0,<0.19.0"`
   (CPU wheels by default; document the CUDA index override).
2. `pip install --upgrade "setuptools>=70,<81" wheel ninja`
   — openmim drags openxlab which pins `setuptools==60.2.0` (its `pkg_resources` calls
   `pkgutil.ImpImporter`, removed in Py 3.12, so mim can't import); restore `>=70,<81` (81 drops the
   `pkg_resources`/`distutils` shims mmcv's source build needs).
3. `CPPFLAGS=-Wno-invalid-specialization mim install --no-build-isolation "numpy<2" "mmengine>=0.10.3" "mmcv>=2.1.0,<2.2.0"`
   — no prebuilt macOS-arm64 mmcv wheel, so it builds from source (slow, ~minutes — budget for it);
   `--no-build-isolation` uses the venv's 3.12-safe setuptools+torch; the `CPPFLAGS` flag downgrades
   a hard compile error in torch<2.4's `c10/util/strong_type.h` that current macOS libc++ forbids.
4. `mim install "mmdet>=3.0.0,<3.4.0"` then `pip install -r requirements-engine.txt` (installs
   `mmpose` + the rest). (Alternatively `mim install "mmpose>=1.3.0,<1.4.0"`.)
5. Final `pip install --upgrade "setuptools>=70,<81"` repair (step 4 can re-pull openxlab's 60.2.0).
Wire `pnpm run setup:mmpose-engine` → this script; installs into the SAME `services/api/.venv`.

### Engine module (`services/api/app/engine/`)
- `device.py`: `DEVICE_CHOICES = ("auto","cpu","cuda","mps")`; `resolve_device(preference="auto")`
  → `_torch()` (returns torch or None), `_cuda_available`, `_mps_available`. Policy: no torch →
  `"cpu"`; `cpu`→cpu; `cuda`→cuda-if-avail-else-cpu; `mps`→mps-if-avail-else-cpu (explicit opt-in);
  **`auto` → cuda if avail else cpu (MPS deliberately skipped on auto)**. Rationale in docstring:
  mmcv/mmdet custom ops (NMS, deform-conv used by the bundled RTMDet person detector) lack MPS
  kernels, so `auto` stays on the safe CUDA→CPU path — matches the OpenMMLab-on-macOS-arm64
  build constraint ("weak/no MPS support → fall back CUDA→CPU, note it"). `mps` remains an explicit
  opt-in for users who want to try it.
- `engine_status.py`: `engine_available()` — tries `import mmcv, mmdet, mmpose, torch`; returns
  bool, never raises. `engine_status(device_preference="auto")` → `{available, device,
  torch_installed, detail}`, cheap + side-effect free (no inference), detail points at
  `pnpm run setup:mmpose-engine`.
- `mmpose_runner.py`: `class EngineUnavailableError(RuntimeError)`. `run_inference(frame_bytes, *,
  model, device, kpt_thr=0.3) -> dict` — lazy-imports `from mmpose.apis import MMPoseInferencer`
  inside the body; maps `model` alias → inferencer args (`human`/`wholebody`/`hand` = 2D
  top-down; `human3d` = `MMPoseInferencer(pose3d="human3d")`); writes the frame to a temp path,
  runs, unlinks in `finally`; returns keypoints (x, y, score) + optional 3D coords per instance.
  Catches `ImportError` → re-raise `EngineUnavailableError` with the install hint; raise it too when
  the engine is absent — **never fabricate a done result** (`engine_available()` gate in
  `service/runs.execute_run`, which writes an `error` manifest and raises rather than fake-green).
- `keypoints.py` (base-safe, numpy/Pillow only, no heavy imports at module top): serialize
  keypoints → JSON; composite a skeleton-overlay PNG for the preview path so the base app can
  render something without the engine.
- **Weights auto-download**: `MMPoseInferencer` fetches checkpoints from the OpenMMLab zoo on first
  use (multi-minute cold). Surface a `running`/"preparing model" status on the execute path so it
  doesn't read as a hang (build-constraint), and have verify pre-warm the default model.

---

## 5. Seeding & license-safe demo data (`scripts/seed_pose.py`, `pnpm run seed`)

Pose estimation is the retrieval-style exception in the build constraints: **synthetic color-bar
input never activates detection** (no person → zero keypoints), so the demo must ingest real,
distinguishable content with visible human figures.

- **Default seed = verified-license footage with visible human figures, fetched at seed time (never
  committed to git).** Prefer **Blender open-movie CC-BY clips** (e.g. Sintel — a realistic CGI
  humanoid) over real people, per the sensitive-content asset rule; decode a short clip to a TINY
  frame set (**≤16 frames**, keep verify/screenshots fast) with `imageio_ffmpeg.get_ffmpeg_exe()`,
  upload to B2 as 1–2 demo sessions under `sessions/<session>/frames/`.
- **Empirical gate (builder MUST verify):** confirm the default model (`human`) detects a figure
  and produces **non-zero keypoints** on the seeded frames. If the chosen CGI figure under-detects,
  fall back to **MMPose's own Apache-2.0 demo images** (`open-mmlab/mmpose/tests/data/`,
  license-clean project fixtures) fetched at runtime. Record the FINAL source + license in the plan
  addendum, `README.md`, and `docs/features/mmpose-engine.md` (§Data & license).
- Gate any at-runtime fetch behind an env flag (e.g. `MMPOSE_USE_DEMO_DATA=1`) and default `--apply`
  to fetch the license-clean footage so the out-of-box demo shows real skeletons. Keep a
  `--synthetic` offline fallback that exercises plumbing only (documented as yielding zero
  keypoints). boto3 stays in `repo/` (`from app.repo import runs as repo`); `--apply` uploads,
  dry-run by default.
- Env: `MMPOSE_DEMO_SESSION` (default `demo-session`), `MMPOSE_PREFIX`, `MMPOSE_DEVICE`,
  `MMPOSE_MODEL_CONFIG` (override the alias→config), `MMPOSE_USE_DEMO_DATA`.

---

## 6. Doc transforms

- **Keep/adapt:** `file-browser.md`, `file-upload.md` (→ note session ingest), `settings.md`,
  `metadata-extraction.md`, `_template.md`; **rewrite** `dashboard.md` for pose metrics.
- **Add (fixed skeleton from `_template.md`):**
  `pose-extraction-runs.md` (primary entity, CRUD+run, verification), `keypoints-manifest.md` (the
  JSONL index + serve/query story), `mmpose-engine.md` (Device policy, Model zoo finite-Select
  table, Data & license, Verification), `video-ingest.md`, `session-library.md` (scoped explorer).
- **README:** retitle to `# MMPose Video Keypoint Extraction`; adapt "What it looks like"
  (screenshots referenced but NOT created here — later pipeline step: `dashboard`, `ingest`,
  `runs`, `run-detail`, `library`), "Core Features", "When to use / When not to use", "Why
  Backblaze B2?" (lead with the write-amplification story), FAQ. Keep the humans-first section order
  from the starter (quick start + visual proof early; governance/FAQ lower). B2 links carry
  `utm_content=b2ai-mmpose-video-keypoint-extraction` or the `https://blze.ai/storage` short link.
- Update `ARCHITECTURE.md` (engine module + B2 key layout + the two-explorer split + the mmcv/MPS
  UA-surface note), `docs/verification.md` (engine install is off the base critical path; real-pose
  verification needs `setup:mmpose-engine` + seeded footage), `AGENTS.md` doc-map rows, and
  register any new gate in `check-agent-docs.mjs` if one is added.

---

## 7. Rename table (`vibe-coding-starter-kit` → `mmpose-video-keypoint-extraction`)

| Kind | From | To |
|---|---|---|
| kebab / repo dir / `package.json` `name` / pnpm-workspace | `vibe-coding-starter-kit` | `mmpose-video-keypoint-extraction` |
| Display name (`apps/web/src/lib/app-config.ts` `APP_NAME`) | `Vibe Coding Starter Kit` | `MMPose Video Keypoint Extraction` |
| `APP_DESCRIPTION` | file-management template blurb | `Extract 2D/3D pose keypoints from video libraries with MMPose, stored on Backblaze B2` |
| `API_TITLE` / description (`main.py`) | derives from `APP_NAME` (check:agent-docs) | derives from `APP_NAME` |
| user-agent + UTM token | `b2ai-oss-start` | `b2ai-mmpose-video-keypoint-extraction` |
| Sample prefix (`lib/sample-prefix.ts` + `settings.sample_prefix`) | — | `mmpose-video-keypoint-extraction/` (`MMPOSE_PREFIX`) |
| Engine env prefix | — | `MMPOSE_*` (`MMPOSE_DEVICE`, `MMPOSE_PREFIX`, `MMPOSE_DEMO_*`, `MMPOSE_MODEL_CONFIG`, `MMPOSE_USE_DEMO_DATA`) |
| pnpm engine/seed scripts | — | `setup:mmpose-engine`, `seed` |
| Railway/Vercel project names, `railway.json`/`vercel.json` | `vibe-coding-starter-kit` | `mmpose-video-keypoint-extraction` |
| README H1, `<!-- labs-project-page -->`, screenshot filenames | starter | `mmpose-video-keypoint-extraction` / `{dashboard,ingest,runs,run-detail,library}.png` |

Env-var rename (b2-doctor): `B2_KEY_ID`→`B2_APPLICATION_KEY_ID`, `B2_ENDPOINT`→`B2_REGION`
(endpoint derived), `B2_PUBLIC_URL`→`B2_PUBLIC_URL_BASE`; `B2_APPLICATION_KEY`/`B2_BUCKET_NAME`
unchanged.

---

## Verify contract
- Base `pnpm verify` stays green **without** the heavy engine (lazy imports; engine off the
  critical path).
- Structural: boto3 only in `repo/`; layering + file-size gates hold; OpenAPI contract in sync.
- b2-doctor green: S3-only, UA on the S3 client, standardized `B2_*` names, no hardcoded region,
  UTM on backblaze.com links.
- Real-pose proof (engine installed + seeded footage): a run produces **non-zero keypoints**, JSON +
  overlays + `keypoints_index.jsonl` land in B2, and the dashboard shows a derived>source
  amplification ratio.
