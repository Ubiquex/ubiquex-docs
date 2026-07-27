# STATE — ubiquex-docs

## UBI-46: chat — `ubx chat`, dialogue capture, `ubx why --dialogue` (2026-07-28, same session as the code)

`ubiquex-cli`'s intent-provider arc gains its second medium this session —
chat, riding UBI-41's own `Adapter`/`DraftWithRetry` interface unchanged,
exactly as that arc's closing comment predicted:

- **New `guides/chat.mdx`** (new entry in the existing "AI-Assisted
  Authoring" nav group, alongside `guides/md-medium.mdx`): the full
  interactive-loop walkthrough — setup (the identical `[intent]` config
  `--from-doc` already uses, no new config key), a real two-turn session
  refining the `payments` stack ("like our staging database but smaller,"
  then "make it multi-az"), the resulting `dialogues/<hash>.dlg.json`
  structure and why it embeds a pre-provenance copy of the draft, why
  `dialogues/` lives top-level rather than under `ledger/` (cross-linked
  to `concepts/ledger-stores.mdx`'s own authoring-mediums split), a second
  real session demonstrating a contradiction ("db.t3.large" then
  "actually, use db.t3.micro instead") resolved by later-turn-wins with
  the override named in `intent.assumptions`, per-turn redaction, and
  session abandonment (`/quit`/EOF) leaving no file behind. Closes with a
  real, freshly-captured `ubx why --dialogue` transcript walking a real
  accepted proposal back to the real conversation that produced it.
- **`cli/why.mdx`** gained the new `--dialogue` flag (flags table) and a
  new "Rendering a captured dialogue" section: the same real transcript
  as the guide, plus the explicit no-dialogue-source message a proposal
  that didn't come from `ubx chat` renders instead of silent nothing.
- **`cli/config.mdx`** and **`cli/propose.mdx`** both gained a one-line
  cross-link to the new guide — no new config surface, since chat reads
  the identical `[intent]` table `--from-doc` already documents.

Every transcript in the new guide and in `cli/why.mdx`'s new section is
real: the two chat sessions ran against the real Claude API this session
(reusing `ubiquex-cli`'s own live-finale work, not re-fabricated for
docs), and the `ubx why --dialogue` transcript was captured fresh, this
session, by running the actual built binary against the real accepted
proposal and dialogue file still on disk from that same live finale. Two
places (a contradiction session's own turn-1-only render, and an
abandoned-session example) are explicitly marked as elided rather than
inventing specific model output that was never actually captured —
consistent with this file's own "real transcripts, honestly labeled when
something is illustrative rather than captured" standard.

`mint validate`/`mint broken-links` both pass clean. See `ubiquex-cli`'s
own STATE.md for the full engineering writeup, including the directory-
location decision's real citation and the live-verified contradiction
probe. **UBI-46 closed in Linear** this session.

## UBI-41: the md medium — `ubx propose --from-doc` (2026-07-28, closing session, same day as the code)

`ubiquex-cli`'s intent-provider arc (Phase 3's opener — AI enters the
product) reaches its first user-visible surface this session, closing
the arc:

- **New `guides/md-medium.mdx`** (new "AI-Assisted Authoring" nav group):
  the full walkthrough — setup (`.ubx/config`'s `intent` table), a real
  transcript with all three ambiguity sections populated (`Assumptions`/
  `Defaults`/`Questions`, including a `blocking` question the model
  correctly raised about an unresolvable `@ref`), the written draft
  file's own `intent.sources` provenance (`document`/`intent_provider`
  kinds), a redaction-at-capture demonstration (a real AWS example key
  pasted into a doc, confirmed absent from the output via a direct
  `grep`), and what happens after the draft (`ubx resolve`/`accept`/`ship`
  — never auto-chained).
- **New `guides/md-authoring-conventions.mdx`**: `@refs`, requirement
  phrasing, cost ceilings — stated as guidance that improves extraction
  quality, never a grammar `ubx` enforces (`ubiquex-cli`'s own conformance
  suite, not this page, defines what actually works reliably).
- **`cli/propose.mdx`** rewritten throughout: the page now documents two
  genuinely different modes sharing one verb (`ubx propose <proposal.json>`
  unchanged; the new `ubx propose --from-doc`), new flags table entries,
  a full `--from-doc` example with the real transcript above, and three
  real error transcripts (`--stack` required, `--from-doc`+positional-arg
  mutual exclusivity, an unresolvable `key_ref.env`).
- **`cli/config.mdx`** gained a new `### intent` section (matching the
  existing `k8s_audit`/`ledger` subsection pattern): the table shape,
  what `key_ref`/`auth`/`vertex` mean, a `<Warning>` on the
  named-but-empty-env-var refusal (with a real transcript), and a real
  `ubx config` transcript showing `intent.*` provenance.
- **`concepts/proposal.mdx`** gained a short paragraph on the new
  `assumptions`/`defaults`/`questions` fields an `--from-doc`-resolved
  proposal's own `intent` object carries, and a cross-link.

Every transcript is real, captured against the actual built `ubx` binary
making real calls to the real Claude API (`ANTHROPIC_API_KEY` supplied by
the user for this session) — none hand-written. Three real findings from
`ubiquex-cli`'s own live verification work this arc (a system-prompt
self-priming bug, a real empty-`resources[]` bug, a real but non-bug
safety-classifier refusal) are documented in that repo's own
`docs/intent-provider-conformance-report.md`, not duplicated here — this
repo documents shipped user-facing behavior, not the engineering history
behind it, per this file's own standing convention.

