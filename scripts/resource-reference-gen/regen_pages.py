#!/usr/bin/env python3
"""UBI-175 Phase D: regenerates every non-Compute-domain GCP/Azure
resource page from the completed Phase B/C artifacts, one real
`generate_richer_provider` call per real [dynamic_providers.<family>]
entry (never a single merged call across families -- schema_name has
to be the real, single family name each page's own local_only
`ubx sdk gen --only <name> ...` comment names, and generate_richer_
provider only ever takes one schema_name per call).

The bare "google"/"azure" dynamic_providers entries (GCP Compute /
Azure Compute domain) are NOT in scope here -- both are already live,
correctly regenerated in an earlier Phase 6 session (verified: existing
gcp/compute/*.mdx and the azure_virtual_machine.mdx precedent already
show real intros and the correct published/local_only split). Callers
must exclude them from the family list passed in.

bindings_status is local_only for every page this writes. A real check
against the published ubx-sdk-google clone found 175/656 non-Compute
GCP wire keys present by name -- but the repo is 8 days stale and an
earlier, deeper check in this same session already found real field-
level mismatches even on keys that superficially match (e.g.
google_agent_identity_auth_provider vs. the current correct
google_agentidentity_auth_provider) -- so this does NOT selectively use
"published" for that 26.7%. That finding is reported, not acted on
silently; a real per-resource published split (mirroring the Phase 6
Compute precedent exactly) is left as explicit follow-up work for the
founder to greenlight. ubx-sdk-azure's published content is 100% under
its own separate "azurerm" identity (sdk/go/azurerm/**), zero overlap
with the "azure" dynamic schema_name at all -- so Azure has no such
question to begin with.

Usage:
  python3 regen_pages.py gcp /tmp/gcp-ir-dump /tmp/local-sdk-gcp /tmp/families_gcp.txt
  python3 regen_pages.py azure /tmp/azure-ir-dump /tmp/local-sdk-azure /tmp/families_azure.txt
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_regen_schema import gcp_corrected_key, gcp_corrected_local, inject_description
from extract_idents import scan_go, scan_py, scan_ts
import gen_provider_docs
from gen_provider_docs import generate_richer_provider

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_ROOT = REPO_ROOT
SCRATCH_DIR = "/tmp/regen-scratch"

PROVIDER_DISPLAY = {"gcp": "Google Cloud", "azure": "Microsoft Azure"}


def main():
    provider, dump_dir, sdk_dir, families_file = sys.argv[1:5]
    os.makedirs(SCRATCH_DIR, exist_ok=True)

    here = os.path.dirname(os.path.abspath(__file__))
    desc_path = os.path.join(here, "..", "..", "artifacts", provider, "descriptions.json")
    desc_raw = json.load(open(desc_path))
    desc_by_key = {k: v for k, v in desc_raw.items() if v.get("source") != "docs-vendor"}

    intros_path = os.path.join(here, "..", "..", "artifacts", provider, "intros.json")
    intros_raw = json.load(open(intros_path))
    # intros.json's own real shape is {wire: intro_text}; some entries may
    # instead be {wire: {"text": ...}} depending on which Phase C batch
    # wrote them -- normalize once here rather than at every call site.
    intros = {k: (v if isinstance(v, str) else v.get("text", v.get("intro"))) for k, v in intros_raw.items()}
    intros_by_provider = {provider: intros}
    print(f"loaded {len(intros)} real intros for {provider}")

    families = [l.strip() for l in open(families_file) if l.strip()]
    print(f"{provider}: {len(families)} families to regenerate")

    # Each real per-family [dynamic_providers.<family>] entry is its own
    # local_only `--only <family>` target, but its eventual published
    # home (referenced only in the go.mod replace comment, never claimed
    # as live) is still the SAME single provider-level repo the "google"/
    # "azure" top-level entries above already point at -- not a claim
    # that ubx-sdk-google/-azure actually contain this family today (the
    # published-repo overlap check earlier this session found most of
    # them don't).
    sdk_repo_id = "google" if provider == "gcp" else "azure"
    for family in families:
        gen_provider_docs.REAL_SDK_REPO_ID.setdefault(family, sdk_repo_id)

    total_resources = 0
    total_services = set()
    wire_to_page = {}
    skipped_no_sdk = []
    per_family_counts = {}

    for i, family in enumerate(families, 1):
        schema_path = os.path.join(dump_dir, family, "schema.json")
        if not os.path.exists(schema_path):
            skipped_no_sdk.append((family, "no dump-ir schema.json"))
            continue
        raw_schema = json.load(open(schema_path))

        corrected = {}
        wire_to_raw = {}
        api_name = family[len("google_"):] if provider == "gcp" and family.startswith("google_") else family
        for raw_wire, rec in raw_schema.items():
            fields = rec["ir"]["Fields"]
            if provider == "gcp":
                wire = gcp_corrected_key(raw_wire, api_name)
                local = gcp_corrected_local(rec["localName"], api_name)
            else:
                wire = raw_wire
                local = rec["localName"]
            inject_description(fields, wire, desc_by_key)
            corrected[wire] = {"service": rec["service"], "localName": local, "ir": {"Fields": fields}}
            wire_to_raw[wire] = raw_wire

        family_schema_path = os.path.join(SCRATCH_DIR, f"{family}.schema.json")
        json.dump(corrected, open(family_schema_path, "w"))

        go_root = os.path.join(sdk_dir, family, "sdk", "go")
        py_root = os.path.join(sdk_dir, family, "sdk", "python")
        ts_root = os.path.join(sdk_dir, family, "sdk", "typescript")
        if not os.path.isdir(go_root):
            skipped_no_sdk.append((family, "no local-sdk output"))
            continue
        go = scan_go(go_root, family)
        py = scan_py(py_root, family)
        ts = scan_ts(ts_root, family)

        idents = {}
        for wire, raw_wire in wire_to_raw.items():
            # local_only rendering only reads go["package"]/go["binding"]/
            # go["config"]/go["service_dir"], py["module"]/["binding"]/
            # ["config"], ts["binding"]/["file"]/["service_dir"] -- all of
            # which are keyed by the RAW (uncorrected) wire in scan_go/py/ts
            # output (they read the real WireType string straight out of
            # the generated source, before any GCP doubling-correction).
            idents[wire] = {"go": go.get(raw_wire), "py": py.get(raw_wire), "ts": ts.get(raw_wire)}

        missing = [w for w, v in idents.items() if not v["go"] or not v["py"] or not v["ts"]]
        if missing:
            print(f"  {family}: {len(missing)} wire(s) missing from >=1 language, dropping: {missing}")
            for w in missing:
                del idents[w]
                del corrected[w]

        if not corrected:
            skipped_no_sdk.append((family, "zero resolvable wires after ident match"))
            continue

        family_idents_path = os.path.join(SCRATCH_DIR, f"{family}.idents.json")
        json.dump(idents, open(family_idents_path, "w"))
        json.dump(corrected, open(family_schema_path, "w"))

        n_resources, n_services = generate_richer_provider(
            docs_root=DOCS_ROOT,
            scratch_dir=SCRATCH_DIR,
            provider=provider,
            schema_name=family,
            provider_display=PROVIDER_DISPLAY[provider],
            stack_name="payments",
            schema_path=family_schema_path,
            idents_path=family_idents_path,
            bindings_status="local_only",
            intros_by_provider=intros_by_provider,
        )
        total_resources += n_resources
        per_family_counts[family] = n_resources
        for wire, rec in corrected.items():
            slug = rec["localName"].replace("_", "-")
            wire_to_page[wire] = f"resource-reference/{provider}/{rec['service']}/{slug}.mdx"
            total_services.add(rec["service"])

        if i % 20 == 0 or i == len(families):
            print(f"  [{i}/{len(families)}] {family}: {n_resources} resources ({total_resources} total so far)")

    print(f"\n{provider}: {total_resources} resource pages written across {len(total_services)} service dirs")
    if skipped_no_sdk:
        print(f"{provider}: {len(skipped_no_sdk)} families skipped entirely: {skipped_no_sdk}")

    json.dump(
        {"wire_to_page": wire_to_page, "per_family_counts": per_family_counts, "skipped": skipped_no_sdk},
        open(os.path.join(SCRATCH_DIR, f"{provider}_regen_result.json"), "w"),
        indent=2,
    )


if __name__ == "__main__":
    main()
