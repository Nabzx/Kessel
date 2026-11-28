# ADR-0085: Literal packaging fixture audit erratum

Status: Accepted audit-only correction to ADR-0084. Candidate, weights, cohorts,
screening predicates and all task/forecast thresholds remain frozen.

The complete first audit inspected 8,899 unique containers/raw/member blobs in
216.63 worker seconds, with no seed or initial-state/pile fingerprint matches.
It rejected one non-JSON packaging fixture under ignored pytest scratch. Its
entire content is the 17-byte literal `data/example.json`, created by
`training/tests/test_static_package.py` writing each test filename as its payload.
This is not research evidence, an undecodable numerical checkpoint or a case.

Preserve the first rejected certificate byte-for-byte as reservation-attempt-1.
Derive a corrected certificate only if this exact single error is present, its
raw hash appears in the original completed inventory, the retained literal bytes
match the source test and all original hits are empty. No blanket scratch-path
exception and no new seed screening are permitted. Preserve original errors and
the original certificate hash alongside the explicit literal-fixture disposition.
Pin this correction driver, protocol and test source in audit_files. Any other
error or changed content blocks correction.

The correction makes zero policy/physics queries. Cap it at ten seconds, with
at most 250 seconds combined original parent audit and correction time. The
original 240-second attempt remains reported separately. Do not erase its failed
status or claim the uncorrected audit passed. Fresh execution uses the derived
certificate and unchanged frozen qualification implementation.
