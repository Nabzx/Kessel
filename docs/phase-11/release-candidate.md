# Local walkthrough candidate

22 November 2026. Refs #274, #351, #385 and #276.

The current work is restricted to repository changes and bounded headless checks.
No remote release, tag, deployment or new visible browser automation is authorised
by this candidate. Human visual acceptance remains open.

## What changed

The entry control could take keyboard focus while its entrance animation kept
it invisible. Reduced motion also left the decorative entrance animation active.
The CSS now shows a focused entry control immediately and removes entrance
animation for reduced motion. Presentation cache version is 2026-11-22.02.

A single headless check covers visible keyboard focus, bounded tab traversal,
dialog return focus and the entry control in normal/reduced motion. The text
contrast audit covers the three target desktop sizes. It checks computed
foreground/panel colours and classifies scene-backed text separately, following
the [W3C contrast thresholds](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum).
It is not a full accessibility certification or maintainer visual judgement.

The previous continuation's entry point remains preserved byte-for-byte in its
evidence capsule. Numerical experiments, controller weights and forecast results
are unchanged.

## Review

Open [the review page](acceptance-review/index.html) from the existing local
repository server. It provides:

- A 60-second main-story storyboard and a 90-second technical storyboard.
- Explicit labels for authored illustration, conventional reference, historical
  failed learning, raw forecasts and nominal imitation results.
- Matched-size earlier/current comparisons and links to retained native footage.
- The new keyboard-focus capture, complete stress results and model limitations.

These are timed still storyboards using retained captures. They are not new
live walkthrough recordings. The old native clip is explicitly dated.

## Static candidate

The ignored repo-local candidate is
.local/release-candidate/kessel-static-candidate.zip. Its 144 source files are
checked against the embedded release manifest. It is 18,769,734 bytes and refers
to source commit 4479de9a863ebb98c26f23b088d31f9113819987. Later changes concern
only the separate review page, its checks and documentation, not the packaged
main experience.

To create another local candidate after committing static source changes:

    python3 scripts/prepare-release-candidate.py --output .local/another-candidate

The tool only writes beneath this repository's ignored .local directory. It
refuses existing output directories, dirty static inputs and candidates above
64 MiB uncompressed. Packaging has a 30-second cap. It never invokes a hosting
service or a release command. The existing static allowlist excludes training
environments, weights and raw research archives.

## Still open

The attempted native-tab interaction check did not complete and cannot certify
background/foreground behaviour. It was stopped after disrupting the maintainer's
other work. The dedicated visible-browser scripts have been removed.

The underlying browser-visibility probe worked, but that is not a completed
application-level test. Do not replace this missing acceptance with the earlier
synthetic visibility check or rerun visible automation without a new instruction.

#274 retains that manual check. #351/#385 retain the maintainer's visual judgement;
#276 retains release approval. This candidate supplies reviewable work while
honouring those limits.
