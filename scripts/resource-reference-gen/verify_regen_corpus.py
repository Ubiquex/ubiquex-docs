#!/usr/bin/env python3
"""UBI-175 Phase D: runs verify_against_golden.py's own real static
checks (frontmatter, fragment examples, intro, AI markers, em dashes,
properties split, category override) against every page regen_pages.py
actually wrote to disk -- full-corpus, not a hand-picked sample, since
regen_pages.py already left one corrected schema.json + idents.json
per family in SCRATCH_DIR that this script can read directly rather
than regenerating in memory a second time.

Usage:
  python3 verify_regen_corpus.py gcp /tmp/regen-scratch
  python3 verify_regen_corpus.py azure /tmp/regen-scratch
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_provider_docs import intro_and_description, frontmatter_description_from_intro, eff_flags
from verify_against_golden import (
    check_frontmatter, check_fragment_examples, check_intro, check_ai_markers,
    check_em_dashes, check_properties_split, check_category_override,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    provider, scratch_dir = sys.argv[1], sys.argv[2]
    here = os.path.dirname(os.path.abspath(__file__))
    artifacts_root = os.path.join(here, "..", "..", "artifacts")
    intros = json.load(open(os.path.join(artifacts_root, provider, "intros.json")))

    # SCRATCH_DIR is shared across both providers' regen_pages.py runs
    # (each leaves its own per-family *.schema.json there, never
    # cleaned between runs) -- restrict to families this provider's own
    # regen actually wrote, per its own real result manifest, rather
    # than globbing every leftover file from a prior run of the OTHER
    # provider.
    result = json.load(open(os.path.join(scratch_dir, f"{provider}_regen_result.json")))
    own_families = set(result["per_family_counts"].keys())

    n_pages = 0
    n_failed = 0
    failures = []

    for schema_path in sorted(glob.glob(os.path.join(scratch_dir, "*.schema.json"))):
        family = os.path.basename(schema_path)[: -len(".schema.json")]
        if family not in own_families:
            continue
        schema = json.load(open(schema_path))
        for wire, rec in schema.items():
            service, local, fields = rec["service"], rec["localName"], rec["ir"]["Fields"]
            slug = local.replace("_", "-")
            page_path = os.path.join(REPO_ROOT, "resource-reference", provider, service, f"{slug}.mdx")
            if not os.path.exists(page_path):
                failures.append((family, wire, [f"page not found at {page_path}"]))
                n_failed += 1
                continue
            page = open(page_path).read()
            n_pages += 1

            intro_text = intros.get(wire)
            problems = []
            problems += check_frontmatter(page, wire)
            problems += check_fragment_examples(page)
            problems += check_intro(page, wire, intro_text)
            problems += check_ai_markers(page, fields)
            problems += check_em_dashes(page)
            problems += check_category_override(provider, wire, artifacts_root)
            input_fields = [f for f in fields if f["Required"] or eff_flags(f)[1]]
            output_fields = [f for f in fields if eff_flags(f)[2]]
            problems += check_properties_split(page, input_fields, output_fields)

            if problems:
                failures.append((family, wire, problems))
                n_failed += 1

    print(f"{provider}: {n_pages} pages checked, {n_failed} with >=1 problem")
    for family, wire, problems in failures[:200]:
        print(f"  [{family}] {wire}:")
        for p in problems:
            print(f"    - {p}")
    if len(failures) > 200:
        print(f"  ... {len(failures) - 200} more (truncated)")


if __name__ == "__main__":
    main()
