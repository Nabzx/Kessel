# Phase 10 visual review

The maintainer reviewed the working localhost experience and approved its
direction, requesting three refinements: upright Earth imagery, correct
geographic labels and a smoother trained-site transition. The final pass fixes
the bitmap orientation and replaces the wireframe switch with a travelling
scan, eased route/machine opacity and a soft metrics hand-off.

The approved storyboard was built as the working clickable prototype, then
refined in place. No separate throwaway prototype was released. The
[60-second timing sheet](presenter-guide.md) and the actual captures below
cover its main route and optional branch.

## Captured frames

| Scene | Capture |
| --- | --- |
| Centred Earth, custom wordmark, start | [Welcome](frames/welcome.jpg) |
| Themed left carousel and fixed markers | [Glacier](frames/glacier.jpg), [desert](frames/desert.jpg), [space](frames/space.jpg), [underground](frames/underground.jpg), [deep sea](frames/deep-sea.jpg) |
| Continuous geographic camera journey | [Descent](frames/descent.jpg), [surface](frames/surface.jpg) |
| Substantial tilted rock mass, five machines | [Baseline](frames/baseline.jpg) |
| Technical policy hand-off | [Scan transition](frames/transition.jpg) |
| Green haul loops and all six measures | [Trained site](frames/trained.jpg) |
| Optional technical viewer | [Learning](frames/learning.jpg) |
| Failure, improvement, successful haul | [Early](frames/checkpoint-0.jpg), [learning](frames/checkpoint-1.jpg), [trained](frames/checkpoint-2.jpg), [delivery](frames/delivered.jpg) |
| Normal scrolling, dynamics/RL/distillation/control | [Product](frames/product.jpg) |
| Proposed retrofit | [Exploded](frames/kit.jpg), [assembled](frames/assembled.jpg) |
| Smaller laptop layout | [1280 x 800](frames/laptop-1280.jpg) |

## Review against the brief

The Earth, rather than a marketing paragraph, opens the site. Earth and its
atmosphere use real imagery; markers rotate with geography. Environment colour
changes affect the surrounding lighting/background as well as the left panel.
Only underground deploys. The same canvas carries the approach and cutaway.

The mine stays overhead, with four correctly directed trucks and the licensed
excavator. Red baseline traffic queues; green routes split into two circuits.
The right panel presents six related operating measures. Connectivity remains
weak in both scenarios. Manual override, truck chase views and pricing are
absent from the current interface.

The technical view shows an original loader, observation samples, predicted
poses, parallel rollout silhouettes, action state, reward and checkpoints.
Its represented counter, results and figures are labelled illustrative. The
world model predicts dynamics; RL improves the policy; distillation produces
a compact policy; onboard sensing/control runs offline. Deployment feedback
returns when connected. The hardware is explicitly a proposed assembly.

Black, off-white and mineral amber are consistent across the experience.
Red/green communicate baseline/trained state. Copy is short and British
English. The permanent concept caption and asset credits remain visible.

## References

[Blackshark](https://www.blackshark.ai/) informed the restrained geographic
presentation. [CesiumJS](https://cesium.com/platform/cesiumjs/) informed the
continuous world-to-site camera story. The implementation does not claim their
photogrammetric coverage or use their proprietary data. The delivery uses
public regional imagery and authored mine foreground, as recorded in ADR-0028.
