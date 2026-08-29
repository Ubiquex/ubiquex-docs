# resource-reference-gen

Real, tracked tooling behind every `resource-reference/<provider>/...`
page in this repo. UBI-144's richer template (complete runnable
programs, richer real params, a real markdown scenario) is the ONLY
real page shape this tooling produces -- every currently-live page
across all six providers is on it.

The original, sparse "mechanical" tier (`build_resource_page`,
`gen_mechanical_pages.py`) is REMOVED entirely, not just deprecated: a
real `go build` against its own literal output failed outright
("expected 'package', found 'import'" -- no `package main`/`func
main(){}` wrapper at all), and a resource whose example can't compile
as shown must never be selectable as final output again. It was never
meant to be a final, shipped shape even historically -- every one of
the original AWS/GCP/Azure/Kubernetes pages was immediately spliced
onto the richer tier before ever being considered done; the mistake
this session corrected was treating that transient scaffold step as
sufficient for onboarding Datadog.

This directory used to be an uncommitted scratch script pointed at the
wrong (disconnected) docs directory -- a real gap, closed here. Nothing
in this pipeline invents a field name, a resource relationship, or a
provider convention that isn't drawn from a real, checked source.

## The real pipeline, three steps

### 1. Dump a real provider schema

Every real provider (thirdparty tfplugin sources AND
`[dynamic_providers.<name>]` entries alike) now goes through this one
real, tested, provider-agnostic `ubx sdk gen --dump-ir` flag, run from
within a real `ubiquex` checkout (`cd` to `sdk/providers`, the repo's
own real, central `.ubx/config`):

```bash
ubx sdk gen --only datadog --dump-ir /tmp/schema-dump --out /tmp/unused
```

Writes one real `<wire_type>.json` per resource type under
`/tmp/schema-dump/<name>/` (identical shape this directory's own
former `dump_schema.go` tool produced -- straight from
`sdk/codegen/ir.FromSchema`, the SAME shared IR translator the real
Go/TS/Python bindings codegen uses -- but with real DescriptionSource
enrichment now correctly applied, which that tool never did), PLUS a
combined `/tmp/schema-dump/<name>/schema.json` (`{wire: {"service",
"localName", "ir": {"Fields"}}}`) -- the whole-provider shape step 3's
own `gen_new_provider_pages.py` needs, computed from the real, same
`ir.ServiceAndLocalName` codegen already uses, not reimplemented here.

`--only <name>` restricts to one declared provider (a
`[thirdparty_providers]` source string or a `[dynamic_providers.<name>]`
name) -- omit it to dump every declared provider in one run.
`dump_schema.go` (this directory's own former tool, tfplugin-only,
never enriches descriptions) is superseded by this flag for every
real provider now that all six source through `ubx-provider-dynamic` --
kept in tree for now, not deleted, but should not be reached for by a
new session; see its own doc comment.

**UBI-197: `ubx sdk gen` also writes a real `PROVENANCE.json` sibling**
(source, commit, dirty, unpushed -- which real `ubx-provider-dynamic`
checkout state produced this dump) next to `schema.json` here, and next
to every real `--out` repo directory step 2 below produces. `regen_pages.py`
and `gen_all_data_source_pages.py` both read these back and refuse to
run unless every one they find is present, clean, pushed, and the whole
batch agrees on one commit -- real root-cause fix for the exact failure
this ticket started from (the published data-source corpus was once
built entirely from a real, unmerged WIP branch, with nothing anywhere
recording that it happened). Pass `--allow-dirty-provenance` to either
script for a deliberate local experiment that will never be committed;
never pass it for a real batch meant to publish.

### 2. Extract real identifiers from the published bindings

```bash
python3 extract_idents.py aws \
    ~/Ubiquex/ubx-sdk-aws-go ~/Ubiquex/ubx-sdk-aws-py ~/Ubiquex/ubx-sdk-aws-ts \
    /tmp/aws_idents.json
```

