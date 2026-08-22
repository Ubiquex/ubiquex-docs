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


def _collapse_first_adjacent_repeat(tokens):
    """Finds the leftmost, longest run of tokens that repeats
    immediately after itself (tokens[i:i+N] == tokens[i+N:i+2N]) and
    collapses it to a single occurrence, leaving everything before and
    after untouched. Returns (new_tokens, changed).

    Same root cause as GCP's gcp_corrected_key/gcp_corrected_local
    (ubx-provider-dynamic's own typeName synthesis doubles a name
    segment when a declared family/config key duplicates the real API
    name), found here in a live audit after the founder caught two live
    URLs showing it (azure_azure_kusto_kusto_cluster_principal_
    assignment, azure_analysisservices_analysisservices_analysis_
    services_server) -- Azure never got GCP's correction applied.
    Unlike GCP, the doubling isn't confined to a fixed "prefix+prefix+"
    shape: it shows up in 54 DECLARED FAMILY NAMES (azure_dns_dns,
    azure_paloaltonetworks_paloaltonetworks_cloudngfw, ...) *and*, found
    only by scanning every wire/localName in the full corpus rather than
    trusting the visually-scanned family list, in 5 more families where
    only one specific resource's own trailing segment happens to
    coincide with its family's own trailing token (azure_hdinsight_
    cluster_cluster -> the family's own "cluster" root resource,
    azure_synapse_workspace_workspace, and 3 others) -- a real,
    adjacent-token exact match is the only thing this function looks
    for, so it does not false-fire on same-looking-but-different words
    (digitaltwins_digital_twins_description is left untouched: "digital"
    != "digitaltwins")."""
    n = len(tokens)
    for i in range(n):
        max_block = (n - i) // 2
        for size in range(max_block, 0, -1):
            if tokens[i:i + size] == tokens[i + size:i + 2 * size]:
                return tokens[:i] + tokens[i:i + size] + tokens[i + 2 * size:], True
    return tokens, False


def azure_corrected_wire(raw_wire):
    """Returns (corrected_wire, changed). See
    _collapse_first_adjacent_repeat's own docstring for the general
    rule; azure_azure_kusto_kusto is a confirmed one-off on top of it
    (the only one of 287 declared families with this shape) -- its real
    spec-repo folder is literally named "azure-kusto" (see .ubx/config's
    own schema_url), so the declared family name carries an extra,
    spurious leading "azure" token that is NOT the real API name (the
    real Azure Resource Manager namespace is plain Microsoft.Kusto --
    confirmed because localName never carries an "azure" token at all,
    only ever "kusto_kusto_..."), stripped here before the general
    collapse runs so the result reads azure_kusto_... rather than
    azure_azure_kusto_...."""
    assert raw_wire.startswith("azure_")
    tokens = raw_wire[len("azure_"):].split("_")
    changed = False
    if tokens[:1] == ["azure"]:
        tokens = tokens[1:]
        changed = True
    tokens, collapsed = _collapse_first_adjacent_repeat(tokens)
    return "azure_" + "_".join(tokens), changed or collapsed


def azure_corrected_local(raw_local):
    tokens, changed = _collapse_first_adjacent_repeat(raw_local.split("_"))
    return "_".join(tokens), changed


def azure_corrected_service(raw_service, family):
    # the one real, confirmed service-field bug alongside the wire/local
    # doubling: azure_azure_kusto_kusto's own dump-ir "service" field
    # reads "azure" (the spurious leading token explained above), not
    # the real "kusto" -- every one of the other 61 affected families'
    # own "service" field was already correct and is left untouched.
    if family == "azure_azure_kusto_kusto" and raw_service == "azure":
        return "kusto"
    return raw_service


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