`mint validate`/`mint broken-links` both pass clean. See `ubiquex-cli`'s
own STATE.md for the full engineering writeup across all four sessions of
this arc, and its own `docs/intent-provider-conformance-report.md` for
Claude's own published conformance numbers. **UBI-41 closed in Linear**
this session — chat (rides this arc's own adapter interface, its own
future session) and OpenAI/Gemini/local adapters (parked on the roster,
no code) both named explicitly as what stays open, not silently implied.

## UBI-30 session 3: `ubx accept`/`ubx ship` gain destroys (2026-07-18, same session as the code)

`ubiquex-cli`'s executor (docs/executor.md's own "Amendment (UBI-30):
shipping destroys") gains real destroy execution this session -- sessions
1-2 (docs-only, then resolver support) correctly didn't touch this repo.

- **`cli/accept.mdx`** gained a new "Confirming a destroy" section: the
  `--confirm-destroys` flag (a new row in the flags table too), a real
  refused transcript (no flag, exit 1) and a real accepted one (with the
  flag) -- both captured from the actual built binary.
- **`cli/ship.mdx`** gained a new "Shipping a destroy" section: a real
  end-to-end chain (`ubx scan` adopts a resource, `ubx resolve` produces a
  destroy proposal, `ubx accept --confirm-destroys`, `ubx ship` applies
  it) with the human-text and `--json` output both real -- the `--json`
  transcript shows the exact `[present_matches, destroyed]` reconciliation
  pair the destroy-specific state machine produces. The intro paragraph
  and flags/description text no longer describe `change` proposals as
  creates-and-modifies-only.
- **`cli/exit-codes.mdx`**: `ubx accept`'s exit-1 row gained the new
  `--confirm-destroys` cause. While this file was already open: `ubx
  ship`'s own exit-2 row still said "wrong kind (not drift_revert)," never
  updated when `change` proposals became shippable (UBI-27) -- a
  pre-existing docs-debt item, not this session's own gap, corrected
  opportunistically rather than left for a future session to rediscover.
- Every transcript real, captured against the actual built binary
  (`cmd/ubx` + `provider/internal/fakeprovider`, which itself gained real
  destroy support this session -- a null-`PlannedState` branch and its
  first piece of cross-call process state, so a live `ReadResource` after
  a destroy genuinely reports the resource gone within one `ubx ship`
  invocation).

`mint validate`/`mint broken-links` both pass clean.

## UBI-30 session 2: `ubx resolve` gains destroys (2026-07-17, same session as the code)

`ubiquex-cli`'s resolver (docs/resolver.md's own "Amendment (UBI-30):
destroys") gains real destroy support this session -- session 1 was
docs-only in `ubiquex-cli`, correctly not touching this repo.

