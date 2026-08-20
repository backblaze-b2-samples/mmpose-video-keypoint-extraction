"""API tests for sessions, the Extraction Run entity, stats, and Library.

Hermetic: the B2 repo boundary (`app.repo.runs`) is monkeypatched, so no network
is touched. The engine is genuinely absent in the verify venv, so the execute
path exercises the real EngineUnavailable → 503 gate.
"""

from datetime import UTC, datetime

import pytest

from app.repo import runs as runs_repo


def _manifest(run_id="abc123", status="pending", **over):
    now = datetime.now(UTC).isoformat()
    base = {
        "id": run_id,
        "label": "Test run",
        "session": "demo-session",
        "model": "human",
        "device": "auto",
        "kpt_thr": 0.3,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "notes": "",
        "tags": [],
        "manifest_key": f"mmpose-video-keypoint-extraction/runs/{run_id}/run.json",
        "error": None,
        "frames": [],
        "summary": {},
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_engine_status_endpoint(client):
    resp = await client.get("/engine/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["torch_installed"] is False
    assert body["device"] == "cpu"


@pytest.mark.asyncio
async def test_list_sessions(client, monkeypatch):
    monkeypatch.setattr(
        runs_repo, "list_sessions", lambda: [{"session": "demo-session", "frame_count": 12}]
    )
    resp = await client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == [{"session": "demo-session", "frame_count": 12}]


@pytest.mark.asyncio
async def test_session_frames_and_404(client, monkeypatch):
    monkeypatch.setattr(
        runs_repo,
        "session_frames",
        lambda s: [{"frame": "0001.jpg", "key": "k", "size": 1}] if s == "demo-session" else [],
    )
    ok = await client.get("/sessions/demo-session/frames")
    assert ok.status_code == 200
    assert ok.json() == ["0001.jpg"]

    missing = await client.get("/sessions/nope/frames")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_create_run_and_missing_session(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(
        runs_repo,
        "session_frames",
        lambda s: [{"frame": "0001.jpg", "key": "k", "size": 1}] if s == "demo-session" else [],
    )
    monkeypatch.setattr(runs_repo, "save_manifest", lambda rid, rec: saved.update(rec))

    resp = await client.post(
        "/runs",
        json={"label": "My run", "session": "demo-session", "model": "human", "kpt_thr": 0.3, "device": "auto"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["session"] == "demo-session"
    assert saved["label"] == "My run"

    bad = await client.post(
        "/runs",
        json={"label": "x", "session": "ghost", "model": "human", "kpt_thr": 0.3, "device": "auto"},
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_create_run_rejects_out_of_range_threshold(client):
    resp = await client.post(
        "/runs",
        json={"label": "x", "session": "demo-session", "model": "human", "kpt_thr": 5, "device": "auto"},
    )
    assert resp.status_code == 422  # kpt_thr Field(ge=0, le=1)


@pytest.mark.asyncio
async def test_get_run_and_404(client, monkeypatch):
    monkeypatch.setattr(
        runs_repo, "load_manifest", lambda rid: _manifest(rid) if rid == "abc123" else None
    )
    ok = await client.get("/runs/abc123")
    assert ok.status_code == 200
    assert ok.json()["id"] == "abc123"

    missing = await client.get("/runs/zzz")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_patch_run(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(runs_repo, "load_manifest", lambda rid: _manifest(rid))
    monkeypatch.setattr(runs_repo, "save_manifest", lambda rid, rec: saved.update(rec))

    resp = await client.patch("/runs/abc123", json={"label": "Renamed", "tags": ["a", "b"]})
    assert resp.status_code == 200
    assert resp.json()["label"] == "Renamed"
    assert saved["tags"] == ["a", "b"]


@pytest.mark.asyncio
async def test_delete_run_and_404(client, monkeypatch):
    deleted = {}
    monkeypatch.setattr(
        runs_repo, "load_manifest", lambda rid: _manifest(rid) if rid == "abc123" else None
    )
    monkeypatch.setattr(runs_repo, "delete_run", lambda rid: deleted.setdefault("id", rid))

    ok = await client.delete("/runs/abc123")
    assert ok.status_code == 200
    assert ok.json() == {"deleted": True, "id": "abc123"}
    assert deleted["id"] == "abc123"

    missing = await client.delete("/runs/zzz")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_execute_run_without_engine_returns_503(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(runs_repo, "load_manifest", lambda rid: _manifest(rid))
    monkeypatch.setattr(runs_repo, "save_manifest", lambda rid, rec: saved.update(rec))

    resp = await client.post("/runs/abc123/execute")
    assert resp.status_code == 503
    # The run must be recorded as an error, never fabricated as done.
    assert saved["status"] == "error"
    assert "setup:mmpose-engine" in saved["error"]


@pytest.mark.asyncio
async def test_execute_missing_run_404(client, monkeypatch):
    monkeypatch.setattr(runs_repo, "load_manifest", lambda rid: None)
    resp = await client.post("/runs/zzz/execute")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pose_stats(client, monkeypatch):
    done = _manifest(
        "done1",
        status="done",
        summary={
            "frame_count": 2,
            "total_instances": 3,
            "total_keypoints": 34,
            "source_bytes": 1000,
            "derived_bytes": 3200,
            "amplification_ratio": 3.2,
        },
    )
    monkeypatch.setattr(runs_repo, "list_run_ids", lambda: ["done1"])
    monkeypatch.setattr(runs_repo, "load_manifest", lambda rid: done)
    monkeypatch.setattr(
        runs_repo, "list_sessions", lambda: [{"session": "demo-session", "frame_count": 2}]
    )

    resp = await client.get("/stats/pose")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_runs"] == 1
    assert body["runs_done"] == 1
    assert body["derived_bytes"] == 3200
    assert body["amplification_ratio"] == 3.2


@pytest.mark.asyncio
async def test_library(client, monkeypatch):
    def fake_list(prefix):
        if prefix.endswith("sessions/"):
            return [{"Key": "k1", "Size": 100}, {"Key": "k2", "Size": 200}]
        return [{"Key": "r1", "Size": 50}]

    monkeypatch.setattr(runs_repo, "list_prefix", fake_list)
    resp = await client.get("/library")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_objects"] == 3
    assert body["total_bytes"] == 350
    stages = {s["stage"]: s for s in body["stages"]}
    assert stages["sessions"]["object_count"] == 2
    assert stages["runs"]["total_bytes"] == 50
