# resource-reference-gen

Real, tracked tooling behind every `resource-reference/<provider>/...`
page in this repo -- both the original, sparse mechanical tier (all
~4649 pages currently live) and UBI-144's own newer, richer template
(complete runnable programs, richer real params, a real markdown
scenario), which is being rolled out one real, diverse batch at a time.

This directory used to be an uncommitted scratch script pointed at the
wrong (disconnected) docs directory -- a real gap, closed here. Nothing
in this pipeline invents a field name, a resource relationship, or a
provider convention that isn't drawn from a real, checked source.

## The real pipeline, three steps

### 1. Dump a real provider schema

Run from **within a real `ubiquex` checkout** (this tool imports
`ubiquex`'s own internal `provider`/`sdk/codegen/ir` packages, which
aren't a public, go-gettable module):

```bash
go run /path/to/ubiquex-docs/scripts/resource-reference-gen/dump_schema.go \
    hashicorp/aws 6.54.0 /tmp/schema-dump \
    aws_iam_role aws_sqs_queue aws_s3_bucket
```

Writes one real `<wire_type>.json` per resource, straight from
`sdk/codegen/ir.FromSchema` -- the SAME shared, already-committed IR
translator the real Go/TS/Python bindings codegen uses, never a
hand-typed field list.

### 2. Extract real identifiers from the published bindings

```bash
python3 extract_idents.py aws \
    ~/Ubiquex/ubx-sdk-aws-go ~/Ubiquex/ubx-sdk-aws-py ~/Ubiquex/ubx-sdk-aws-ts \
    /tmp/aws_idents.json
```

Scans the real, already-published SDK bindings repos for each
resource's own real package/binding/config identifier per language --
never guessed or derived from the wire name alone.

### 3. Generate pages

**New pages** (a provider with no resource-reference pages yet at
all), full mechanical tier:

```bash
python3 gen_mechanical_pages.py gcp google GCP \
    github.com/ubiquex/ubx-sdk-google-go ubx-sdk-google-ts 0 \
    /tmp/gcp_schema_all.json /tmp/gcp_idents.json
```

**Existing pages**, UBI-144's own richer template, one resource or a
real batch at a time -- splices ONLY the `## Example` section into
whatever page already exists, never touches Input properties/Output
properties/See also or any other hand-tuned prose on that page:

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
