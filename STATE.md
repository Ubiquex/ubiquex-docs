# STATE — ubiquex-docs

## UBI-22: Kubernetes and Helm support (2026-07-17, same session as the code)

`ubiquex-cli`'s first non-cloud-provider provider, both stages:

- **`getting-started/installation.mdx`** now mentions
  `--source hashicorp/kubernetes`/`hashicorp/helm` alongside AWS/GCP, and
  a working `kubectl` context (`~/.kube/config` +
  `--provider-config '{"config_path":...,"config_context":...}'`) as the
  credential mechanism for a cluster.
- **`cli/lookup.mdx`** gained a "Kubernetes and Helm" section: five
  live-verified `kubernetes_*` kinds all confirmed to need only
  `{"id": "<namespace>/<name>"}` (or the bare name for cluster-scoped
  types) — a real, live correction to the Stage-1 hermetic guess that
  `metadata`'s own `NestingList` schema shape would require pre-populating
  it in `--lookup`. `helm_release` is the reverse case: `id` alone is
  NOT enough, confirmed live -- `id`+`name`+`namespace` together are
  required.
- **`cli/scan.mdx`** gained a "Kubernetes and Helm" section: a real
  `kubernetes_secret_v1` adopt+rotate+drift transcript (redaction
  confirmed end to end against a real cluster), and a real
  `helm_release` values-drift transcript showing `metadata[0].values` is
  the field that actually carries the signal (not the top-level
  `values`/`chart`, which stay `null`) — with a `Warning` that neither
  `metadata[0].values` nor `manifest` is `Sensitive`-flagged, so a
  `set_sensitive` value can still surface there in plaintext.
- **`cli/config.mdx`** gained a `[k8s_audit]` subsection — the one config
  table with no CLI flag equivalent, entirely optional, degrading to
  `audit_unattributed`/`not_configured` when absent.
- **`concepts/attribution.mdx`**'s reason table gained `not_configured`
  (a fourth value, `k8s_audit_logs`-specific), and a new "Kubernetes and
  Helm: EKS audit logs" section states the `not_configured` stance
  honestly, including a `Warning` that the EKS audit-log leg itself
  wasn't live-verified this session (no EKS cluster was provisioned —
  real, hourly-billed infrastructure judged out of proportion to create
  autonomously, unlike the free/local `kind` cluster used for
  `kubernetes_*`/`helm_release` resource-scanning verification itself).
- **`concepts/secrets.mdx`** gained a cross-reference: `hashicorp/kubernetes`/
  `hashicorp/helm` added to the "schemas checked directly" list,
  `kubernetes_secret_v1` end-to-end confirmation, and `helm_release`'s
  `set_sensitive` as the first real Set-nested sensitive value found in
  any currently-integrated provider.

Every new/changed transcript came from the actual built `ubx` binary run
against a real, local `kind` cluster during Stage 2 (not hand-written) —
captured once, reused across pages rather than re-run per page.
`mint validate`/`mint broken-links` both pass clean. See `ubiquex-cli`'s
own STATE.md for the full engineering writeup, including every empirical
finding (the `NestingList` metadata/spec shape, the `_v1`-vs-bare-name
duplication, the `helm_release` reversed lookup requirement, the
Set-nested `set_sensitive` redaction confirmation, and the deliberate
decision not to provision a real EKS cluster this session).

## UBI-23: secrets -- redaction of Sensitive attributes (2026-07-17, same session as the code)

`ubiquex-cli`'s "secrets must never enter the ledger" work:

