# Walkthrough narrative study

Refs #407, #415 and #416. This isolated prototype does not change the main
walkthrough. It compares opening routes and camera treatments using existing
hash-validated synthetic records. It is not a new trained policy or an MVP.

From the repository root, serve the files locally:

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

Open <http://127.0.0.1:8080/docs/phase-11/narrative-study/>. Localhost or HTTPS
is required by the existing recorded-bundle integrity checks.

Choose Mine first or Current opening. The latter uses captured stills of the
existing opening, followed by the same five task beats. Play/scrub controls
operate the selected recording. The forecast freezes its actual anchor; the
learner is explicitly a different run. Contact detail can exclude task context.

See the [research report](../../research/2026-11-13-walkthrough-narrative.md)
for the first-minute script, source boundaries and unperformed comprehension
review. [ADR-0058](../../adr/0058-task-first-narrative-study.md) is proposed.

## Verification

Run `node scripts/research/verify-narrative-study.cjs` with the local server
and native Chrome available. It captures the original context scenes, checks
both routes, controls, source changes, forecast anchor, compact layout and
missing-record recovery. It checks every visible loader pose and midpoint at
1440 × 900 and 1365 × 768. A 390 × 844 check covers basic navigation and overflow;
it does not qualify the full desktop controls for phones.

The retained run uses Chrome 157 and ANGLE Metal on Apple M1. It checks 3,007
pose/midpoint projections per desktop profile, 6,014 total, with no page errors.
Ten existing recorded-adapter and material-surface tests also pass. This is
functional/framing evidence, not a rendering performance qualification or
proof that humans understand the story better. No comprehension participants
have been tested.

`evidence/report.json` contains browser diagnostics and captured frame identities.
The source/evidence manifest is checked by
`python3 scripts/verify-narrative-evidence.py`. Screenshots are research artefacts;
their underlying asset credits remain those of the existing repository.
