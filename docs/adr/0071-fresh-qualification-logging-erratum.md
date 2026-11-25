# ADR-0071: Fresh qualification logging correction and replacement base

Status: Accepted for the maintainer's continued work on 25 November 2026.
Preserves ADR-0070's frozen controller, families, per-seed gates and physics.

The first execution stops before retaining the first healthy case because a
local source-hash variable shadows the identity function. Available plan, source,
empty archive and error/cost bounds are retained under the qualification evidence's
`aborted-attempt/`. No outcome table or replay exists. At most 600 environment
decisions and 600 neural queries occurred; exact counts and trajectory are lost.
An archive timestamp span is not monotonic active-time measurement.

Base 208700 has been queried and is consumed for every derived family/source.
Never rerun or count it as fresh. Retain the original successful reservation
certificate unchanged. Audit replacement 208708 against the same full available
history/raw/ZIP scope before any query. Reject on a hit, unreadable input or
timeout. The untouched 208701–208707 retain the original certificate; combine
their identities with the verified replacement, binding both certificates and
the consumed-base exclusion. Do not infer freshness from a text search.

The corrected qualification cohort is exactly 208701–208708. Correct the logger
by giving the source-hash value a distinct name and isolating identity creation
in a tested helper. Add a bounded practice-only journal regression test before
any fresh restart. No control parameter, weight, action rule or gate changes.

Use one serial CPU and the existing 180-second replacement-audit cap. Restart
qualification once in a distinct output directory with 120 cases and unchanged
replay coverage. Reduce evaluation cap to 71,400, leaving 600 decisions for the
aborted attempt within the former 72,000 allowance. Reduce active cap to 400
seconds; replay and archive caps stay unchanged. Preserve both attempts and all
costs. Another exception, cap or failed gate ends this study without admission;
do not retune, replace more cases or rerun after its results.

This is a logging correction with an explicitly audited replacement, not a
retest of consumed held-out data. All remaining boundaries in ADR-0070 apply.