Scans the real, already-published SDK bindings repos for each
resource's own real package/binding/config identifier per language --
never guessed or derived from the wire name alone. For a provider with
no published `ubx-sdk-<name>{,-go,-py,-ts}` repos yet (real, confirmed
gap for `datadog`/`github` as of this pipeline's own dynamic-provider
switch -- `gh repo view` returns zero results for both), point these
three roots at a real LOCAL generation instead:

```bash
ubx sdk gen --only datadog --lang go --out /tmp/local-sdk
ubx sdk gen --only datadog --lang py --out /tmp/local-sdk
ubx sdk gen --only datadog --lang ts --out /tmp/local-sdk
python3 extract_idents.py datadog \
    /tmp/local-sdk/datadog/sdk/go /tmp/local-sdk/datadog/sdk/python /tmp/local-sdk/datadog/sdk/typescript \
    /tmp/datadog_idents.json
```

The extracted identifiers are real either way (the same codegen a
published repo would contain) -- only the SOURCE differs. Publishing
real `ubx-sdk-datadog`/`ubx-sdk-github` repos is separate, real,
unstarted work, not something this docs pipeline does as a side
effect.

### 3. Generate pages

**New provider** (no resource-reference/<provider> pages at all yet)
-- the ONLY tool that may write a first, final page for a resource,
always the complete richer template, never a fragment:

```bash
python3 gen_new_provider_pages.py datadog datadog Datadog \
    /tmp/schema-dump/datadog/schema.json /tmp/datadog_idents.json \
    --bindings-status local_only   # omit for a provider with published SDK repos
```

Every schema_name passed here must have a real, confirmed entry in
`REAL_SDK_REPO_ID` (`gen_provider_docs.py`) first -- verified against
the real GitHub org, never inferred.

