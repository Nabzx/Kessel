# ADR-0017: Adopt a CC-BY loader model, credited in the README

Status: Accepted

## Context

No clean CC0 LHD-specific loader model exists (#121). The realistic
options found in research are CC-BY: usable, but requiring attribution,
in a repo whose house style has otherwise avoided any external
attribution (no Claude/AI credit, no third-party code copied in).

The maintainer has also decided to go photoreal across the board (#124's
parent decision), including the loader itself, rather than keeping a
stylised primitive rig next to photoreal rocks and textures -- a
primitive-built loader would read as visibly out of place once the
ground and rock pile are real geology.

## Decision

Adopt a CC-BY loader model and credit it in the README. A model credit
is a normal, expected part of using CC-BY assets -- it's not the same
category of thing as AI/tool attribution, which this repo avoids for
different reasons (keeping the commit history and authorship honest to
who actually made the decisions). A one-line credit costs nothing and
unblocks the realism goal everywhere the loader appears.

## Consequences

#124 proceeds as "adopt" rather than "keep the primitive rig": the
primitive boom/bucket/wheel rig's animation points need to carry over
onto the new model's bones/pivots. The README gains a short credits
section naming the model and its licence once a specific asset is
chosen and integrated.