- **New `concepts/secrets.mdx`** (added to nav, Concepts group, right
  after `concepts/attribution`): the full mental model — what gets
  redacted and when, a worked adoption→drift transcript with real
  `$redacted` JSON, the per-ledger `.ubx/salt` (generation, `.gitignore`
  safety net, the honest "losing it degrades equality comparison, never
  leaks material or hides a change" recovery framing), why
  `writeback`/`revert-plan` always decline a redacted attribute, the bulk
  onboarding redaction count, and two explicitly out-of-scope items
  (`--lookup` is never redacted; a future v6-only-`NestedType` provider
  gap).
- **`cli/scan.mdx`** gained a new "Sensitive-flagged attribute is
  redacted" example and a redaction-count bullet under bulk onboarding,
  both cross-linking to `concepts/secrets`.
- **`cli/writeback.mdx`** and **`cli/revert-plan.mdx`** each gained a
  redacted-attribute example (a real transcript: `writeback` declining
  with the exact reason text, `revert-plan`'s plan line rendering
  `(redacted)` on both sides).
- **`cli/why.mdx`** gained a redacted-attribute example, plus two
  **pre-existing examples corrected**: `why`'s human rendering gained a
  new `change: <addr>: <path>: <before> -> <after>` line this session
  (not redaction-specific — it applies to any proposal with a real delta)
  that the previously-committed transcripts didn't show, since they
  predate the change. Re-ran both against the actual built binary rather
  than hand-patching the text.
- **`cli/lookup.mdx`** gained a short section explaining why `--lookup`
  itself is safe to leave unredacted (real schemas never flag an
  identity/lookup attribute `Sensitive`).
- **`cli/scan.mdx`**'s two `scan --all` example transcripts had their
  summary lines corrected too (`N adopted, N skipped` →
  `N adopted, N skipped, N attribute(s) redacted`) — same "the binary's
  output genuinely changed, so the doc's transcript would otherwise be
  lying" reasoning as the `why` fix above.

Every new/changed transcript was regenerated against the actual built
`ubx` binary (a real `fakeprovider` fixture run with the new
`FAKEPROVIDER_SENSITIVE_ATTRS` env var, per `ubiquex-cli`'s own doc
comment) — none hand-written. `mint validate`/`mint broken-links` both
pass clean. See `ubiquex-cli`'s own STATE.md for the full engineering
writeup, including the live AWS Secrets Manager verification (a real
`aws_secretsmanager_secret_version`, rotated and grepped for leaked
material) and the `aws_iam_access_key` negative finding that preceded it.

## UBI-21: GCP support, both stages (2026-07-16, same session as the code)

`ubiquex-cli`'s first cross-provider generalization, both stages
(Stage 1 hermetic; Stage 2 needed a real GCP account, set up mid-session):

- **`getting-started/installation.mdx`** now mentions
  `--source hashicorp/google --provider-version <version>` alongside
  AWS, and GCP credential setup (`GOOGLE_APPLICATION_CREDENTIALS` /
  `gcloud auth application-default login`) alongside AWS's own
  credential chain.
- **`cli/lookup.mdx`** gained a GCP section: five live-verified types
  (`google_service_account`, `google_project_iam_custom_role`,
  `google_storage_bucket`, `google_pubsub_topic`,
  `google_secret_manager_secret`), each with its actual confirmed
  `--lookup` shape, not a guess. A `Warning` calls out the two types
  (`google_pubsub_topic`, `google_secret_manager_secret`) whose `id`-alone
  mistake produces **no error at all** — `ReadResource` succeeds, but the
  resource's own natural-key attribute comes back empty — a materially
  more dangerous shape than anything the existing AWS table shows, since
  nothing signals anything went wrong.
- **`concepts/attribution.mdx`**'s "Beyond AWS" section, written in an
  earlier part of this same session as a description of a design not yet
  built, was rewritten once `gcpaudit/` actually shipped: a real
  transcript (a real Pub/Sub drift, the real GCP account email that
  caused it, a real event ID), not a future plan. A `Warning` documents
  a real, confirmed gap: GCP audit log entries don't consistently name
  the affected resource the same way across services (Pub/Sub uses the
  project ID; Secret Manager uses the numeric project number instead),
  so `google_secret_manager_secret` drift can't be attributed via this
  backend yet, even when a matching audit log entry genuinely exists.

`mint validate`/`mint dev`/`mint broken-links` all pass clean. See
`ubiquex-cli`'s own STATE.md for the full engineering writeup, including
every empirical finding behind these docs (per-type lookup shapes, the
GCP IAM read-after-write lag, the correlation gap, and a real UBI-20
regression this session's own live test runs caught and fixed).

## UBI-20: hardening pass reference (2026-07-16, same session as the code)

Four workstreams, one ubiquex-cli session, all documented same-session:

- **Exit-code contract** — new `cli/exit-codes.mdx`: the general 0/1/2
  principle explained once, then one table per verb (`scan`, `status`,
  `accept`, `why`, `writeback`, `revert-plan`, plus the 0/2-only
  `version`/`init`/`propose`), a CI-gating `bash`/`case` example. Cross-
  linked from every affected page's own body or Related list.
  `cli/writeback.mdx` and `cli/revert-plan.mdx` each had a sentence
  claiming a declined attribute / manual step "is not a command failure"
  — true before this session, but now incomplete: it doesn't fail, but it
  does exit `1`. Reworded rather than left to mislead a reader checking
  `$?` in CI. `cli/why.mdx`'s `--verify-acceptance` section got the
  equivalent fix (a reviewer `MISMATCH` used to be described as "never a
  hard failure," full stop — now correctly distinguishes "not a hard tool
  error" from "still exits 1").
- **`--json` schemas** — a `## --json output` section added to
  `cli/scan.mdx`, `cli/status.mdx`, `cli/why.mdx` each, every example a
  real transcript (captured from the built binary for `scan`/`status`;
  `why`'s `--verify-acceptance` JSON payload from the CLI test suite's own
  fixture-driven fake GitHub server, the same "real, not fabricated"
  standard used throughout this repo — see UBI-13's own note on that).
- **Teaching errors** — `cli/lookup.mdx` gained a note that `ubx`'s own
  runtime error text now names the fix directly for the three types
  (`aws_s3_bucket`/`aws_iam_role`/`aws_iam_user`) whose mistake is a
  missing field, cross-linked to `cli/exit-codes.mdx` for the resulting
  exit code. The page's own table needed no correction — it already
  described the *required* shape correctly; only the new runtime error
  text's direction needed catching (see ubiquex-cli's STATE.md Surprises
  for the live-verification finding that caught it before it shipped).
- **Ledger lock** — new "Concurrent access" section on
  `concepts/ledger.mdx`: what `.ubx/lock` protects (only `accept`, never
  `scan`/`why`/`status`), two real transcripts (live contention timing
  out, a stale lock detected and reported), and why `ubx` never
  auto-removes a confirmed-stale lock. This closes the exact gap this
  file's own "Possible future improvements" note (below, now cleared)
  had flagged as open. Cross-linked from `cli/accept.mdx` and
  `cli/exit-codes.mdx`'s `accept` row.

`mint validate`, `mint dev`, and `mint broken-links` all pass clean.

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

None open. The `.ubx/lock`/concurrent-access gap noted here previously
was closed in the UBI-20 session above (`concepts/ledger.mdx`'s new
"Concurrent access" section).

## Next steps

No open UBI-13 or UBI-20 work. Next docs session starts from whatever new
user-visible change lands in ubiquex-cli next and gets logged as debt
there.
