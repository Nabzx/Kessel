# Security policy

## Reporting a vulnerability

Do not open a public issue for a security problem.

Use GitHub's private vulnerability reporting on this repository (Security
tab, "Report a vulnerability"), or email the maintainer at
nabilshahx@gmail.com with "Kessel security" in the subject.

You should get an acknowledgement within a few days.

## Scope

This repository is a static, client-side visualisation with no backend, no
authentication, and no user data. In scope: anything that would let a visitor
to the published demo execute unintended code in another visitor's browser,
or that would let a compromised dependency (see `.github/dependabot.yml`)
inject code into the published site.

Out of scope: the public mirror repository's GitHub Pages hosting
infrastructure itself (that is GitHub's), and anything requiring write access
to this private repository, which is already access-controlled.
