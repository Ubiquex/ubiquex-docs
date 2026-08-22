#!/usr/bin/env python3
"""UBI-175 Phase C: merges a batch of hand-authored resource-type intros
into artifacts/<provider>/intros.json, skipping (never overwriting) any
key already present. Every intro is written by hand, two-search-verified
against the vendor's own real overview docs -- this script does no
generation of its own, only merging and reporting.

Usage:
  python3 intro_merge.py gcp batch.json [batch2.json ...]
  python3 intro_merge.py azure batch.json [batch2.json ...]
"""
import argparse
import json
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("provider", choices=["gcp", "azure"])
    p.add_argument("batches", nargs="+", help="batch JSON file(s): {wire_type: intro_text}")
    args = p.parse_args()

    path = f"artifacts/{args.provider}/intros.json"
    intros = json.load(open(path))
    before = len(intros)
    added, skipped = 0, 0
    for batch_path in args.batches:
        batch = json.load(open(batch_path))
        for key, text in batch.items():
            if key in intros:
                skipped += 1
                continue
            intros[key] = text
            added += 1

    with open(path, "w") as f:
        json.dump(intros, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"before={before} added={added} skipped(already present)={skipped} after={len(intros)}")


if __name__ == "__main__":
    sys.exit(main())
