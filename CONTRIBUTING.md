# Contributing

This is a private repository with a single maintainer, Nabil Shah. It is not
open to external contributions — there is no public audience to open issues
or pull requests yet. This file exists so the process is explicit for anyone
with repo access (an engineering agent included), not as an invitation.

## How work happens here

Work is tracked as GitHub issues, following the Wayfinder structure in
[`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md) and the phases
in [`ROADMAP.md`](ROADMAP.md). Every change lands through a pull request with
green CI, even though there is one author.

## Commits and pull requests

- Conventional Commits: `<type>(<scope>): <description>`, lowercase,
  imperative. See `AGENTS.md` for the full house style.
- Reference the issue with `refs #<n>` in the body, never a closing keyword.
  A build issue carries `pending-release` and closes in a batch when tagged.
- No co-author trailer on any commit, including AI tool attribution.
- Small, reviewable commits over one large one. A sequence of commits that
  tells the story of how a feature was built is preferred to a single squash.

## Dependabot

Dependabot is the maintainer's own dependency-update tooling, configured in
`.github/dependabot.yml`. Each Dependabot pull request is reviewed and
re-landed under the maintainer's own commit, so the history stays
single-author; it is not left open as a queue.
