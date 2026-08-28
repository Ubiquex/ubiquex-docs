# CLAUDE.md — ubiquex-docs

## What this is

The public documentation site for `ubx` (Mintlify). Coordinating repo:
`github.com/ubiquex/ubiquex` — user-visible changes to `ubx` (new commands,
flags, behaviors) update this repo in the SAME session they land in
`ubiquex`, per that repo's own CLAUDE.md rule 5.

## Git rules

- Direct commits and pushes to `main` ARE allowed here, unlike the SDK/schema
  repos — confirm the checkout you're editing is actually this real,
  git-connected repo before pushing anything (`git remote -v`); a stale or
  disconnected local copy under a similar-looking path is a real, previously
  hit mistake, not a hypothetical one.
- NO AI attribution anywhere in commits or PR bodies.
- If ever working from a feature branch instead of `main` directly: before
  pushing more commits to it, confirm any PR on it is STILL open (`gh pr list
  --state open` or `gh pr view <n>`) — a merged PR's branch looks identical to
  any other from `git status` alone, and a push after merge lands nowhere
  near `main`, silently.

## Content discipline

- Pages must be verified against the actual built `ubx` binary — transcripts
  real (rebuilt `ubx` + a fresh `fakeprovider` binary, captured verbatim, not
  hand-edited), flags sourced from `--help`, not guessed.
- Never run `ubx ship` (or anything that reaches a provider's own
  `ApplyResourceChange`) against a real cloud provider for a doc transcript,
  even one already credentialed on the machine — use the hermetic
  `fakeprovider` binary via `UBX_PROVIDER_MIRROR` instead, always.
- `mint validate` / `mint broken-links` clean before considering any change
  done.
- "Committed and pushed" is only true once `git log -1` in this real checkout
  shows the commit AND the content is confirmed via `gh api
  repos/Ubiquex/ubiquex-docs/contents/<path>` (this repo is private —
  `raw.githubusercontent.com` 404s unauthenticated) — a real, repeated past
  incident (`ubiquex`'s own `HISTORY.md`, search `UBI-140`/`UBI-141`) reported
  this twice before either was actually true, both times because the edits
  landed in an unconnected local copy at a similar-looking path, not this
  real repo.
- An architectural change to this repo's own pipeline (a new artifact
  type, a change to the coverage check, a change to provenance
  enforcement, a new generation mechanism) is documented in
  `ubiquex-internals` (the developer documentation site) in the same
  body of work, never a follow-up — a bug fix inside an
  already-documented mechanism doesn't qualify (matches `ubiquex`
  CLAUDE.md rule 10; `ubiquex-internals`' own `Docs Pipeline` page is
  the real target).
