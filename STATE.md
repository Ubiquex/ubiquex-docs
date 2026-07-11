# STATE — ubiquex-docs

## Current slice

UBI-13, Session 1: scaffold + spine. Done.

- `docs.json` navigation (Getting Started / Concepts / CLI Reference groups).
- `index.mdx` landing page.
- `getting-started/installation.mdx` — honest placeholder: no packaged
  releases exist yet (`ubiquex-cli` is a private repo, no tags, no
  `.goreleaser`, no CI), so the only documented path is build-from-source.
- `concepts/proposal.mdx`, `concepts/ledger.mdx`, `concepts/drift.mdx`,
  `concepts/attribution.mdx`, `concepts/why.mdx` — mental model pages, drawn
  from `ubiquex-cli/docs/architecture.md` but written for users. Every
  example is a real transcript captured from an actual `ubx` + fake-provider
  run this session, not fabricated. Deliberately excludes anything from
  architecture.md that isn't shipped (IR resolver, SDK, intent/LLM provider,
  policy engine, cross-stack refs, Nexus/SaaS, `revert`/`drift_revert` kinds
  — the latter two are declared enum constants with zero implementing code,
  confirmed via grep, so they're not documented as usable).
- `cli/version.mdx`, `cli/scan.mdx`, `cli/accept.mdx`, `cli/propose.mdx`,
  `cli/why.mdx`, `cli/writeback.mdx` — skeleton pages (synopsis + plain-
  language description + forward links). Each explicitly notes that full
  flag tables and verified examples are follow-up work, and that
  `ubx <cmd> --help` is authoritative in the meantime.
- Validated: `mint validate` passes clean; `mint dev` smoke-tested (home,
  a concept page, a CLI page all 200, no errors/warnings in the server log).

## Docs debt (ubiquex-docs)

Open, for subsequent UBI-13 sessions:

- Per-verb CLI reference pages need full flag tables verified against
  `--help` output of the actual built binary, plus runnable/verified
  examples, for all six verbs (`version`, `scan`, `accept`, `propose`,
  `why`, `writeback`).
- Flags not yet documented anywhere (skeleton pages punt on all of these):
  `scan`/`accept`'s `--source`/`--provider-version` (UBI-8 acquisition),
  `scan`'s `--no-attribution` (UBI-10), `accept`'s `--from-merge`/
  `--repo-dir`/`--proposal-file`/`--github-repo` (UBI-11 stage 1 PR-merge
  acceptance), `why`'s `--verify-acceptance`/`--repo-dir`/`--github-repo`
  (UBI-11 stage 1), `writeback`'s `--tf-dir`/`--write` (UBI-11 stage 2),
  `scan`'s `--surface-as issue|pr`/`--github-repo`/`--tf-dir` (UBI-11
  stage 3).
- A `guides/` section doesn't exist yet. Per prior debt note in
  ubiquex-cli's STATE.md, the PR-merge acceptance workflow (trailer
  convention, zero-approvers-is-normal, the whole propose→PR→merge→accept
  flow) is a real workflow, not just flags — it probably deserves its own
  guide page rather than being buried in `cli/accept.mdx`'s flag table.
- The conformance-registry per-type lookup-requirement table (what the
  user flagged as "the top support question waiting to happen") isn't
  written yet — belongs either in `concepts/drift.mdx` or as its own
  reference page once the per-verb pages exist to link it from.

## Next steps

Pick up per-verb reference pages against the built binary, starting
wherever ubiquex-cli's own STATE.md docs-debt list points next.
