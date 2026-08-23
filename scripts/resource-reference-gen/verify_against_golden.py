#!/usr/bin/env python3
"""UBI-175 Phase 6: the real verification mechanism -- regenerates every
candidate listed in golden/manifest.json, in memory, using the exact
same gen_golden_page.generate() a real regeneration would call, and
diffs the result against the already-committed golden/<provider>/
<slug>.mdx. Any difference is reported and FAILS (nonzero exit) until a
human has reviewed the diff and re-run with --accept to update the
golden file deliberately. This script never regenerates or touches
anything under resource-reference/ -- it only ever reads real schema
dump / idents / intros inputs and compares against golden/.

Independent of the diff itself, every regenerated page (whether it
matched golden or not) is run through a real set of static checks for
the defect classes this ticket named: fragment code examples, missing
or wrong intro, missing AI markers, wrong category placement, em
dashes, boilerplate, malformed frontmatter. See CHECKS_THIS_CANNOT_DO
at the bottom of this file for the real, explicit list of defect
classes this mechanism does NOT catch -- printed every run, not just
documented in a comment nobody reads.

Usage:
  python3 verify_against_golden.py \\
      --schema-dir /tmp/schema-dump \\
      --idents-dir /tmp \\
      --artifacts-root ../../artifacts \\
      [--accept] [--only aws,github]

--idents-dir must contain <schema_name>_idents.json for every provider
in golden/manifest.json (matching this session's own real file names --
azure/datadog/github/kubernetes were extracted from LOCAL generation,
not a published repo; see golden/manifest.json's own bindings_status
and README.md).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_golden_page import generate
from gen_provider_docs import intro_and_description, frontmatter_description_from_intro, eff_flags
from category_resolve import resolve_category

GOLDEN_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(GOLDEN_DIR, "golden", "manifest.json")

EM_DASH = "—"

OLD_BOILERPLATE_RE = re.compile(
    r"^`[a-z0-9_]+` -- real, typed bindings generated directly from$", re.MULTILINE
)

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
FRONTMATTER_LINE_RE = re.compile(r'^(title|description): ".*"$')


def check_frontmatter(page, wire):
    m = FRONTMATTER_RE.match(page)
    if not m:
        return ["frontmatter: no --- ... --- block found at all"]
    problems = []
    lines = m.group(1).split("\n")
    keys_seen = set()
    for line in lines:
        if not FRONTMATTER_LINE_RE.match(line):
            problems.append(f"frontmatter: malformed line: {line!r}")
            continue
        key = line.split(":", 1)[0]
        keys_seen.add(key)
    if "title" not in keys_seen:
        problems.append("frontmatter: missing title")
    if "description" not in keys_seen:
        problems.append("frontmatter: missing description")
    title_line = next((l for l in lines if l.startswith("title:")), "")
    if wire not in title_line:
        problems.append(f"frontmatter: title does not contain real wire name {wire!r}: {title_line!r}")
    return problems


def check_fragment_examples(page):
    problems = []
    if "```go" in page and "func main(" not in page:
        problems.append("Go example: no func main( -- looks like a fragment, not a complete runnable program")
    if "```go" in page and "package main" not in page:
        problems.append("Go example: no package main")
    if "```typescript" in page and "export default stack(" not in page:
        problems.append("TypeScript example: no export default stack( -- looks like a fragment")
    if "```python" in page and 'if __name__ == "__main__":' not in page:
        problems.append("Python example: no if __name__ guard -- looks like a fragment")
    if '<Tab title="Markdown">' not in page:
        problems.append("Markdown tab missing entirely")
    return problems


def check_intro(page, wire, intro_text):
    problems = []
    if OLD_BOILERPLATE_RE.search(page):
        if intro_text:
            problems.append(
                "boilerplate: the old generic 3-line paragraph is present even though a real intro exists -- "
                "intro_text was not actually spliced in"
            )
        # else: real, honest fallback -- not a defect, see CHECKS_THIS_CANNOT_DO
    elif intro_text:
        # UBI-175 Phase 6 fix: body no longer always renders intro_text
        # verbatim in full -- intro_and_description() strips a leading
        # prefix that exactly matches the frontmatter description, to
        # stop that sentence rendering twice (once as Mintlify's own
        # subtitle, once as body's opening line). Check against what
        # the fixed generator actually computes, not the raw intro_text,
        # so this assertion can't silently drift from the real behavior.
        _, body_intro = intro_and_description(intro_text)
        if body_intro not in page:
            problems.append("intro: real intro text from intros.json does not appear in the generated page")
        # regression guard: the found-in-review bug was fm_description's
        # own text appearing a second time as body's own opening line --
        # confirm that specific duplication hasn't come back.
        fm_description = frontmatter_description_from_intro(intro_text)
        if fm_description in page and page.count(fm_description) > 1:
            problems.append(
                "intro: frontmatter description text also appears again in the body -- "
                "the intro is rendering twice"
            )
        if "Real, typed bindings generated directly from" in page:
            problems.append(
                "intro: leftover generic bindings-format sentence still renders alongside a real intro"
            )
    return problems


def check_ai_markers(page, fields):
    def any_ai(fields):
        for f in fields:
            if f.get("DescriptionSource") == "ai-inferred":
                return True
            t = f.get("Type", {})
            obj = t.get("Object")
            elem = t.get("Element")
            inner = obj if obj else (elem.get("Object") if elem else None)
            if inner and any_ai(inner):
                return True
        return False

    problems = []
    if any_ai(fields):
        if "**(AI-inferred)**" not in page:
            problems.append("AI markers: schema has AI-inferred fields but zero (AI-inferred) markers appear on the page")
    # regression guard: the once-per-page <Note> callout was removed in
    # favor of the inline marker alone -- confirm it hasn't come back.
    if "were not sourced from the real provider schema" in page:
        problems.append("AI markers: the once-per-page <Note> callout is back -- should be the inline marker only")
    return problems


def check_properties_split(page, input_fields, output_fields):
    """UBI-175 Phase 6, found-in-review defect: a resource whose real
    schema marks nearly every field both Optional and Computed at once
    (datadog_monitor's own real shape, not a code bug) produced an
    Output properties section that was a pure, redundant subset of
    Input -- same fields, same descriptions, same order, zero new
    information. build_resource_page_complete now collapses to one
    "## Properties" section when Output would add nothing Input doesn't
    already show. Confirms the page's own heading matches that rule,
    computed independently here rather than trusted from the caller."""
    input_names = {f["WireName"] for f in input_fields}
    has_real_split = any(f["WireName"] not in input_names for f in output_fields)
    problems = []
    if has_real_split and "## Output properties" not in page:
        problems.append("properties: Output would add real, distinct fields but no '## Output properties' heading renders")
    if not has_real_split and "## Output properties" in page:
        problems.append(
            "properties: Output adds nothing Input doesn't already show, but a redundant "
            "'## Output properties' section still renders"
        )
    return problems


def check_em_dashes(page):
    return [f"em dash (U+2014) found, {page.count(EM_DASH)} occurrence(s)"] if EM_DASH in page else []


def check_category_override(provider, wire, artifacts_root):
    """Confirms this wire's own category resolves to a real, non-empty
    label via the real three-step resolver (category_resolve.py):
    overrides by exact wire name first, then the resource's derived
    service in services, then the raw vendor-derived label from
    categories.json's own {categories: {wire: label}} map (CFN typeName
    / Discovery Doc title / ARM namespace / Kubernetes API group /
    OpenAPI tag). services/overrides are a purely additive authored
    layer for display names and for the rare case where the vendor's
    own grouping is wrong for a reader -- categories itself is never
    edited by that layer. A wire with no entry at all (e.g. one outside
    the scoped, vendor-field-correlated corpus, like a legacy
    HashiCorp-sourced page) is not an error -- see
    CHECKS_THIS_CANNOT_DO for what this cannot verify."""
    cat_path = os.path.join(artifacts_root, provider, "categories.json")
    if not os.path.exists(cat_path):
        return []
    cats = json.load(open(cat_path))
    if wire not in cats.get("categories", {}):
        return []
    label, _domain, _source = resolve_category(cats, wire)
    if not label:
        return [f"category: {wire!r} resolved to an empty/missing label"]
    return []


def diff_lines(old, new):
    import difflib
    return list(difflib.unified_diff(
        old.splitlines(), new.splitlines(), fromfile="golden (committed)", tofile="regenerated (fresh)", lineterm=""
    ))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--schema-dir", required=True)
    p.add_argument("--idents-dir", required=True, help="directory containing <schema_name>_idents.json per provider")
    p.add_argument("--artifacts-root", required=True, help="path to ubiquex-docs/artifacts")
    p.add_argument("--accept", action="store_true", help="overwrite golden/<provider>/<slug>.mdx with the fresh regeneration -- only after a human has reviewed the diff, never blindly")
    p.add_argument("--only", help="comma-separated provider list to restrict to")
    args = p.parse_args()

    manifest = json.load(open(MANIFEST_PATH))
    candidates = manifest["candidates"]
    if args.only:
        wanted = set(args.only.split(","))
        candidates = [c for c in candidates if c["provider"] in wanted]

    any_fail = False
    for c in candidates:
        provider, schema_name, wire = c["provider"], c["schema_name"], c["wire"]
        idents_path = os.path.join(args.idents_dir, f"{schema_name}_idents.json")
        intros_path = os.path.join(args.artifacts_root, provider, "intros.json")

        print(f"\n=== {provider}/{wire} ===")
        try:
            page, slug, fields, intro_text = generate(
                provider, schema_name, c["provider_display"], wire,
                args.schema_dir, idents_path, intros_path,
                bindings_status=c.get("bindings_status", "published"),
            )
        except SystemExit as e:
            print(f"  GENERATION FAILED: {e}")
            any_fail = True
            continue

        golden_path = os.path.join(GOLDEN_DIR, "golden", provider, f"{slug}.mdx")
        problems = []
        problems += check_frontmatter(page, wire)
        problems += check_fragment_examples(page)
        problems += check_intro(page, wire, intro_text)
        problems += check_ai_markers(page, fields)
        problems += check_em_dashes(page)
        problems += check_category_override(provider, wire, args.artifacts_root)
        input_fields = [f for f in fields if f["Required"] or eff_flags(f)[1]]
        output_fields = [f for f in fields if eff_flags(f)[2]]
        problems += check_properties_split(page, input_fields, output_fields)

        if not os.path.exists(golden_path):
            print(f"  NO GOLDEN FILE YET at {golden_path} (nothing to diff against)")
            any_fail = True
        else:
            golden_text = open(golden_path).read()
            if golden_text == page:
                print("  diff: IDENTICAL to committed golden")
            else:
                any_fail = True
                d = diff_lines(golden_text, page)
                print(f"  diff: DIFFERS from committed golden ({len(d)} diff lines)")
                for line in d[:40]:
                    print("   ", line)
                if len(d) > 40:
                    print(f"    ... {len(d) - 40} more diff lines")
                if args.accept:
                    with open(golden_path, "w") as fh:
                        fh.write(page)
                    print(f"  --accept: wrote {golden_path}")

        if problems:
            any_fail = True
            print(f"  static checks: {len(problems)} problem(s)")
            for pr in problems:
                print("   -", pr)
        else:
            print("  static checks: clean")

    print("\n" + "=" * 70)
    print(CHECKS_THIS_CANNOT_DO)
    sys.exit(1 if any_fail else 0)


CHECKS_THIS_CANNOT_DO = """This mechanism does NOT catch, and should not be assumed to cover:
- Rendered/visual overflow (a wide code block breaking page layout in
  an actual browser). Catching this needs crawl_overflow.js against a
  real `mint dev` instance (see README.md) -- deliberately NOT run here
  per this ticket's own "no per-page browser instances" instruction.
  A text-level diff cannot see CSS layout at all.