**Existing pages only**, touching up one resource or a real batch at a
time -- splices ONLY the `## Example` section into whatever page
already exists, never touches Input properties/Output properties/See
also or any other hand-tuned prose on that page. This tool cannot
onboard a new provider (it hard-skips with "no existing page" if the
target doesn't exist yet -- use `gen_new_provider_pages.py` for that):

```bash
python3 gen_complete_pages.py --schema-dir /tmp/schema-dump --idents-path /tmp/aws_idents.json \
    aws_iam_policy aws_sqs_queue aws_s3_bucket
# or: --wires-file a-real-batch.txt
```

## Verification, non-negotiable, every real batch

`gofmt`/`deno fmt` run INLINE at generation time (`gofmt_lines`/
`deno_fmt_lines` in `gen_provider_docs.py`) -- a page that fails either
never gets written at all. That only proves syntax, though; it has
already once missed a real bug (an import a preamble needed, requires
matched only against the FIRST preamble that needed it, not the
second). Run these three passes on every batch before committing:

```bash
python3 verify_go_blocks.py --sdk-go-root ~/Ubiquex/ubx-sdk-go \
    --sdk-provider-go-root ~/Ubiquex/ubx-sdk-aws/sdk/go \
    <changed-page.mdx> [<changed-page.mdx> ...]

python3 verify_py_blocks.py <changed-page.mdx> [<changed-page.mdx> ...]

npm install   # once, installs playwright into this directory only
node crawl_overflow.js <pages-file> http://localhost:PORT out.jsonl 4
```

`crawl_overflow.js` needs a real `mint dev` instance running against
this checkout. It clicks through all four tabs (Go/TypeScript/Python/
Markdown) per page -- UBI-148's own original crawler only ever measured
whichever tab happens to be active by default, which misses real
overflow in every other tab.

**A wide code block that's still fully contained by its own
`overflow-x: auto` wrapper (`document.documentElement.scrollWidth ===
clientWidth`, page-level, never breaks layout) is acceptable** -- this
was checked and approved explicitly (UBI-144 Phase 1's own checkpoint,
confirmed again through Phase 2). Real page-level overflow, or a wide
block NOT contained by a scroll wrapper, is not.

## A fix to an artifact does not reach already-published pages

Real, standing gotcha, caught twice now (UBI-176's own 187 broken GCP
vendor links, 31 published pages affected). `vendor-spec`-sourced
description text is baked directly into each field's own real
`Description` at `--dump-ir`/generation time, straight from the raw
provider schema -- `regen_pages.py`'s own `inject_description` deliberately
never touches it (`SKIP_INJECTION_SOURCE`, "already baked in, don't
re-inject"). That means editing `artifacts/<provider>/descriptions.json`
alone, however correct, changes nothing on any page that was already
generated before the edit -- the page's own `.mdx` file still carries
the old, unfixed text verbatim, and nothing about `mint validate` or the
JSON's own validity will ever surface that gap.

**When fixing `vendor-spec` text (a broken link, a typo, anything baked
directly into the raw schema dump), always check whether any already-
published page carries the same broken text, and patch it too** -- grep
the real `resource-reference/<provider>/**/*.mdx` tree for the same
pattern the artifact fix targets, not just the artifact. Don't assume a
full corpus regen is the fix either: regenerating from the still-live,
still-unfixed vendor schema reproduces the identical broken text, since
the schema itself is upstream of both the artifact and the page. A
direct, targeted patch to the affected `.mdx` files (mirroring the exact
same fix applied to the artifact) is the correct, minimal fix -- verified
this way for UBI-176 (193 occurrences found baked into 31 live pages,
separate from and in addition to the 187 in the artifact itself).

## A full regen used to silently discard published bindings_status and abandon stale duplicate pages

Two real, related gotchas in `regen_pages.py` itself, fixed together (UBI-214)
since both are answered by the same question: does this wire already have a
page, and if so where and in what `bindings_status`. That question is now
answered once, per provider, at the start of a regen, by
`corpus_index.scan_provider_corpus` -- a real index of the CURRENTLY
COMMITTED tree, keyed by wire identity (see `real_wire_of`, not bare title:
a resource and its own same-named data source share identical bare `title:`
text and would otherwise collide).

**1. bindings_status data loss.** `regen_pages.py` used to hardcode
`bindings_status="local_only"` for every page it wrote, unconditionally. A
full regen would silently downgrade every one of the 9,623 pages UBI-196
deliberately, verifiably flipped to `"published"` back to `local_only`,
discarding real, already-verified work with no signal anywhere that it had
happened. Fixed: `regen_pages.py` now looks up each wire's own existing
`bindings_status` in the corpus index before writing, and only falls back to
`local_only` for a wire with no existing page. Verified live against a real
AWS regen: 1,700 already-published wires correctly preserved as published.

**2. Stale duplicate pages.** A wire whose service-directory derivation
improves (an established, recurring pattern in this pipeline) gets a fresh
page at the new, correct path on regen, but nothing used to delete the old
one -- confirmed live: 148 of a real AWS regen's new pages were exactly this,
and the old path was still live in `docs.json` navigation, not dead content.
137 of these had already been fixed once by hand in UBI-202 and simply
recurred on the next regen. Fixed: `regen_pages.py` now detects, for every
wire it writes, whether the corpus index already has that wire at a
DIFFERENT path, and reports it. Pass `--reconcile-stale-paths` to actually
delete the old file, update every `docs.json` navigation reference, and add
a redirect from the old published URL to the new one -- the same
wire-identity move mechanism UBI-209 used for 274 real page moves earlier
this project. Without the flag, `regen_pages.py` only reports the count and
leaves the old pages in place, since deleting files and rewriting navigation
is not something a report-only run should ever do silently.

`scripts/resource-reference-gen/check_duplicate_wires.py` is a standalone,
read-only detector for the same stale-duplicate condition, usable outside a
regen (e.g. as a scheduled CI gate, mirroring `coverage-watch.yml`'s own
shape) -- it always prints a real per-provider wire count and duplicate
count, including zero, since a check that only speaks when something is
wrong reads the same as a check that isn't running.

## Real, deliberate scope limits -- read before extending

- **`MAX_RICH_FIELDS = 8`** (`gen_provider_docs.py`): required fields +
  `name` + every pure-optional field, capped. A resource with dozens of
  optional fields (`aws_db_instance`, 87 real fields) still gets a
  readable example, not a wall of config.
- **`KNOWN_FAMILY_MARKDOWN`**: a real, multi-resource markdown scenario
  exists ONLY for resource families this session actually verified a
  real, already-published scenario for (currently: `aws_iam_role`,
  reusing `tutorial/markdown/references.mdx`'s own real content).
  Every other resource gets `render_generic_markdown_scenario` --
  real, mechanically built from the same example fields the other tabs
  show, but single-resource, since inventing a companion resource
  relationship this session hasn't verified is real would be worse
  than an honest, simpler scenario.
- **JSON-policy heuristics are two, deliberately separate, shapes**:
  `is_json_policy_field` (a real IAM TRUST policy -- has `Principal`,
  `sts:AssumeRole`) and `is_generic_policy_field` (a real IAM ACCESS
  policy -- no `Principal`, never `AssumeRole`). A real, found-in-
  review bug: reusing the trust-policy shape for `aws_iam_policy`'s
  own bare `policy` field produced real JSON, semantically wrong
  content. `redrive_policy` and other `*_policy`-suffixed fields are
  deliberately NOT matched by either heuristic -- their own real JSON
  shape differs again, and guessing wrong is worse than the generic
  placeholder fallback.
- **Two real, structural overflow patterns found across the first two
  real batches, neither fixable by trimming shown content**: deep
  nesting from the required `func main(){ Stack(func(){ ... }) }`
  wrapping (worst on resources with a JSON-policy preamble too), and
  `gofmt`'s own struct-field alignment padding every line in a literal
  to match its OWN longest real field name (worst on resources with
  genuinely long AWS field/service names, e.g. `secretsmanager`,
  `ApplicationFailureFeedbackRoleArn`). Tracked separately as UBI-150,
  not blocking rollout.

## UBI-175 Phase B: gap-fill description dictionaries

Real, tracked tooling for filling `artifacts/<provider>/descriptions.json`'s
own gap -- fields Phase A's schema mirror found no vendor description for
at all. Two pieces:

- **`common_gcp_fields.py` / `common_azure_fields.py`**: live-verified
  (`google.aip.dev`'s own AIP-122/132/148/154/155/216/217, `learn.microsoft.com`'s
  own ARM docs) dictionaries of field descriptions keyed by leaf field name
  (a dotted path's last segment) -- both providers' schemas repeat the SAME
  real, standardized vocabulary thousands of times over (Google's AIP
  conventions; Azure's ARM resource envelope, plus the Microsoft.Network
  resource provider's own deeply cross-referential object graph, the same
  pathology already `describe_exclude`'d once for `azure_network_virtualnetwork`).
  `FAMILY_LEAF`/`ARM_NETWORK` hold per-family dictionaries for the
  single largest, most repetitive families (GCP's aiplatform/dlp/dialogflow/
  bigquery/run; Azure's shared Network vocabulary) -- extend these, not the
  cross-provider dicts, when a specific family's own remaining fields share
  a real, recurring concept the shared dict doesn't cover.
- **`gap_fill_apply.py`**: applies a provider's own dictionary against a
  real `ubx sdk gen --list-undescribed` gap dump (see the script's own
  docstring for the exact prerequisite command), producing one merge-ready
  batch file per family, source tagged `ai-dictionary`. Never invents
  text -- a field whose leaf name isn't in the dictionary is reported as
  needing individual authorship (`ai-individual`, written by hand, two-
  search minimum against the real API's own reference docs, same
  discipline as the AWS intros), not guessed at.
- **`gap_fill_merge.py`**: merges a batch (from `gap_fill_apply.py` or
  hand-authored) into `artifacts/<provider>/descriptions.json`, skipping
  (never overwriting) any key already present.

`source=ai-dictionary` and `source=ai-individual` are real, different
provenance -- a dictionary entry is grounded in the concept's own
documented, stable meaning but applied mechanically wherever the field
name matches, without per-occurrence verification that the specific
nested context agrees; an individual entry was verified against that
exact field's own real context. Kept as separate `source` values (not
folded into one `ai`) so a future reviewer can tell which is which.
See each provider's own `manifest.json` `last_migration` note for the
real, current per-family remainder.
