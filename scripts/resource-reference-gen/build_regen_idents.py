#!/usr/bin/env python3
"""UBI-175 Phase D: builds a combined idents.json for a local_only
regeneration spanning many [dynamic_providers.<family>] entries, each
with its own real, separate `ubx sdk gen --only <family> --lang X --out
<root>/<family>` output tree (real, per-family `--out` shape -- see
README.md's own --out flag doc: one repo-shaped tree per declared
source, not one merged tree across many `--only` names in a single
run). extract_idents.py's own scan_go/scan_py/scan_ts expect exactly
one such tree per call, so this drives them once per family and merges
the real per-wire results -- never touches or reimplements the actual
scan/regex logic, only the per-family looping and merging around it.

Usage:
  python3 build_regen_idents.py /tmp/local-sdk-gcp /tmp/gcp_local_idents.json google_apigee google_apihub ...
  (family names read from a file with --families-file also supported)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_idents import scan_go, scan_py, scan_ts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sdk_root", help="root containing one <family>/sdk/{go,python,typescript} tree per family")
    p.add_argument("out_path")
    p.add_argument("families", nargs="*")
    p.add_argument("--families-file")
    args = p.parse_args()

    families = list(args.families)
    if args.families_file:
        families += [l.strip() for l in open(args.families_file) if l.strip()]

    combined = {}
    skipped = []
    for family in families:
        go_root = os.path.join(args.sdk_root, family, "sdk", "go")
        py_root = os.path.join(args.sdk_root, family, "sdk", "python")
        ts_root = os.path.join(args.sdk_root, family, "sdk", "typescript")
        if not os.path.isdir(go_root):
            skipped.append(family)
            continue
        go = scan_go(go_root, family)
        py = scan_py(py_root, family)
        ts = scan_ts(ts_root, family)
        wires = set(go) | set(py) | set(ts)
        for w in wires:
            if w in combined:
                print(f"WARNING: duplicate wire {w!r} (family {family!r}) -- keeping first")
                continue
            combined[w] = {"go": go.get(w), "py": py.get(w), "ts": ts.get(w)}

    if skipped:
        print(f"skipped {len(skipped)} families with no generated output: {skipped}")
    json.dump(combined, open(args.out_path, "w"))
    print(f"wrote {len(combined)} combined ident entries -> {args.out_path}")


if __name__ == "__main__":
    main()