- Whether the generated example code actually COMPILES/imports against
  the real SDK (verify_go_blocks.py / verify_py_blocks.py, also not run
  here). gofmt/deno fmt (run inline during generate()) only prove the
  code is syntactically valid Go/TypeScript, not that it type-checks
  against real SDK bindings -- the README's own doc comment on this
  already notes gofmt once missed a real bug for exactly this reason.
- Real docs.json navigation placement. check_category_override only
  confirms a categories.json override entry (if one exists) resolves to
  a real label, not "UNRESOLVED:...". It cannot confirm the page is
  actually wired into docs.json under that category, because none of
  this candidate set has a live page yet -- that check only becomes
  meaningful once a real regeneration adds the page to nav.
- Whether a cross-reference backtick-mentions a resource that has its
  own real page under a DIFFERENT provider, or a resource type that was
  renamed/removed since the intro was written.
- Semantic correctness of vendor-sourced field descriptions. Real,
  found-in-review examples in this candidate set (AWS's own CFN text
  reading "an ASlong group" for "an Auto Scaling group", GCP's own
  Discovery Doc text reading "azone" for "a zone") are faithfully
  reproduced, not detected as errors, because they are genuinely what
  the vendor's own schema says -- this tool checks fidelity to source,
  not correctness of source.
- Content duplication or near-duplication across different pages.
- Anything about resources NOT in golden/manifest.json's own candidate
  list -- six pages, one per provider, prove the mechanism works; they
  do not themselves verify the other ~3,600+ ungenerated pages."""


if __name__ == "__main__":
    main()
