# Static hosting handover

The repository ships a plain static presentation. No build step, backend,
training process or numerical service is required by the published main route.
The existing static allowlist is `scripts/package-static.py`: index, licence,
CSS, JavaScript, authored JSON and presentation assets including vendored modules.
It excludes training code, weights, raw studies, `.local` and repository metadata.

## Reviewable candidate

Commit static inputs before packaging. Create a fresh repo-local candidate:

    python3 scripts/prepare-release-candidate.py --output .local/current-static-candidate

The tool checks every archive member against its manifest, pins the source
commit, refuses dirty static inputs and preserves the 64 MiB/30-second caps.
`candidate.json` adds the archive hash and file count. Packaging does not upload,
tag, create a remote repository or change hosting settings.

As checked on 27 November, `Nabzx/Kessel` has no Pages configuration visible to
the current credentials. `Nabzx/kessel-demo` does not resolve to an accessible
repository. There is no verified public deployment URL. Do not present a planned
mirror URL as live or assume an inaccessible repository is absent.

## Publication procedure after acceptance

Use a dedicated public static mirror only after its owner, visibility and target
are confirmed. Copy the verified archive's presentation files to its publishing
branch, preserving all source labels, credits and licences. Keep its source
manifest with the deployment. Set Pages to that branch/root and HTTPS. The
relative asset paths and import map support a repository subpath.

For the first accepted candidate:

1. Confirm the owner/name and create or select the public mirror. Clone it into
   a new ignored `.local/public-mirror` directory. Do not reuse another checkout
   or push the source repository into it.
2. Extract only the verified static archive into that mirror root. Review its
   manifest and `git status` for presentation files, credits and licence. There
   should be no training code, raw research, credentials or source docs.
3. Commit the candidate with its source commit in the message and push the
   publishing branch. For updates, review removed files too, to avoid stale assets.
4. In the mirror's Settings, select Pages, then Deploy from a branch. Choose the
   actual publishing branch and `/(root)`, then Save. GitHub's
   [publishing-source instructions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
   cover these settings and the deployment run.
5. Wait for successful deployment and use the URL shown by Pages. Complete the
   checks below before sharing it or closing the hosting ticket.

Automatic mirror synchronisation is not configured by this work. Regenerate,
verify and publish subsequent accepted candidates through this same procedure.
Preserve the preceding verified candidate for rollback.

Check the actual published URL after deployment: main route, cold/cached assets,
source switching, replay, failed-asset retry, keyboard focus and reduced motion.
Capture response headers, source commit and deployment identity. For rollback,
restore the previous verified static artifact and redeploy; do not rebuild
numerical evidence or silently replace source labels.

No publication has occurred in this work. The maintainer's earlier instruction
keeps visual reviews #351/#385 open. #274 still needs deliberate manual browser
checks; #276 needs real complete capture and acceptance. Those criteria cannot
be supplied by uploading an archive. The candidate is ready for that review.
