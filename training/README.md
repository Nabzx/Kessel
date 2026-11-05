# CPU experiment tools

These tools are separate from the static investor experience. No policy or
world model is trained by the current page. See ADRs 0031-0034 and the
[interface contract](contracts/README.md).

Use Python 3.12 and uv 0.12.18 or later. The lock file supports Apple Silicon
macOS and x86-64 Linux. Linux resolves PyTorch from its official CPU index;
no CUDA environment is installed. All experiment commands use CPU explicitly.

From this directory:

```sh
uv sync --locked
uv run --locked pytest
```

The project creates its own ignored `training/.venv`. It does not touch a
repository-root `.venv` or another personal environment. To use a separate
temporary environment, set `UV_PROJECT_ENVIRONMENT` to a task-specific path.
Keep generated runs in `training/runs/`, checkpoints in `training/checkpoints/`
and source archives in `training/raw/`; all are ignored. Commit only compact
reviewed reports or validated viewer exports in their intended locations.

`uv lock --upgrade-package <name>` updates a dependency deliberately; rerun
tests and compare the numerical/benchmark effects before accepting an update.
Dependabot covers this uv manifest and GitHub Actions. Vendored Three.js files
remain governed by their explicit version/update procedure. Dependabot changes
are reviewed and re-landed under the maintainer as CONTRIBUTING.md requires.

## Static presentation package

From the repository root, choose a new output directory:

```sh
python3 scripts/package-static.py --output /private/tmp/kessel-static-demo
```

Serve that directory with `python3 -m http.server 8080 --bind 127.0.0.1`.
The package contains only the static entry point, scene code/data, supported
assets and their notices. It does not include Python tools, environments,
raw scans, unexported weights or Git metadata. No deployment is performed.