- **`cli/resolve.mdx`** updated throughout: frontmatter/intro no longer say
  "never destroys"; new `--known-dependent` flag documented in the flags
  table; new "Destroying a resource" section covering the dedicated
  `destroys` intent-file list, orphan protection (both the refusal and the
  two ways to make a would-be-orphaning destroy legal -- a mutual destroy,
  or repointing the dependent away first), and cross-stack orphan
  protection's three real outcomes (`not_performed`, `checked_clear`, and
  a real refusal against a genuine cross-stack pin). "When resolution
  fails" gained the destroy-specific error list.
- Every transcript is real, captured from the actual built binary
  (`cmd/ubx` + `provider/internal/fakeprovider`, `FAKEPROVIDER_MODE=ok-v6`)
  against real temporary ledger directories -- adopt via `ubx scan`/`ubx
  accept`, link a dependent via a same-batch `$ref`-bearing modify,
  observe the real orphan refusal, repoint the dependent away in a
  separate proposal, observe the destroy succeed. The cross-stack refusal
  transcript used a real second ledger directory with a genuine `$cross`
  pin recorded against the destroy target, not a hand-written example.
- One real bug this transcript work found and got fixed in the code (not
  just the docs): the orphan-protection walk originally accumulated every
  historical `depends_on` mention forever, so a destroy stayed refused
  even after its dependent had genuinely been repointed away by a later,
  separate proposal. Fixed to track each address's own most recently
  recorded `depends_on` only, with a new hermetic regression test
  (`core/resolver/destroys_test.go`) reproducing the exact scenario this
  transcript surfaced.

`mint validate`/`mint broken-links` both pass clean.

## UBI-26 (closing session): `ubx why`'s new apply-history rendering (2026-07-17, same session as the code)

`ubiquex-cli`'s live adversarial-program session against real AWS found a
real gap: `ubx why` never rendered anything about a shipped `drift_revert`'s
own apply history. Fixed same session in the code; docs updated here too,
since it's a real, user-visible behavior change, not internal-only.

- **`cli/why.mdx`** gained a new "A shipped `drift_revert`'s apply history"
  section: the real transcript (a clean single-attempt ship, and an
  interrupted-then-reconciled multi-attempt one), captured from the actual
  built binary against real AWS infrastructure, not hand-written. A new
  `--json` example showing the `applies` array.
- **`concepts/apply-record.mdx`** and **`concepts/why.mdx`** cross-link to
  the new section.
- The main published reliability report itself
  (docs/reliability-report.md) lives in `ubiquex-cli`'s own repo docs, not
  here -- it's an internal engineering artifact this session drafted, not
  end-user-facing CLI/concept documentation.

`mint validate`/`mint broken-links` both pass clean.

## UBI-26: `ubx ship` -- the executor's first user-visible surface (2026-07-17, same session as the code)

`ubiquex-cli`'s executor (docs/executor.md, docs/schema.md's apply-record
amendment) reaches its first user-visible CLI surface this session --
sessions 1-2 were docs/hermetic-code-only, correctly not touching this repo.

