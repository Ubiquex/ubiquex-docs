# STATE — ubiquex-docs

## UBI-19: `.ubx/config` and `ubx init` reference (2026-07-16, same session as the code)

New `cli/config.mdx` (full format reference: why TOML over YAML, discovery
walking upward from cwd with nearest-wins, precedence, the five keys in a
table, unknown-key warnings, and a `<Warning>` about the real TOML
ordering gotcha this session's own `ubx init` implementation hit first —
root-level keys written after a `[table]` header silently get absorbed
into that table) and `cli/init.mdx` (both generation modes: fully
commented template, and real-values-for-given-flags). `cli/scan.mdx` and
`cli/status.mdx` each gained a short daily-command-form example, real
transcripts, demonstrating what `.ubx/config` actually buys a reader —
`status.mdx` also documents the one deliberate precedence exception
(config's `stack` default doesn't apply to `--stack`'s filter semantics
there). `cli/writeback.mdx`, `cli/revert-plan.mdx`, `cli/accept.mdx`, and
`cli/why.mdx` each gained a brief config-fallback note for their own
relevant key, plus a cross-link. `getting-started/installation.mdx` now
points to `ubx init` as the natural first step after install. `mint
validate`, `mint dev`, and `mint broken-links` all pass clean.

## UBI-18: bulk onboarding docs, and the carried UBI-16 debt cleared (2026-07-16, same session as the code)

New `cli/revert-plan.mdx` — this is the carried-over UBI-16 debt (below),
cleared: full reference, real transcripts, including a mixed
literal/declined `--tf-dir` case. `concepts/drift.mdx` gained a "Two
resolutions to a drift: adopt, or revert" section, since `drift_revert`
had shipped (UBI-16) with no conceptual explanation anywhere — the other
half of that carried debt.

Discovered while updating `cli/scan.mdx` for this session's own
`--all`/`--tfstate`/`--out-dir` flags: **`--propose` (UBI-16) was never
added to this page at all** — it shipped entirely under the old
docs-debt protocol, and the debt entry only ever mentioned the missing
`revert-plan` page, not the missing flag on an already-published page.
Added alongside `--all`'s own documentation: the flag table entry, a
"Generating a revert proposal instead of (or alongside) adopt" example
section, and a "Bulk onboarding (`--all`)" section covering stack
inference, `count`/`for_each` and module-path addressing (including why a
module path gets folded into the resource's own address, not just noted
in prose — two different modules can declare a same-type, same-name
resource), and the skipped-summary. New `guides/onboarding.mdx`: the full
`--all` walkthrough, every transcript real — adopt, accept each in
sequence, `ubx status` (ledger-only, then `--drift`, clean), plus a
messier real-world skipped-resources example. `mint validate`, `mint
dev`, and `mint broken-links` all pass clean.

**Lesson for next time a docs-debt entry gets written**: name every file
*and* every already-published page a change touches, not just the new
ones — a debt entry that only lists "no reference page for X" can miss
"page Y already exists and is now stale," which is exactly what happened
here.

## Protocol change (2026-07-16): docs land same-session now

ubiquex-cli's CLAUDE.md session protocol changed: user-visible changes now
update ubiquex-docs in the *same* session (verified against the built
binary, `mint validate` clean, committed and pushed), not batched as a
"docs debt" STATE.md entry for a later session — that was the prior
convention (see UBI-13 below, which existed specifically to work through
that backlog). A docs-debt entry is now the documented exception for when
same-session isn't feasible, not the default path.

## UBI-17: `ubx status` reference (2026-07-16, same session as the code)

New `cli/status.mdx`: both modes (ledger-only vs. `--drift`) documented as
genuinely different capabilities, not one capability with a default; every
example transcript real, captured from the actual built binary (including
a hand-crafted "no lookup recorded" proposal to demonstrate the
`unreadable` classification honestly). The exit-code CI contract (0/1/2)
gets its own table plus a worked `bash`/`case` example, since that's the
single most operationally important fact about this command.
`concepts/ledger.mdx`'s "Stacks are independent" section gained a
clarification that this is conceptual, not physical — one ledger directory
can hold several stacks' proposals interleaved in one chain, which is
exactly what `ubx status`'s "every resource, every stack, by default"
report depends on (a confirmed finding from this session's ubiquex-cli
work, not assumed). `mint validate`, `mint dev`, and `mint broken-links`
all pass clean.

~~**Still open, carried over from ubiquex-cli's own STATE.md (UBI-16, prior
session, predates the protocol change above)**: `ubx revert-plan` has no
CLI reference page yet, and the "one ledger directory can span multiple
stacks" note above was written for UBI-17 specifically — a
`concepts/revert.mdx` (or an addition to `concepts/drift.mdx`) explaining
`drift_revert`'s corrective-direction semantics still doesn't exist. Pick
up next.~~ **Cleared in the UBI-18 session above** (`cli/revert-plan.mdx`,
`concepts/drift.mdx`'s new section) — along with a related gap that debt
entry itself hadn't named: `cli/scan.mdx`'s own `--propose` flag, missing
since UBI-16.

## Release cut v0.1.0 (2026-07-11)

ubiquex-cli's release infrastructure (goreleaser + a tag-triggered GitHub
Actions workflow) landed this session — see that repo's STATE.md for the
mechanics. On this side:

- `getting-started/installation.mdx` replaced the source-only placeholder
  with real instructions: `gh release download` (the repo is currently
  private, so plain `curl` won't authenticate), checksum verification
  against the published `checksums.txt`, `chmod`, and `PATH` setup. Labeled
  honestly as pre-alpha — a release existing doesn't mean API/schema
  stability. Build-from-source is kept as an explicit alternative.
- `cli/version.mdx` updated for the new `<version>+<commit>` output format
  (previously always bare `dev`) — both real examples (a release-tag build,
  a plain local `go build`) verified against the actual binary this
  session, along with the two different sources of the commit suffix
  (ldflags vs. Go's own VCS build stamping).
- Note: these pages reference `v0.1.0` as already published to GitHub
  Releases. As of this commit, the tag has *not* been pushed yet — that's
  Roozbeh's manual act, after reviewing this session's goreleaser
  dry-run output. The docs describe the release process that will exist
  once he does, not a claim that it exists yet at commit time.
- `mint validate`, `mint dev`, and `mint broken-links` all pass clean.

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

None open. The UBI-16 carry-over (`ubx revert-plan` reference page,
`drift_revert` concepts explanation) was cleared in the UBI-18 session
above. Per the new protocol (see top of this file), this section should
stay empty except for genuine, explicitly-noted exceptions going forward.

Historical: every item tracked in ubiquex-cli's STATE.md docs-debt section
as of UBI-13's start was addressed by that milestone; see that file's own
UBI-13 entry for the full list it closed out.

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
