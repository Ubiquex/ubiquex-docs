# CLAUDE.md — ubiquex-docs

## What this is

User-facing documentation for `ubx` (ubiquex), built on **Mintlify**.
Audience: platform engineers evaluating or using ubx. This repo is a *projection*
of the product — it documents what is shipped, never what is planned.

The source of truth for design/architecture lives in the `ubiquex` repo
(`docs/`). Never document internal design here; translate shipped behavior
into user language.

## Structure conventions (Mintlify)

- Pages are `.mdx`, navigation in `docs.json` — every new page MUST be added
  to navigation or it's invisible.
- Sections: `concepts/` (proposal, ledger, drift, why), `cli/` (one page per
  command), `guides/` (task-oriented walkthroughs), `getting-started/`.
- CLI reference pages follow a fixed skeleton: synopsis, description, flags
  table, at least one real example with real output, related commands.
- Use Mintlify components (Callout, CodeGroup, Steps) sparingly and
  consistently; prefer prose + code blocks.

## Writing rules

- Document behavior as it IS in the latest released ubx, verified against the
  actual CLI output — never from memory, never from plan.md.
- Every code example must be runnable as shown. Test before committing.
- Tone: precise, direct, no marketing language in reference pages. Concepts
  pages may explain the "why" (proposals, ledger) — that's the one place for
  narrative.
- Terminology is fixed: "proposal", "ledger", "adopt", "revert", "stack",
  "drift". Never introduce synonyms.

## Workflow

1. Docs debt arrives from ubiquex's STATE.md ("docs debt" entries) —
   batched per slice during foundational phase.
2. Each docs session: read the debt list, verify actual CLI behavior, write
   pages, clear the debt entries in ubiquex's STATE.md.
3. Mintlify preview (`mintlify dev`) must render clean before commit.

## Git rules

Same as ubiquex: Roozbeh's identity and signing key, no AI attribution
anywhere, terse conventional messages (`cli-ref: add ubx scan page`).
