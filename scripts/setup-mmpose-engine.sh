#!/usr/bin/env bash
# Install the opt-in MMPose engine (torch + mmcv + mmdet + mmpose) into the
# SAME services/api/.venv that `pnpm run setup` created. This is deliberately
# separate from `pnpm run setup`: mmcv has no prebuilt macOS-arm64 wheel and is
# built from source (slow, ~minutes), so keeping it out of the base setup lets
# the base app, `pnpm verify`, and CI stay fast and green without it.
#
# The STEP ORDERING below is load-bearing — do not reorder. It mirrors the
# proven OpenMMLab-on-macOS-arm64 recipe.
#
# CUDA override (Linux + NVIDIA): install torch/torchvision from the CUDA wheel
# index BEFORE running this script, e.g.
#   .venv/bin/pip install "torch>=2.1,<2.4" "torchvision>=0.16,<0.19" \
#     --index-url https://download.pytorch.org/whl/cu121
# then run this script (it will keep the already-installed CUDA build).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$HERE/services/api"
VENV_PIP="$API_DIR/.venv/bin/pip"
VENV_MIM="$API_DIR/.venv/bin/mim"

if [ ! -x "$API_DIR/.venv/bin/python" ]; then
  echo "services/api/.venv not found. Run \`pnpm run setup\` first." >&2
  exit 1
fi

echo "==> [1/5] Base scientific stack: numpy<2, openmim, torch, torchvision (CPU wheels by default)"
"$VENV_PIP" install "numpy<2" "openmim>=0.3.9" \
  "torch>=2.1.0,<2.4.0" "torchvision>=0.16.0,<0.19.0"

echo "==> [2/5] Pin a Python-3.12-safe build toolchain (+ Cython for the xtcocotools source build)"
# openmim drags openxlab, which pins setuptools==60.2.0; its pkg_resources calls
# pkgutil.ImpImporter (removed in 3.12) so mim can't even import. Restore a
# modern-but-not-too-new setuptools: >=70 works, 81 drops the pkg_resources /
# distutils shims mmcv's source build needs. Cython goes here too: xtcocotools
# has no macOS-arm64/py3.12 wheel and its setup.py imports Cython (and numpy) at
# build time, so it must be in the venv before step 4's --no-build-isolation build.
"$VENV_PIP" install --upgrade "setuptools>=70,<81" wheel ninja cython

echo "==> [3/5] Build mmcv from source (no prebuilt macOS-arm64 wheel — budget minutes)"
# --no-build-isolation reuses the venv's 3.12-safe setuptools + torch. The
# CPPFLAGS flag downgrades a hard compile error in torch<2.4's
# c10/util/strong_type.h that current macOS libc++ otherwise forbids.
CPPFLAGS="-Wno-invalid-specialization" "$VENV_MIM" install --no-build-isolation \
  "numpy<2" "mmengine>=0.10.3" "mmcv>=2.1.0,<2.2.0"

echo "==> [4/5] Install mmdet, then the rest of the engine group (mmpose + transitive pins)"
# Hold numpy<2 on the mim command (as step 3 does for mmcv): without it, mim's
# resolver upgrades numpy to 2.x and breaks the mmcv/torch ABI built in steps 1-3.
"$VENV_MIM" install "numpy<2" "mmdet>=3.0.0,<3.4.0"
# --no-build-isolation reuses the venv's numpy<2 + Cython + setuptools so the
# source-built xtcocotools (no macOS-arm64/py3.12 wheel) compiles against them,
# mirroring step 3's mmcv build.
"$VENV_PIP" install --no-build-isolation -r "$API_DIR/requirements-engine.txt"

echo "==> [5/5] Repair setuptools (step 4 can re-pull openxlab's 60.2.0)"
"$VENV_PIP" install --upgrade "setuptools>=70,<81"

echo ""
echo "MMPose engine installed into services/api/.venv."
echo "Next: \`pnpm run seed\` to upload a demo session, then execute a run in the UI."
