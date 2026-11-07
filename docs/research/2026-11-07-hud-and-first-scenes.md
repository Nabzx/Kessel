# HUD and first-scene visual follow-up

7 November 2026. #297–#303. Requested after the mine-entry report.

## Layout and HUD

The [USWDS typography guidance](https://designsystem.digital.gov/components/typography/)
and [data-visualisation guidance](https://designsystem.digital.gov/components/data-visualizations/)
inform readable type, consistent units, compact legends and accessible data
presentation. Use those principles within Kessel's existing identity. Do not
import a component framework or imply that a technical appearance validates
an experiment.

The current mine labels were mostly 8–9 px, and the learning view put forecast
instruments over the left part of the 3D task. #297 increases label/value
sizes and groups the instruments in one right rail. Policy and world-model
tabs reveal the same existing data; they do not seek, train or alter a model.
Playback controls and actual outcome text stay visible. The raw forecast and
its physical-violation warning remain explicit.

## Home and environment tickets

The maintainer's [Blackshark](https://www.blackshark.ai/) and
[CesiumJS](https://cesium.com/platform/cesiumjs/) references support a restrained
geospatial direction: realistic terrain/globe imagery, a clear selected
location and a continuous camera journey. Their appearance does not clear
website imagery or software integration for reuse.

- #298: photographic Earth lighting, cloud/terminator balance and atmosphere.
- #299: globe-led orbital composition, satellite finishes and sparse stars.
- #300: deliberate home arrival and responsive start hand-off.
- #301: locally served photographic previews with per-image clearance.
- #302: geographically anchored markers and a clearer carousel hierarchy.
- #303: themed surroundings and interruption-safe camera continuity.

Keep the existing cleared NASA Earth layers and unmarked NASA/VTAD ISS model
as the initial asset base. [NASA media guidance](https://www.nasa.gov/nasa-brand-center/images-and-media/)
and the [Earth imagery FAQ](https://science.nasa.gov/earth/faq/) require attention
to individual credits and third-party notices. No additional NASA image is
approved solely from a NASA-hosted preview.

[NOAA's FAQ](https://oceanexplorer.noaa.gov/faqs/) and
[media guidance](https://oceanexplorer.noaa.gov/about/media-kit/) identify its
ocean-exploration collection as a candidate for deep-sea imagery, subject to
the original caption and any copyright exception. [Poly Haven](https://polyhaven.com/license)
is the CC0 alternative for environment material studies. #301 requires
individual source records, credits and derivative hashes before importing
new previews. No new external imagery is bundled by the HUD work.

#298–#303 are queued work items with explicit acceptance criteria. #297 is the
implemented layout follow-up. All seven are native sub-issues of #197.
