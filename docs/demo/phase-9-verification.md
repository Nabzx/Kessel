# Phase 9 verification

Measured 2026-11-01T22:44:28.419Z. The complete local mission and online Google
satellite view passed in Chromium using the native Apple M1 Metal renderer.
The mobile profile uses the same GPU with 4x CPU throttling and a phone-sized
viewport. Physical-phone performance remains unverified.

## Functional checks

- Earth, four environment cards, planned-biome feedback and Rutongo descent.
- Surface arrival, Google satellite view, retained provider credits and 3D-site switch.
- Portal loading and transition, cutaway network and red route visibility.
- Pre-computed optimisation, staggered green routes and before/after metrics.
- Fleet cards, truck picking, moving follow camera and return without resetting the result.
- Loading with the existing excavator, hauling, stationary tipping and empty return.
- Three prediction horizons, error scale and clear scripted labels.
- Sources dialog; Escape closes the dialog before returning from truck inspection.
- Portrait and landscape layouts without document overflow.
- Opening copy and environment controls remain separate at 1280 x 720,
  1440 x 900, 390 x 844 and 844 x 390; flight skip stays clear of Sources.
- No page errors on desktop, mobile or the throttled-network mission.
- No external requests for the complete core flow with `?offline=1`.
- Mission graph validation and JavaScript syntax checks.

## Vehicle correctness

A 120-second deterministic route exercise visited all four haul phases.
The truck tipped its bed, returned empty and retained finite coordinates.
A final displacement-based heading check returned a minimum forward dot
product of 0.9785. Return departure begins with the bed lowered; the maximum
remaining angle was 0.000016 radians.
The final minimum world-up component was 0.9930, confirming the return journey
does not invert the vehicle on the 8% decline. Heading uses the directed
route and a stable world-up vector; the headlights and cab face the same
forward axis. Wheels roll with distance travelled.

Exact initial-pose mesh bounds, excluding the nonphysical contact shadow,
were 7.710 m long, 2.274 m wide and 2.357 m high. They fit the configured
7.710 x 2.274 x 2.395 m envelope. This is a visual correctness check, not
a vehicle dynamics or swept-path certification.

## Transfer

Resource Timing encoded body sizes, plus the main HTML response body.
The Python static server sends these resources without gzip. Texture JPEGs
and web fonts already use compression. Response headers are not included.

| Stage | Mission assets | Target | Result |
| --- | ---: | ---: | --- |
| First interactive globe | 1.66 MiB | 3 MiB | Pass |
| Optional globe layers and mineral markers after interaction | 1.76 MiB | Reported separately | Included in total |
| Additional local surface assets | 0.29 MiB | 3 MiB | Pass |
| Additional underground assets, including excavator | 3.45 MiB | 4 MiB | Pass |
| Complete mission assets | 7.15 MiB | 10 MiB | Pass |

Pinned local libraries and fonts add 1.40 MiB, for a combined
8.55 MiB core route. Documentation screenshots are not loaded by the
application. Google loads the optional online iframe; its variable transfer
is outside these local-asset totals. No Google imagery or map screenshot is
committed as a local asset.

## Rendering samples

Performance samples refer to implementation commit `83d7004`. The final
departure correction was checked separately through the full native browser
flow and a deterministic route exercise. It adds a two-triangle tipping pad
to the existing combined floor, with no extra draw call or texture.

These short samples include scene entry and shader compilation. The primary
profile uses the native **Apple M1 Metal GPU** in headless Chromium. Mobile
emulation adds 4x CPU throttling, a 390 x 844 viewport and a device scale of 2.
It does not replace a physical-phone measurement. The WebGL pixel ratio is
capped and adapts to frame cost; HTML text stays at display resolution.

| Profile and stage | Mean fps | Draw calls | Triangles | Estimated texture MiB |
| --- | ---: | ---: | ---: | ---: |
| Desktop globe | 60 | 9 | 71,112 | 64 |
| Desktop surface | 60 | 26 | 132,197 | 8 |
| Desktop fleet | 60 | 43 | 27,750 | 13.02 |
| Desktop truck | 51.9 | 39 | 27,232 | 14.35 |
| Mobile globe | 60 | 7 | 13,864 | 10.67 |
| Mobile fleet | 60 | 43 | 27,750 | 10.35 |
| Mobile truck | 55.4 | 31 | 20,052 | 10.35 |

All primary means exceed a 30 fps target. The fleet overview uses 43 draw
calls, reduced from 187 before batching and distant-vehicle detail. The
three-second rolling frame windows include compilation pauses; the truck
means are 51.9 fps on desktop and 55.4 fps under mobile CPU emulation.

A separate SwiftShader software-rendering profile returned 3.9 to 22.6 fps
and does not meet the smoothness target. Those results are retained in
[verification-software.json](verification-software.json). They describe the
software fallback; the primary measurements above use the available native
GPU. Hardware acceleration matters for the presentation.

Texture figures estimate referenced RGBA storage including mipmaps; they
are not process-memory measurements. Departed Earth and surface stage GPU
resources are disposed. Mobile uses a 2,048 x 1,024 Earth image in GPU memory
and omits the optional night/cloud layers and mine normal maps. Desktop
uses a 4,096 x 2,048 day texture with optional night and cloud layers.

## Loading

The unthrottled first interactive globe took 0.50 s
in this native GPU run. With a cold cache, 1.6 Mbit/s download and 150 ms
latency, measured times were:

- First interactive globe: 16.52 s.
- Surface arrival after choosing Underground and skipping the flight: 7.03 s.
- Underground preparation and portal transition: 27.65 s.

The interface remains on the preceding scene while preparing the next one,
with explicit loading feedback. There are no blank loading frames or page
errors in the flow. These timings show that a cold slow connection is not
instant. For a presentation, run the local server with its local assets.

## Scope

Google satellite imagery requires internet. The local alternative is supplied
with `?offline=1`. Browser emulation does not establish physical-phone frame
rate, thermal stability, Safari compatibility or a deployment safety case.
The predictions and optimiser trace are illustrative throughout.

Raw results: [verification.json](verification.json).
