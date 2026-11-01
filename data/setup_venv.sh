#!/usr/bin/env bash
# Sets up the virtualenv for data/generate_rollout.py (ADR-0020).
#
# On macOS, pybullet has no prebuilt wheel and fails to build from
# source out of the box: its vendored zlib's zutil.h collides with
# TARGET_OS_MAC in current macOS SDK headers (bulletphysics/bullet3
# #4607). This script downloads pybullet's source, applies the known
# one-line patch, builds it into the venv, then installs the rest of
# requirements.txt normally. Linux/Windows shouldn't need the patch at
# all (TARGET_OS_MAC is Apple-SDK-specific), but the script applies it
# unconditionally since it's a no-op there either way.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
if ! "$PY" -c "import sys; sys.exit(0 if sys.version_info < (3, 13) else 1)" 2>/dev/null; then
  for cand in python3.12 python3.11 python3.13; do
    if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
  done
fi

"$PY" -m venv .venv
.venv/bin/pip install --quiet --upgrade pip

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
.venv/bin/pip download --no-binary :all: --no-deps pybullet -d "$TMPDIR" --quiet
tar xzf "$TMPDIR"/pybullet-*.tar.gz -C "$TMPDIR"
PYBULLET_SRC=$(find "$TMPDIR" -maxdepth 1 -type d -name "pybullet-*")

ZUTIL_H="$PYBULLET_SRC/examples/ThirdPartyLibs/zlib/zutil.h"
if [ -f "$ZUTIL_H" ]; then
  sed -i.bak \
    's/#if defined(MACOS) || defined(TARGET_OS_MAC)/#if (defined(MACOS) || defined(TARGET_OS_MAC)) \&\& !defined(__APPLE__)/' \
    "$ZUTIL_H"
fi

.venv/bin/pip install --quiet "$PYBULLET_SRC"
.venv/bin/pip install --quiet -r data/requirements.txt

echo "Done. Activate with: source .venv/bin/activate"
