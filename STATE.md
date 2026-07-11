# STATE — ubiquex-docs

## UBI-13: closed out (2026-07-11)

Three sessions, scaffold through full reference:

- **Session 1** — `docs.json` navigation, landing page, honest
  build-from-source install placeholder, five concept pages
  (proposal/ledger/drift/attribution/why), and skeleton `cli/` pages for
  all six verbs.
- **Session 2** — full flag tables (every flag copied from the built
  binary's own `--help` output) and verified examples for all six verbs,
  plus `cli/lookup.mdx`, the per-type resource lookup table sourced from
  `ubiquex-cli/conformance/registry.go`.
- **Session 3** — `guides/pr-merge-acceptance.mdx`, a full draft-to-accept
  walkthrough (including a real zero-approvers-accepted transcript backing
  up "not a review-policy gate"), and a real `--source`/`--provider-version`
  (and `--reverify-source`/`--reverify-provider-version`) worked example in
  `cli/scan.mdx`/`cli/accept.mdx` via `UBX_PROVIDER_MIRROR`, which also
  surfaced a previously-undocumented field: `resolution.inputs[].provider_checksum`,
  present only when a provider was acquired by source+version rather than
  pointed at directly with `--provider`.

Every example transcript across all three sessions was captured from a
real, running `ubx` binary (plus `fakeprovider` for resource state, and a
throwaway fixture GitHub API server for anything touching PR-merge
acceptance or drift-surfacing) — nothing hand-typed or fabricated.
`mint validate`, `mint dev`, and `mint broken-links` all pass clean as of
the last commit.

## Docs debt (ubiquex-docs)

None open. Every item tracked in ubiquex-cli's STATE.md docs-debt section
as of UBI-13's start is now addressed; see that file's own UBI-13 entry
for the full list this closed out.

## Possible future improvements (not debt — no user-visible change is
waiting on these)

- No page goes into `.ubx/ledger.lock`/concurrent-access behavior at
  CLI-reference depth — only `concepts/ledger.mdx`'s brief mention exists.
  Worth a paragraph somewhere if it ever becomes a real support question,
  but nothing shipped this session makes it more or less true than before.

## Next steps

No open UBI-13 work. Next docs session starts from whatever new
user-visible change lands in ubiquex-cli next and gets logged as debt
there.