- **New `cli/ship.mdx`**: `ubx ship <proposal-id>` -- the one `ubx` command
  that actually changes real infrastructure. Every transcript is real,
  captured from the actual built binary against a fakeprovider subprocess
  (the same fixture `ubiquex-cli`'s own tests use): a clean apply, an
  idempotent re-run (`already fully applied`), `--json` output, a
  simulated terminal provider diagnostic, and a hand-constructed
  redacted-restore-target proposal being declined outright. A
  `partially_applied` outcome is described narratively (hermetic
  test-suite territory) rather than faked with an unverified transcript --
  this project's own standing discipline against inventing output.
- **New `concepts/apply-record.mdx`**: the ledger object `ubx ship`
  produces -- where it lives, the state machine (with the durability
  invariant stated plainly), the idempotency table, redaction at the apply
  boundary in both directions, and the `drift_revert`-only v1 scope.
- **`cli/exit-codes.mdx`** gained a `ubx ship` section (0/1/2, matching
  every other UBI-20-audited verb's table shape) and a cross-link.
- **`cli/revert-plan.mdx`** gained a `<Note>` distinguishing the two
  commands now that both exist: `ubx revert-plan` still never applies
  anything, and is still the only path for an attribute `ubx ship`
  declines (a redacted restore target).
- **`concepts/proposal.mdx`**/**`concepts/secrets.mdx`** cross-link to the
  new apply-record concept page and `ubx ship`'s own redacted-attribute
  behavior respectively.
- **`docs.json`** nav: `concepts/apply-record` added to Concepts,
  `cli/ship` added to CLI Reference (after `cli/revert-plan`, before
  `cli/exit-codes`).

`mint validate`/`mint broken-links` both pass clean.

## UBI-25: read-only MCP server (2026-07-18, same session as the code)

`ubiquex-cli`'s `ubx mcp` verb -- `ubx` as assistant tools:

- **New `guides/mcp.mdx`** ("ubx + your AI assistant"), added to the
  Guides nav group: what the three tools (`ubx_why`/`ubx_status`/
  `ubx_scan`) answer and which CLI command each mirrors, the
  boundary-by-omission stance (`accept`/`ship`/`writeback`/`revert-plan`/
  `scan --surface-as` are not exposed, stated plainly rather than left to
  be inferred from absence), Claude Code (`claude mcp add`, verified for
  real against a scratch project before writing it down) and Claude
  Desktop (`claude_desktop_config.json`) setup, a real transcript, and
  the full `ubx mcp --help` text.
- **The transcript is real**, not hand-written: captured against the
  same real `ubx-states` S3 bucket/ledger this project's live-verification
  work has used since UBI-9/UBI-10 -- a real tag mutation, scanned with
  real CloudTrail attribution, then asked "who changed this bucket and
  when" via a real MCP client connected to the real `ubx mcp` subprocess
  over stdio. Trimmed to the two most recent of 24 real matching
  CloudTrail events for readability; nothing about the mechanism itself
  trims it for a real client.
- **Cross-links added** from `cli/why.mdx`/`cli/status.mdx`/`cli/scan.mdx`
  to the new guide, each naming the specific MCP tool it mirrors.

`mint validate`/`mint broken-links` both pass clean. See `ubiquex-cli`'s
own STATE.md for the full engineering writeup, including a real SDK
gotcha (automatic JSON-schema generation over `json.RawMessage` fields)
found by actually calling the tools over the real protocol before this
page was written, not assumed safe from the Go types alone.

## UBI-24: sensitive-override table (2026-07-18, same session as the code)

`ubiquex-cli`'s fix for UBI-22's own `helm_release` redaction gap —
"we do not treat upstream flags as the ceiling":

- **`concepts/secrets.mdx`** gained a new "The provider's schema is a
  floor, not a ceiling" section (right after "What gets redacted, and
  when"): the union model (schema flags + a ubx-owned override table,
  additive only), the real audit finding (checked both
  `hashicorp/kubernetes` and `hashicorp/helm`, nothing further found),
  and a mention of the draft, unsubmitted upstream issue for the Helm
  provider (`docs/upstream/helm-sensitive-flags.md` in `ubiquex-cli`).
- **`cli/scan.mdx`**'s own Helm section needed a real correction, not
  just an addition: its example values-drift transcript previously
  showed `metadata[0].values` as *raw*, unredacted JSON, and its
  `Warning` described the gap as still open. Both were written before
  UBI-24 shipped the override table; now that it has, the same
  transcript always redacts (regardless of what a given chart's values
  actually contain), so the doc was corrected to show that, and the
  `Warning` now states the gap is closed by `ubx`'s own override table
  rather than left as a disclosed-but-unfixed limitation.

`mint validate`/`mint broken-links` both pass clean. See `ubiquex-cli`'s
own STATE.md for the full engineering writeup, including the live `kind`
cluster verification (a real Helm release with a secret-looking value,
adopted and drift-tested, proposal file grepped by hand for zero
material both times) and the precise correction that `helm_release`'s
`metadata` is a compound-typed attribute, not a real nested block —
which is exactly why tfplugin's wire protocol has no way to flag one of
its sub-fields Sensitive upstream, and why a ubx-side, JSON-shape-driven
override was the right fix regardless of upstream cooperation.

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
