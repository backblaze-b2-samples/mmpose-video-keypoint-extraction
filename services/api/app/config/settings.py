from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Backblaze B2, addressed over the S3-compatible API. The regional endpoint
    # is derived from `b2_region` (see the `b2_endpoint` property) so no region
    # string is ever hardcoded in source — the b2-doctor standard.
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    # Optional: base URL for building public object URLs (only meaningful for a
    # public bucket). The app runs without it — presigned URLs cover private
    # buckets — so it stays optional.
    b2_public_url_base: str = ""

    # Every object this sample writes lives under this prefix, so the scoped
    # Library explorer and prefix-scoped run deletes never touch other apps'
    # data in a shared bucket. Mirrors the frontend `SAMPLE_PREFIX`
    # (apps/web/src/lib/sample-prefix.ts). Read from MMPOSE_PREFIX.
    sample_prefix: str = Field(
        default="mmpose-video-keypoint-extraction/",
        validation_alias="MMPOSE_PREFIX",
    )
    # Default device preference for the MMPose engine ("auto" resolves CUDA →
    # CPU; MPS is opt-in only — see app/engine/device.py). Read from MMPOSE_DEVICE.
    mmpose_device: str = Field(default="auto", validation_alias="MMPOSE_DEVICE")

    api_port: int = 8000
    # Interactive API docs (/docs, /redoc, /openapi.json). On by default for
    # local dev and starter-kit exploration; set false to hide the full API
    # surface in production.
    enable_docs: bool = True
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    # TTL for the presigned PUT the browser uploads directly to B2 with. Long
    # enough for a big file on a slow link, short enough that a leaked URL is a
    # narrow, single-key, single-size window.
    presign_upload_expiry_seconds: int = 900  # 15 minutes

    # Optional confinement for key-addressed reads/deletes. Empty by default so
    # the by-key routes accept any key shape (they deliberately support nested
    # folders and reserved-word segments). Point a fork at a bucket shared with
    # other data? Set to e.g. "uploads/" to restrict all key ops to app uploads.
    allowed_key_prefix: str = ""

    # Full-bucket listing cache (repo/list_cache.py). Both /files and
    # /files/stats need every object, and paginating a 16k-object bucket takes
    # ~8-20s, so one scan is shared. Entries older than the TTL are still
    # served *immediately* while a background thread refreshes them
    # (stale-while-revalidate), so only the very first scan can make a user
    # wait. Uploads and deletes invalidate the cache outright, so the app's own
    # writes are never served stale — only bucket changes made elsewhere can lag
    # by up to this TTL.
    list_cache_ttl_seconds: float = 300.0
    # Scan the bucket once at startup so the first page view doesn't pay for the
    # cold scan. Set false for offline dev or when startup must not touch B2.
    warm_list_cache_on_startup: bool = True

    # Rate limiting (per client IP, per 60s window). In-process per replica —
    # documented in docs/RELIABILITY.md; horizontal scaling needs a shared
    # store (e.g. Redis). Writes/downloads get the tighter cap.
    rate_limit_per_minute: int = 120
    # Covers uploads, deletes, downloads and previews — kept generous enough
    # that a normal browsing/upload session doesn't trip it.
    rate_limit_write_per_minute: int = 60

    # Small durable counters (downloads, etc). Relative paths resolve against
    # the repo root (see repo/counter.py). Point at a persistent volume in
    # production if you care about surviving restarts.
    #
    # It must stay OUTSIDE services/api/: that is the directory `uvicorn
    # --reload` watches in dev, so a counter file there means every download
    # writes into the reloader's watch tree. Today uvicorn only restarts for
    # `*.py`, so the writes surface as misleading "N changes detected" log noise
    # on every download — but a single added `--reload-include` would turn a
    # normal user action into an API restart that drops in-flight requests.
    download_count_file: str = ".data/download_count.json"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Allow populating aliased fields (sample_prefix, mmpose_device) by their
        # Python names too, so tests and internal callers can set them directly.
        "populate_by_name": True,
    }

    @property
    def b2_endpoint(self) -> str:
        """Regional S3 endpoint, derived from `b2_region`.

        Kept as a derived value (never a literal) so the region lives in exactly
        one place — the `B2_REGION` env var — and no region string is baked into
        source. Empty when `b2_region` is unset; startup fails fast in that case
        (see main.REQUIRED_B2_SETTINGS).
        """
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def cors_origins(self) -> list[str]:
        # Drop empties so a trailing comma or API_CORS_ORIGINS="" doesn't yield
        # a stray "" origin.
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


settings = Settings()
