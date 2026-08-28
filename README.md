# ubiquex-docs

The user-facing documentation corpus for `ubx`. A Mintlify site,
published at [docs.ubiquex.io](https://docs.ubiquex.io).

## Where this sits

Documents [ubiquex](https://github.com/Ubiquex/ubiquex) (the CLI and
codegen this whole corpus describes) and the six `ubx-sdk-<provider>`
bindings repos (`aws`, `azure`, `google`, `kubernetes`, `github`,
`datadog`), whose real, current resource and data-source content this
site's own resource-reference section is generated from. Nothing in
this repo generates or affects those repos; the dependency runs one
way, docs describe code, never the reverse.

See [ubiquex-internals](https://github.com/Ubiquex/ubiquex-internals)
for the architecture and design explanation this site deliberately
does not carry, this repo is user-facing content, that one is
developer-facing explanation.

## What it contains

- `resource-reference/`: one page per real resource/data-source type,
  per provider, generated content
- `artifacts/<provider>/`: the committed, reviewed, versioned source
  data generation assembles into pages, see "The artifact model" below
- `concepts/`: hand-written conceptual pages (blueprints, drift,
  outputs, and so on)
- `tutorial/`: step-by-step, verified-against-the-real-binary walkthroughs
- `cli-reference/`: one page per real `ubx` command, flags and examples
- `scripts/resource-reference-gen/`: the real generator, golden-page
  verification, and coverage check
- `install/`, `integrations/`, `server/`: setup and integration guides
- `docs.json`: Mintlify navigation and site config

## The artifact model

Nothing about `artifacts/` is self-explanatory from the directory alone,
so it gets its own explanation here rather than assumed obvious.
Generation assembles artifacts into pages; it does not decide content.
Four real files per provider, plus a manifest:

- `descriptions.json`: field-level text, keyed by full field path, each
  entry recording its real source (vendor spec first, AI only where the
  vendor text is missing or thin)
- `intros.json`: one real, unique paragraph per resource, summarizing
  the vendor's own overview documentation in this project's own words
- `categories.json`: per-service sidebar grouping, with per-resource
  overrides for cases a mechanical split gets wrong
- `exclusions.json`: which resources are real but not
  description-generated (`skip_descriptions`), and which aren't
  documented at all (`skip_page`), each with a required reason
- `manifest.json`: onboarding state, so a generation run is resumable
  rather than needing to rediscover where it left off

## How to use it

```
npm install -g mint
mint dev        # local preview
mint validate    # confirm the corpus builds
mint broken-links # confirm no dead links
```

`.github/workflows/docs-structure-gate.yml` runs both checks on every
push to `main`; `validate` fails the build, `broken-links` opens a
tracking issue rather than failing (see that workflow's own header
comment for why).

## How it's maintained

Most of this corpus is generated, not hand-written, the single most
surprising thing about it to someone new. `scripts/resource-reference-gen/`
regenerates resource-reference pages from `artifacts/` against a real,
current schema dump; `.github/workflows/coverage-watch.yml` runs
weekly and opens a tracking issue the moment the schema grows content
the corpus hasn't caught up to; `.github/workflows/golden-page-gate.yml`
diffs every regeneration against one committed golden page per
provider and fails the build until a real diff is reviewed and
accepted. Hand-written content (`concepts/`, `tutorial/`,
`cli-reference/`) is never regenerated and is edited directly.

## Links

- Docs: https://docs.ubiquex.io
- Internals (architecture and design): https://github.com/Ubiquex/ubiquex-internals
- Linear board: https://linear.app/ubiquex
