# Repository-only acceptance review

Serve the repository with the existing loopback static server and open this folder.
The review uses retained captures; only its own storyboard clock runs when Play
is selected. Pausing, changing routes or hiding the page cancels that clock.

The main and technical sequences total 60 and 90 seconds. These are planned
story timings, not newly measured recordings. Captions preserve the distinction
between authored illustration and actual synthetic experiment outcomes.

The earlier/current frames share a 16:10 composition and are displayed at matched
sizes. Different source resolutions are disclosed. The old native video is
retained as historical footage rather than presented as a new capture.

The bounded headless runners are:

    node scripts/research/review-focus.cjs
    node scripts/research/verify-review-page.cjs

They have 45- and 30-second caps and never open visible windows. Contrast output
and focus/interaction evidence are in evidence/. The interrupted native-tab check
is not counted as acceptance. No visible-browser runner is retained.

[Local candidate notes](../release-candidate.md) describe the archive and the
remaining visual/manual approval. No publication is performed.
