#!/usr/bin/env python3
"""Seed a license-clean demo pose session into Backblaze B2.

Pose estimation is the retrieval-style exception to the "synthetic input" seed
rule: a color-bar frame activates no person detector (no person -> zero
keypoints), so the out-of-box demo must ingest real, distinguishable content
with visible human figures. This script fetches **verified-license footage**
(Blender open-movie CC-BY clips by default — a realistic CGI humanoid, preferred
over real people), decodes a tiny frame set with the ffmpeg binary bundled by
`imageio-ffmpeg` (no system ffmpeg required), and uploads the frames to B2 under
`sessions/<session>/frames/`.

boto3 stays in the repo layer: all uploads go through `app.repo.runs`.

Usage:
    python scripts/seed_pose.py                 # dry run (default): fetch + decode, upload NOTHING
    python scripts/seed_pose.py --apply         # fetch license-clean footage, upload to B2
    python scripts/seed_pose.py --apply --synthetic   # offline plumbing test (yields ZERO keypoints)

Env:
    MMPOSE_DEMO_SESSION   session name (default: demo-session)
    MMPOSE_PREFIX         object prefix (default: mmpose-video-keypoint-extraction/)
    MMPOSE_DEMO_VIDEO_URL CC-BY clip to decode (default: a Blender open-movie clip)
    MMPOSE_MAX_FRAMES     frames to extract (default: 16; kept tiny for fast verify/screenshots)
    MMPOSE_USE_DEMO_DATA  =1 to fall back to MMPose's Apache-2.0 demo images if the clip fetch fails
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

# Blender open-movie CC-BY clip with a realistic human figure (Sintel — the
# girl protagonist), so the default `human` model detects a person and produces
# non-zero keypoints. Override via MMPOSE_DEMO_VIDEO_URL. If this clip
# under-detects on your machine, set MMPOSE_USE_DEMO_DATA=1 to fall back to
# MMPose's own Apache-2.0 demo images.
DEFAULT_VIDEO_URL = os.environ.get(
    "MMPOSE_DEMO_VIDEO_URL",
    "https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4",
)
# MMPose's own Apache-2.0 demo image (license-clean project fixture) — the
# fallback when the clip can't be fetched and MMPOSE_USE_DEMO_DATA is set.
MMPOSE_DEMO_IMAGES = [
    "https://raw.githubusercontent.com/open-mmlab/mmpose/main/tests/data/coco/000000000785.jpg",
    "https://raw.githubusercontent.com/open-mmlab/mmpose/main/tests/data/coco/000000040083.jpg",
]


def out(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _fetch(url: str, dest: Path) -> None:
    out(f"Fetching {url}")
    # Send a browser-like User-Agent: some CDNs (e.g. download.blender.org) 403
    # the default Python-urllib UA. Applies to every fetch this helper performs.
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as fh:  # noqa: S310
        fh.write(resp.read())


def _decode_frames(video: Path, workdir: Path, max_frames: int) -> list[Path]:
    """Decode up to `max_frames` frames from `video` using imageio's ffmpeg."""
    pattern = str(workdir / "%04d.jpg")
    cmd = [
        _ffmpeg(), "-y", "-i", str(video),
        "-vf", "fps=2,scale=640:-2",
        "-frames:v", str(max_frames),
        "-q:v", "3",
        pattern,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return sorted(workdir.glob("*.jpg"))


def _synthetic_frames(workdir: Path, n: int) -> list[Path]:
    """Offline plumbing-only frames. Documented to yield ZERO keypoints (no person)."""
    from PIL import Image, ImageDraw

    frames = []
    for i in range(n):
        img = Image.new("RGB", (640, 360), (20 + i * 6 % 200, 40, 80))
        d = ImageDraw.Draw(img)
        d.rectangle([40 + i * 5, 40, 200 + i * 5, 300], fill=(200, 200, 60))
        p = workdir / f"{i + 1:04d}.jpg"
        img.save(p, quality=80)
        frames.append(p)
    return frames


def _gather_frames(workdir: Path, synthetic: bool, max_frames: int) -> list[Path]:
    if synthetic:
        out("Generating synthetic frames (offline; these yield ZERO keypoints).")
        return _synthetic_frames(workdir, max_frames)

    try:
        video = workdir / "source.mp4"
        _fetch(DEFAULT_VIDEO_URL, video)
        frames = _decode_frames(video, workdir, max_frames)
        if frames:
            return frames
        out("Decoded no frames from the clip.")
    except Exception as exc:  # noqa: BLE001
        out(f"Clip fetch/decode failed: {exc}")

    if os.environ.get("MMPOSE_USE_DEMO_DATA"):
        out("Falling back to MMPose Apache-2.0 demo images (MMPOSE_USE_DEMO_DATA set).")
        frames = []
        for i, url in enumerate(MMPOSE_DEMO_IMAGES):
            dest = workdir / f"{i + 1:04d}.jpg"
            try:
                _fetch(url, dest)
                frames.append(dest)
            except Exception as exc:  # noqa: BLE001
                out(f"  demo image fetch failed: {exc}")
        return frames

    out(
        "No frames obtained. Set MMPOSE_USE_DEMO_DATA=1 to use MMPose demo images, "
        "or pass --synthetic for an offline plumbing test."
    )
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Upload to B2 (default: dry run).")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Offline plumbing test — generates frames with no person (zero keypoints).",
    )
    args = parser.parse_args()

    session = os.environ.get("MMPOSE_DEMO_SESSION", "demo-session")
    max_frames = int(os.environ.get("MMPOSE_MAX_FRAMES", "16"))

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        frames = _gather_frames(workdir, args.synthetic, max_frames)
        if not frames:
            return 1

        out(f"\nSession: {session}")
        out(f"Frames:  {len(frames)}")

        if not args.apply:
            out("\nDry run — re-run with --apply to upload these frames to B2.")
            return 0

        # boto3 lives in the repo layer.
        from app.repo import runs as repo

        if not repo.settings.b2_bucket_name:
            out("B2 is not configured (see .env). Aborting upload.")
            return 2

        prefix = repo.frames_prefix(session)
        total = 0
        for idx, frame in enumerate(frames, start=1):
            name = f"{idx:04d}.jpg"
            total += repo.put_bytes(prefix + name, frame.read_bytes(), "image/jpeg")
        out(f"\nUploaded {len(frames)} frames ({total} bytes) to {prefix}")
        out("Create a run against this session in the UI, then Execute.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
