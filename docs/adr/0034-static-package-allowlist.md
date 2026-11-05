# ADR-0034: Static package allowlist

Status: Accepted

## Decision

Prepare presentation packages with `scripts/package-static.py`, using an
explicit allowlist: the entry page, repository licence, scene JavaScript/CSS,
JSON data and supported local asset types. Retain licence/credit Markdown
inside `assets/`. Exclude experiment tools, environments, raw datasets,
checkpoints, docs, Git metadata and arbitrary root files by construction.

The script creates a new output directory and never removes or overwrites an
existing directory. It does not deploy or change Pages configuration. Future
mirror/hosting automation must consume this package rather than copy the whole
repository. Training artefacts require a separate validated export into the
presentation data directories before they can be packaged.

## Consequences

Adding Python tools cannot accidentally add their dependencies or raw data to
the page. The published application remains plain static files. New public
asset formats require an explicit allowlist update and package verification.
Refs: #206. This records the packaging boundary before publishing code changes.
