# ADR-0020: pybullet for generator-side rock physics

Status: Accepted

## Context

#129 compared pybullet, Rapier-via-Node, MuJoCo and Genesis for
baking real rigid-body physics into `data/generate_rollout.py`
(ADR-0016). pybullet won on fit: pip-installable, zlib-licensed, runs
fully headless (`p.connect(p.DIRECT)`), and its API is close to a
direct match for "create rigid bodies, step, read positions back."

In practice, installing it on this machine (macOS, current Xcode
Command Line Tools) failed: pybullet has no prebuilt wheel for macOS
arm64 on PyPI, and building from source fails compiling its bundled,
outdated vendored zlib (`examples/ThirdPartyLibs/zlib/zutil.c`) --
`TARGET_OS_MAC` is defined by modern macOS SDK headers in a way that
collides with a `#define fdopen(fd, mode) NULL` macro the vendored
zlib never updated for current macOS. This is a known upstream issue
(see [bulletphysics/bullet3#4607](https://github.com/bulletphysics/bullet3/issues/4607)),
not specific to this environment -- it's hit as of pybullet 3.2.7 on
Xcode 16.3+.

## Decision

Still pybullet. The fix is one line: guard the offending macro with
`!defined(__APPLE__)` in the vendored `zutil.h`, which only disables
zlib's own obsolete classic-MacOS codepath (OS_CODE 0x07) -- not a
behaviour this project depends on. `data/setup_venv.sh` applies the
patch automatically as part of setting up the generator's virtualenv,
rather than requiring every contributor on macOS to hit this and fix
it by hand. Linux and Windows aren't expected to need the patch at
all, since `TARGET_OS_MAC` is Apple-SDK-specific.

Rejecting pybullet entirely over this would have meant falling back to
Rapier-via-Node (#129's documented second choice) purely because of a
one-line, well-understood, auto-applied build patch -- a bad trade.

## Consequences

`data/generate_rollout.py` gains its first real dependency (previously
pure stdlib). `data/requirements.txt` plus `data/setup_venv.sh`
document and automate the setup; anyone regenerating `rollout.json`
runs the setup script once rather than a bare `pip install`. The
macOS zlib patch is scoped to a throwaway venv build, not committed
anywhere that affects the shipped site -- this is entirely a
generator-time, developer-machine concern.
