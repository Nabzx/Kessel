# Recorded learned-control technical demo

Serve the repository root and open `docs/phase-11/phase-memory-demo/` in Chrome.
The viewer replays three finite measured recordings from the admitted method:
neural continuous actions with conventional observation-derived phase memory.
It does not run inference or train in the browser. All 96 final outcomes remain
in the catalogue/report; the three displayed records are the first successful
case for each training seed, chosen by case order. Each uses scenario 207600.

The main authored concept is separate. Meshes are visual proxies; actual poses,
joints, physical pile heights and kilogram totals drive playback. Wheels are
fixed visuals because rotation was not retained. Source and case identities
switch with the clock, and record bytes are SHA-256 checked before presentation. An optional readout
shows recorded drive, steer, boom and bucket commands, normalised to -1 through 1.

Native Chrome checks cover laptop, retina/reduced motion, a narrow functional
layout, all recorded machine poses, playback/seek, keyboard, rapid switching,
verified terminal delivery and corrupt-data recovery. GPU/render timings are
retained under `evidence/`. Human comprehension and phone presentation acceptance
are not inferred from those checks.

To create a standalone static preview from the repository root:

```sh
python3 scripts/package-phase-demo.py --output /tmp/new-kessel-recorded-preview
```

Serve the generated folder with a static HTTP server. The ZIP beside it includes
all viewer dependencies, three recordings and study metadata, without Python
training tools or model weights. The production entry point is not changed.

A [verified standalone preview ZIP](offline-preview.zip) is retained for offline sharing.
