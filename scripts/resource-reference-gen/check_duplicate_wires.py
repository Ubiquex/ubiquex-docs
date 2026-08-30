#!/usr/bin/env python3
"""UBI-214: general, standalone detector for the stale-duplicate-page
finding -- a real title (the same wire) appearing at more than one path
in the CURRENTLY COMMITTED resource-reference/<provider> tree. Confirmed
live: a real full AWS regen produced 137 of these on a single snapshot,
8% of AWS's own 1715-resource corpus, and the old path was still live
in docs.json navigation, not dead content.

Report-only, deliberately -- this tool never decides which of two paths
for the same wire is correct (it has no idents access to re-derive the
canonical path the way regen_pages.py can), it only says a collision
exists. Fixing a REAL collision this finds means running regen_pages.py
with --reconcile-stale-paths for that provider, which does know the
correct path (it just computed it while writing).

Always reports a real count and real per-provider breakdown, including
zero -- a check that only speaks when something is wrong reads the same
as a check that isn't running, the exact failure mode this session hit
more than once (STATE.md's own record of coverage-watch.yml/
golden-page-gate.yml both existing because a silent gap went unnoticed
long enough to need a real incident to surface it).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus_index import all_titles_with_paths

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_ROOT = REPO_ROOT

ALL_PROVIDERS = ["aws", "azure", "gcp", "kubernetes", "github", "datadog", "digitalocean"]


def check_provider(docs_root, provider):
    by_title = all_titles_with_paths(docs_root, provider)
    duplicates = {title: paths for title, paths in by_title.items() if len(paths) > 1}
    return {
        "provider": provider,
        "total_wires": len(by_title),
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
    }


def print_report(result):
    p = result["provider"]
    # UBI-214: always printed, zero or not -- see this file's own module
    # doc comment for why silence is not an acceptable "all clear."
    print(f"{p}: {result['total_wires']} real wire(s) indexed, "
          f"{result['duplicate_count']} duplicate title(s) found")
    for title, paths in sorted(result["duplicates"].items()):
        print(f"  {title}:")
        for path in paths:
            print(f"    {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated provider list to restrict to (default: all six)")
    ap.add_argument("--docs-root", default=DOCS_ROOT)
    args = ap.parse_args()

    providers = args.only.split(",") if args.only else ALL_PROVIDERS
    for p in providers:
        if p not in ALL_PROVIDERS:
            print(f"unknown provider {p!r} -- one of {ALL_PROVIDERS}", file=sys.stderr)
            sys.exit(2)

    results = [check_provider(args.docs_root, p) for p in providers]
    for r in results:
        print_report(r)

    total_dupes = sum(r["duplicate_count"] for r in results)
    total_wires = sum(r["total_wires"] for r in results)
    # UBI-214: the real, always-printed summary line -- this is what a
    # scheduled CI run's own log shows even on a fully clean pass, so
    # "the check ran and found nothing" stays distinguishable from "the
    # check silently stopped running."
    print(f"\ntotal: {total_wires} real wire(s) indexed across {len(results)} "
          f"provider(s), {total_dupes} duplicate title(s) found")

    sys.exit(1 if total_dupes > 0 else 0)


if __name__ == "__main__":
    main()
