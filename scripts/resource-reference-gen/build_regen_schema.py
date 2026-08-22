#!/usr/bin/env python3
"""UBI-175 Phase D: builds the combined, corrected, description-enriched
schema.json that generate_richer_provider consumes for a full GCP or
Azure page regeneration.

Two real jobs, both grounded in already-established, real precedent:

1. Merges every per-family `--dump-ir` schema.json (one real file per
   [dynamic_providers.<family>] entry) into one combined
   {wire: {service, localName, ir}} dict, applying the SAME wire-key
   doubling correction gap_fill_apply.py's own gcp_corrected_key
   already established for GCP in Phase B (ubx-provider-dynamic's own
   typeName synthesis doubles the API name when a config entry's key
   duplicates the discovery doc's own doc.Name field -- e.g. raw
   google_lustre_lustre_instance -> corrected google_lustre_instance)
   -- extended here to ALSO correct localName the same way, since an
   uncorrected localName would otherwise produce a doubled page path
   (gcp/lustre/lustre-instance.mdx instead of the correct
   gcp/lustre/instance.mdx) even after the wire key itself is fixed.
   Azure keeps the raw wire type and localName as-is, per Phase B's own
   established rule (no doubling pathology found there).

2. Injects real Phase B/C description and intro text directly from
   artifacts/<provider>/descriptions.json into each field's own
   Description/DescriptionSource -- bypassing `ubx sdk gen`'s own
   --descriptions-dir mechanism entirely (which expects one file per
   RAW, uncorrected family wire key, a real but avoidable extra
   indirection) since this script already has the corrected key each
   field needs to look itself up under. Only source != "docs-vendor"
   entries are injected (docs-vendor text already lives natively in
   the dumped IR's own real Description field, sourced straight from
   the wire schema itself -- injecting it again would be redundant,
   never a fix for a real gap). A field that already carries a real,
   non-empty native Description is left untouched -- this only fills
   genuine gaps, never overrides real vendor text, matching
   --descriptions-dir's own real, established fill-only behavior.

Usage:
  python3 build_regen_schema.py gcp /tmp/gcp-ir-dump /tmp/gcp-schema-combined.json
  python3 build_regen_schema.py azure /tmp/azure-ir-dump /tmp/azure-schema-combined.json
"""
import json
import os
import sys


def gcp_corrected_key(raw_wire, api_name):
    prefix = f"google_{api_name}_{api_name}_"
    if raw_wire.startswith(prefix):
        return f"google_{api_name}_" + raw_wire[len(prefix):]
    return raw_wire


def gcp_corrected_local(raw_local, api_name):
    prefix = f"{api_name}_"
    if raw_local.startswith(prefix) and len(raw_local) > len(prefix):
        return raw_local[len(prefix):]
    return raw_local


def inject_description(fields, wire, desc_by_key):
    """Walks fields (a real []ir.Field list, possibly nested via
    Type.Object/Type.Element.Object) and fills any field whose own
    Description is empty from desc_by_key[f"{wire}.{dotted_path}"],
    when a real, non-docs-vendor artifact entry exists for it."""

    def walk(flist, path_prefix):
        for f in flist:
            path = f"{path_prefix}{f['WireName']}"
            if not f.get("Description"):
                entry = desc_by_key.get(f"{wire}.{path}")
                if entry:
                    f["Description"] = entry["text"]
                    f["DescriptionSource"] = "ai-inferred"
            t = f.get("Type") or {}
            obj = t.get("Object")
            if not obj and t.get("Element"):
                obj = t["Element"].get("Object")
            if obj:
                walk(obj, path + ".")

    walk(fields, "")


def main():
    provider, dump_dir, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    here = os.path.dirname(os.path.abspath(__file__))
    desc_path = os.path.join(here, "..", "..", "artifacts", provider, "descriptions.json")
    desc_raw = json.load(open(desc_path))
    desc_by_key = {
        k: v for k, v in desc_raw.items() if v.get("source") != "docs-vendor"
    }
    print(f"loaded {len(desc_by_key)} non-docs-vendor description entries for {provider}")

    combined = {}
    families = sorted(
        d for d in os.listdir(dump_dir) if os.path.isdir(os.path.join(dump_dir, d))
    )
    for family in families:
        schema_path = os.path.join(dump_dir, family, "schema.json")
        if not os.path.exists(schema_path):
            continue
        schema = json.load(open(schema_path))
        if provider == "gcp":
            api_name = family[len("google_"):] if family.startswith("google_") else family
        else:
            api_name = None

        for raw_wire, rec in schema.items():
            service = rec["service"]
            local = rec["localName"]
            fields = rec["ir"]["Fields"]

            if provider == "gcp":
                wire = gcp_corrected_key(raw_wire, api_name)
                local = gcp_corrected_local(local, api_name)
            else:
                wire = raw_wire

            inject_description(fields, wire, desc_by_key)

            if wire in combined:
                # a real, already-known duplicate-key hazard (Phase B's own
                # google_run/bigtableadmin/networkservices finding) -- never
                # silently overwrite, always surface it.
                print(f"WARNING: duplicate wire key {wire!r} (family {family!r}, "
                      f"already present from an earlier family) -- keeping first")
                continue
            combined[wire] = {"service": service, "localName": local, "ir": {"Fields": fields}}

    json.dump(combined, open(out_path, "w"))
    print(f"{provider}: {len(combined)} combined resource types -> {out_path}")


if __name__ == "__main__":
    main()
