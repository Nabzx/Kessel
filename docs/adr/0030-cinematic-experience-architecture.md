# ADR-0030: Cinematic experience architecture

Status: Accepted

Supersedes the Phase 9 presentation and phone-first requirement for this phase.
The maintainer explicitly targets a MacBook Pro M1 running Chrome.

## Decision

Use one persistent renderer and camera, with owned globe, surface, cutaway,
training and proposed-kit roots. The controller owns welcome, selection,
approach, surface, cutaway, comparison-transition, trained and world-model
states. Main mine views remain overhead. No chase camera or manual machine
override is included. Button-led scenes release into ordinary vertical page
scrolling after the trained-site comparison.

The optional world-model view preserves its entry context, comparison state
and page scroll position. Entering it freezes the mine clock; exiting restores
the scene. Only the current/next stage loads eagerly. The kit loads when its
section approaches the viewport. Cancel stale transitions and release scene
resources on replay. Visibility changes pause animation; reduced motion shortens
camera moves. Plain HTML, CSS and ES modules remain the shipping format.

Authored scene content is in data/experience.json: locations, themes, stage
poses, cutaway rock mass, routes, operating assumptions, training checkpoints,
model dimensions and kit components. Data swaps do not require scene-content
changes to rendering code. Keep the existing Phase 9 dataset for provenance.

The main guided route is approximately 60 seconds including normal viewing
pauses; viewers advance through buttons. Optional training exploration and the
product page are outside that timing. There is no pricing section.

Native M1 target: 60 fps, with a minimum acceptance mean of 30 fps and disclosed
frame-time tails at representative laptop/Retina viewports. Record software
rendering separately. Preserve the permanent concept label and source credits.
