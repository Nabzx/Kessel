## What this does

One or two sentences. Reference the issue in the body: `refs #<n>`.

## Why

The reason, or a pointer to the ADR or map that called for it.

## Checklist

- [ ] Title and commits follow Conventional Commits; `refs #<n>`, not `closes #<n>`
- [ ] Advances a labelled issue
- [ ] An ADR covers anything touching the rollout data schema, the panel
      split, the renderer's public shape, or the hosting/publish mechanism
- [ ] Checked in a real browser, not just "no console errors"
- [ ] Checked on a narrow viewport (mobile layout), if UI changed
- [ ] The permanent caption and illustrative HUD labelling are still intact,
      if `index.html` or `js/app.js` changed
- [ ] Commits are small, British English, no co-author trailer
- [ ] Docs updated (`CONTEXT.md`, `ROADMAP.md`, `docs/adr/`) if behaviour or a
      decision changed
