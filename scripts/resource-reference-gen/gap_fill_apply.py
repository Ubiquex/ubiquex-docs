#!/usr/bin/env python3
"""UBI-175 Phase B: applies common_gcp_fields.py / common_azure_fields.py's
own live-verified field dictionaries to a provider's real
`ubx sdk gen --list-undescribed` gap-field dump, producing merge-ready
{key: {source: "ai-dictionary", text}} batch files -- one per family.

This is a dictionary-application tool ONLY. It never invents text: every
description it writes is a live-verified entry already sitting in
common_gcp_fields.py/common_azure_fields.py, keyed by a field's own leaf
name (its last dotted path segment). A field whose leaf name isn't in the
dictionary is left for individual authorship (source=ai-individual,
written by hand, not by this tool) -- this script reports exactly which
fields those are, per family, rather than guessing at them.

Prerequisite (run from within a real `ubiquex` checkout, `sdk/providers`):

    ubx sdk gen --only <family1,family2,...> --list-undescribed <gap-dir> \
        --out /tmp/unused --lang go

writes one real <gap-dir>/<family>.json gap file per family. For
azure_<rp>_<file> families needing the dynamic-provider binary:
UBX_PROVIDER_DYNAMIC_REPO=<path to a real ubx-provider-dynamic checkout>.

Usage:
  python3 gap_fill_apply.py gcp --gap-dir /tmp/gcp-gaps --out-dir batches_gcp \
      --families google_dlp,google_bigquery
  python3 gap_fill_apply.py azure --gap-dir /tmp/azure-gaps --out-dir batches_azure \
      --families-file azure_targets.txt
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_gcp_fields import COMMON_LEAF, COMMON_LEAF_TYPE_GUARD, JSON_SCHEMA_LEAF, FAMILY_LEAF as GCP_FAMILY_LEAF
from common_azure_fields import ARM_COMMON, ARM_NETWORK


def gcp_corrected_key(raw_wire, api_name):
    # ubx-provider-dynamic's typeName synthesis doubles the API name when a
    # config entry's own key duplicates the discovery doc's own doc.Name
    # field -- e.g. raw google_lustre_lustre_instance corrected to
    # google_lustre_instance. Confirmed against the real, already-migrated
    # descriptions.json before relying on it (see STATE.md UBI-175 Phase A).
    prefix = f"google_{api_name}_{api_name}_"
    if raw_wire.startswith(prefix):
        return f"google_{api_name}_" + raw_wire[len(prefix):]
    return raw_wire


def apply_gcp(family, gap):
    api_name = family[len("google_"):] if family.startswith("google_") else family
    family_dict = GCP_FAMILY_LEAF.get(family, {})
    matched, unmatched = {}, []
    for raw_wire, fields in gap.items():
        wire = gcp_corrected_key(raw_wire, api_name)
        for path, info in fields.items():
            leaf = path.split(".")[-1]
            full_key = f"{wire}.{path}"
            if leaf in COMMON_LEAF:
                guard = COMMON_LEAF_TYPE_GUARD.get(leaf)
                if guard and guard not in info.get("type", ""):
                    unmatched.append(full_key)
                    continue
                matched[full_key] = {"source": "ai-dictionary", "text": COMMON_LEAF[leaf]}
            elif leaf in JSON_SCHEMA_LEAF:
                matched[full_key] = {"source": "ai-dictionary", "text": JSON_SCHEMA_LEAF[leaf]}
            elif leaf in family_dict:
                matched[full_key] = {"source": "ai-dictionary", "text": family_dict[leaf]}
            else:
                unmatched.append(full_key)
    return matched, unmatched


def apply_azure(family, gap):
    # Azure keeps the raw wire type as-is (no doubling correction) -- the
    # founder's own explicit config-expansion decision to defer that
    # cleanup (see manifest.json's own last_migration note, Phase A).
    is_network = family.startswith("azure_network_")
    matched, unmatched = {}, []
    for wire, fields in gap.items():
        for path, info in fields.items():
            leaf = path.split(".")[-1]
            full_key = f"{wire}.{path}"
            if leaf in ARM_COMMON:
                matched[full_key] = {"source": "ai-dictionary", "text": ARM_COMMON[leaf]}
            elif is_network and leaf in ARM_NETWORK:
                matched[full_key] = {"source": "ai-dictionary", "text": ARM_NETWORK[leaf]}
            else:
                unmatched.append(full_key)
    return matched, unmatched


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("provider", choices=["gcp", "azure"])
    p.add_argument("--gap-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--families")
    p.add_argument("--families-file")
    args = p.parse_args()

    families = []
    if args.families:
        families += args.families.split(",")
    if args.families_file:
        families += [l.strip() for l in open(args.families_file) if l.strip()]
    if not families:
        p.error("pass --families or --families-file")

    os.makedirs(args.out_dir, exist_ok=True)
    apply_fn = apply_gcp if args.provider == "gcp" else apply_azure

    total_gap = total_matched = 0
    for family in families:
        gap_path = os.path.join(args.gap_dir, f"{family}.json")
        if not os.path.isfile(gap_path):
            print(f"{family}: NO GAP FILE at {gap_path}")
            continue
        gap = json.load(open(gap_path))
        matched, unmatched = apply_fn(family, gap)
        gap_total = sum(len(v) for v in gap.values())
        with open(os.path.join(args.out_dir, f"{family}.json"), "w") as f:
            json.dump(matched, f, indent=1, sort_keys=True)
            f.write("\n")
        total_gap += gap_total
        total_matched += len(matched)
        print(f"{family}: {gap_total} gap -> {len(matched)} matched, {len(unmatched)} remain (individual authorship needed)")

    if total_gap:
        print(f"\nTOTAL: {total_gap} gap fields across {len(families)} families -> {total_matched} matched ({100*total_matched/total_gap:.1f}%)")


if __name__ == "__main__":
    main()
