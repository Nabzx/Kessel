# ADR-0011: Webfont choice and loading strategy

Status: Accepted

## Context

The UI currently uses a system monospace stack (`ui-monospace, Menlo,
Consolas, monospace`), which is legible but generic -- it doesn't carry
any deliberate brand identity, and a YC/EWOR-facing demo benefits from
looking considered rather than default.

## Decision

Two Google Fonts, loaded via a standard `<link>` (no build step, same
delivery mechanism already used for the Three.js import map's CDN
modules):

- **JetBrains Mono** for the HUD, caption, and all body/UI text --
  replaces the system monospace stack. Open-licensed, highly legible at
  small sizes, and already reads as "engineering tool" rather than
  generic terminal font.
- **Space Grotesk** for the intro-card headlines and the Kessel wordmark
  only -- a distinct, slightly technical display face, used sparingly so
  it doesn't compete with the monospace UI for attention.

**Loading**: a `<link rel="preconnect">` to Google's font hosts plus the
stylesheet `<link>` in `<head>`, `font-display: swap` (Google Fonts'
default), and the existing system-monospace stack kept as the CSS
fallback chain so the page is never blocked on font load and never shows
invisible text.

Self-hosting was considered and rejected for now: it adds files and a
licence-tracking burden for marginal benefit on a page already pulling
Three.js from a CDN; the "runs fully offline" invariant in AGENTS.md
applies to the real product's onboard runtime, not to how this web demo's
assets are delivered over a normal internet connection.

## Consequences

Two font requests added to the page load; both are small, cached
aggressively by Google's CDN, and `font-display: swap` means there's no
flash-of-invisible-text penalty. If this demo later needs to work from a
fully offline file (e.g. opened via `file://` with no network), these
fonts would need to be vendored -- not a requirement today, noted for
future reference.
