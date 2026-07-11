# STATE — ubiquex-docs

## Current slice

UBI-13, Session 2: per-verb CLI reference pages. Done.

- `cli/version.mdx`, `cli/scan.mdx`, `cli/accept.mdx`, `cli/propose.mdx`,
  `cli/why.mdx`, `cli/writeback.mdx` — full flag tables (every flag copied
  from the actual built binary's `--help` output, not from memory or
  plan.md) and at least one real, verified example per command:
  - `scan`: new / drifted / unchanged outcomes, plus `--surface-as issue`
    and `--surface-as pr`, including the issue-write vs. contents/PR-write
    permission distinction between the two modes.
  - `accept`: local acceptance, `--reverify-with` (both the pass-when-fresh
    and blocked-when-stale cases), and `--from-merge` PR-merge acceptance.
  - `why`: proposal-ID lookup, resource-address chain lookup, and
    `--verify-acceptance`.
  - `writeback`: default diff preview, `--write`, and a declined-attribute
    case (a `.tf` value that's an expression, not a literal).
  - `propose`: computing a trailer hash from a draft proposal file.
  - `version`: honest note that a source build always prints `dev` absent
    `-ldflags`, since no release process exists yet.
- `cli/lookup.mdx` (new page, added to `docs.json`'s CLI Reference group):
  the per-type resource lookup table, sourced from
  `ubiquex-cli/conformance/registry.go`. Distinguishes the seven AWS types
  with a lookup shape verified live against the real AWS provider
  (`aws_s3_bucket`, `aws_iam_role`, `aws_iam_user`, `aws_iam_policy`,
  `aws_sqs_queue`, `aws_sns_topic`, `aws_vpc`) from the ~40 remaining types
  that default to `{"id": "..."}`, verified only against each type's
  schema and a fixture, not against a real provider's live `ReadResource`
  call. Deliberately excludes registry entries with no `Implemented: true`
  (e.g. `aws_iam_group`'s adopt-path note) since those aren't backed by an
  actual conformance test, however plausible the comment reads.
- Every example transcript in this session's pages (proposal JSON, scan/
  accept/why/writeback output, GitHub issue/PR body content) was captured
  from a real, running `ubx` binary and — for `--from-merge`/
  `--verify-acceptance`/`--surface-as`, which need a GitHub API — a
  throwaway local HTTP server serving fixture responses on the same
  endpoints `cli/accept_frommerge_test.go` and `cli/surface_test.go` use.
  Nothing in these pages is hand-typed/fabricated output.
- Validated: `mint validate`, `mint dev` (smoke-tested every new/changed
  route), and `mint broken-links` all pass clean.

## Docs debt (ubiquex-docs)

Open, for subsequent UBI-13 sessions:

- A `guides/` section still doesn't exist. The PR-merge acceptance
  workflow (trailer convention, zero-approvers-is-normal, the whole
  propose→PR→merge→accept flow, now that `cli/accept.mdx` and
  `cli/propose.mdx` cover the mechanics) probably still deserves a
  dedicated walkthrough page, not just flag reference — carried forward
  from Session 1, not yet started.
- `--source`/`--provider-version` (registry provider acquisition, UBI-8)
  are named in `cli/scan.mdx`/`cli/accept.mdx`'s flag tables but have no
  worked example — every example this session used `--provider` with a
  local binary. A registry-acquisition example needs either a real
  registry round trip or a documented reason to skip one.
- No page yet explains `.ubx/ledger.lock`/concurrent-access behavior in
  CLI-reference depth (only `concepts/ledger.mdx`'s brief mention).

## Next steps

Pick up the `guides/` PR-merge-acceptance walkthrough, or the registry
acquisition example gap, next — whichever ubiquex-cli's own STATE.md
docs-debt entry prioritizes.
