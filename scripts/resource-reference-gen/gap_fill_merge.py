#!/usr/bin/env python3
"""Merges gap_fill_apply.py's own batch output (or a hand-authored
individual batch, {key: {source: "ai-individual"|"ai-dictionary", text}})
into a provider's real artifacts/<provider>/descriptions.json, preserving
its existing format (indent=1, sort_keys=True, one trailing newline).
Skips (never overwrites) any key that already exists -- Phase B only ever
fills a real, confirmed gap, never touches docs-vendor or previously
authored ai/ai-individual/ai-dictionary content.

Usage:
  python3 gap_fill_merge.py artifacts/gcp/descriptions.json batches_gcp/*.json
  python3 gap_fill_merge.py artifacts/azure/descriptions.json my_hand_authored_batch.json
"""
import json
import sys

desc_path = sys.argv[1]
batch_paths = sys.argv[2:]
if not batch_paths:
    sys.exit("usage: gap_fill_merge.py <descriptions.json> <batch.json> [<batch.json> ...]")

desc = json.load(open(desc_path))
before = len(desc)
added = skipped = 0
for path in batch_paths:
    batch = json.load(open(path))
    for k, v in batch.items():
        if k in desc:
            skipped += 1
            continue
        desc[k] = v
        added += 1

with open(desc_path, "w") as f:
    json.dump(desc, f, indent=1, sort_keys=True)
    f.write("\n")

print(f"before={before} added={added} skipped(already present)={skipped} after={len(desc)}")
