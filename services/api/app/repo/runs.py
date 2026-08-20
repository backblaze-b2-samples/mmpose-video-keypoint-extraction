"""B2 persistence for sessions and extraction runs (S3-compatible API only).

The Extraction Run is the primary entity and B2 is its sole store: each run is a
`runs/<id>/run.json` manifest plus its derived artifacts, all under the sample
prefix. boto3/botocore stays confined to this repo/ layer. The shared S3 client
(and its custom user agent) is reused from `b2_client` for connection pooling.
"""

from __future__ import annotations

import json

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.b2_object import get_object_bytes
from app.repo.list_cache import invalidate as _invalidate_list_cache


def _base() -> str:
    # sample_prefix always ends with "/" (see config.Settings default).
    return settings.sample_prefix


def sessions_prefix() -> str:
    return f"{_base()}sessions/"


def runs_prefix() -> str:
    return f"{_base()}runs/"


def frames_prefix(session: str) -> str:
    return f"{sessions_prefix()}{session}/frames/"


def run_prefix(run_id: str) -> str:
    return f"{runs_prefix()}{run_id}/"


def manifest_key(run_id: str) -> str:
    return f"{run_prefix(run_id)}run.json"


def keypoints_key(run_id: str, frame: str) -> str:
    return f"{run_prefix(run_id)}keypoints/{frame}.json"


def overlay_key(run_id: str, frame: str) -> str:
    return f"{run_prefix(run_id)}overlays/{frame}.png"


def index_key(run_id: str) -> str:
    return f"{run_prefix(run_id)}keypoints_index.jsonl"


def list_prefix(prefix: str) -> list[dict]:
    """Every object under `prefix` as {Key, Size, LastModified}. Raises RuntimeError."""
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return contents


def list_sessions() -> list[dict]:
    """Group ingested frames by session → [{session, frame_count}], sorted."""
    base = sessions_prefix()
    counts: dict[str, int] = {}
    for obj in list_prefix(base):
        rest = obj["Key"][len(base):]
        if "/frames/" not in rest:
            continue
        session = rest.split("/frames/", 1)[0]
        if session:
            counts[session] = counts.get(session, 0) + 1
    return [
        {"session": s, "frame_count": n}
        for s, n in sorted(counts.items())
    ]


def session_frames(session: str) -> list[dict]:
    """Frame objects for one session as [{frame, key, size}], sorted by name."""
    base = frames_prefix(session)
    frames = []
    for obj in list_prefix(base):
        name = obj["Key"][len(base):]
        if not name or "/" in name:
            continue  # only direct children
        frames.append({"frame": name, "key": obj["Key"], "size": obj["Size"]})
    frames.sort(key=lambda f: f["frame"])
    return frames


def get_frame_bytes(key: str) -> bytes:
    """Download a source frame. Raises RuntimeError on any S3 failure."""
    return get_object_bytes(key)


def put_bytes(key: str, data: bytes, content_type: str) -> int:
    """Write derived bytes to B2 and return the byte count. Raises RuntimeError."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    _invalidate_list_cache()
    return len(data)


def save_manifest(run_id: str, record: dict) -> None:
    """Persist a run manifest as JSON at runs/<id>/run.json."""
    body = json.dumps(record, indent=2, default=str).encode("utf-8")
    put_bytes(manifest_key(run_id), body, "application/json")


def load_manifest(run_id: str) -> dict | None:
    """Read a run manifest, or None if it does not exist."""
    key = manifest_key(run_id)
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e
    return json.loads(response["Body"].read())


def list_run_ids() -> list[str]:
    """Every run id that has a run.json manifest."""
    base = runs_prefix()
    ids = []
    for obj in list_prefix(base):
        rest = obj["Key"][len(base):]
        if rest.endswith("/run.json"):
            ids.append(rest[: -len("/run.json")])
    return ids


def delete_run(run_id: str) -> int:
    """Prefix-scoped delete of every object under runs/<id>/. Returns count.

    Scoped to this run's own prefix so it can never touch another run's or
    another app's data in a shared bucket. Raises RuntimeError on S3 failure.
    """
    client = get_s3_client()
    objects = list_prefix(run_prefix(run_id))
    deleted = 0
    try:
        for i in range(0, len(objects), 1000):
            batch = objects[i : i + 1000]
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": o["Key"]} for o in batch]},
            )
            deleted += len(batch)
    except ClientError as e:
        raise RuntimeError(f"B2 delete failed for run '{run_id}': {e}") from e
    _invalidate_list_cache()
    return deleted
