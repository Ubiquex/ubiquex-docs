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

bindings_status defaults to local_only ONLY for a wire that has never
had a real page before. UBI-214: this used to be hardcoded local_only
for every page unconditionally -- a real, confirmed data-loss bug, since
it would silently downgrade every one of the 9,623 real pages UBI-196
deliberately, verifiably flipped to "published" back to local_only on
the very next full regen. Fixed via corpus_index.py's own real scan of
the CURRENTLY COMMITTED tree, done once per provider before any page is
written: a wire already carrying a real page keeps that page's own real,
current bindings_status; only a wire with no existing page at all gets
the honest local_only default. The GCP-specific caveat from before this
fix (a real check against the published ubx-sdk-google clone found
175/656 non-Compute GCP wire keys present by name, but the repo was 8
days stale with real field-level mismatches even on keys that
superficially matched) is why this reads the COMMITTED PAGE's own
already-verified status rather than re-deriving "published" from a
fresh SDK-repo scan on every regen -- UBI-196's own verification is
trusted here, not re-litigated.

UBI-214: also reconciles stale duplicate pages -- a wire whose service-
directory derivation changed since its page was first generated (a
real, recurring pattern: azure_corrected_wire's own collapsing, UBI-151's
escape-undo, the appflow/appsync-style collapses a real AWS regen
surfaced) used to get a fresh page at the new path while the old one
stayed published, live in navigation, forever. Reported every run
(corpus_index.py's own wire-identity index makes this free to check);
only actually deleted with --reconcile-stale-paths.

AWS is the third provider (added for the resource-reference/aws split
and CFN-sourced regeneration): a single real [dynamic_providers.aws]
entry (schema_source = "cloudformation") covers all ~1,705 real
AWS::-namespaced resource types via one registry zip, unlike GCP/
Azure's hundreds of per-family discovery-doc/OpenAPI entries -- the
families_file for aws is expected to contain the single literal line
"aws". No wire/local/service correction needed or applied: real,
confirmed live (artifacts/aws/descriptions.json's own keys, e.g.
"aws_access_analyzer_analyzer") -- CFN's own AWS::Service::Resource ->
aws_service_resource naming has neither GCP's per-family doubling nor
Azure's raw-wire-doubling pathology, so the raw wire IS the corrected
wire and descriptions.json/intros.json were authored directly against
it, no aliasing required.

Kubernetes (UBI-176: recovering the 21 alpha/beta/older-major version
siblings a real resourcemap.go collision-guard used to silently drop)
is the fourth provider, and shares AWS's own "no correction needed"
shape exactly: a single real [dynamic_providers.kubernetes] entry, one
literal "kubernetes" line in the families_file, raw wire IS the
corrected wire (Kubernetes' typeNames were never doubled the way GCP's
own dynamic-provider synthesis is), descriptions.json/intros.json
authored directly against it.

DigitalOcean (UBI-222: the runbook's own first provider onboarded end
to end through this exact chain) is the fifth provider, and shares
AWS's/Kubernetes' own "no correction needed" shape exactly: a single
real [dynamic_providers.digitalocean] entry, one literal
"digitalocean" line in the families_file, raw wire IS the corrected
wire (DigitalOcean's own OpenAPI spec has neither GCP's per-family
doubling nor Azure's raw-wire-doubling pathology), descriptions.json/
intros.json authored directly against it.

Usage:
  python3 regen_pages.py gcp /tmp/gcp-ir-dump /tmp/local-sdk-gcp /tmp/families_gcp.txt
  python3 regen_pages.py azure /tmp/azure-ir-dump /tmp/local-sdk-azure /tmp/families_azure.txt
  python3 regen_pages.py aws /tmp/aws-ir-dump /tmp/local-sdk-aws /tmp/families_aws.txt
  python3 regen_pages.py kubernetes /tmp/k8s-ir-dump /tmp/local-sdk-k8s /tmp/families_k8s.txt

  Add --reconcile-stale-paths to any of the above to also delete a
  stale old-path duplicate once its wire's new page is confirmed
  written, updating docs.json nav + redirects (see
  reconcile_stale_paths.py). Without the flag, stale duplicates are
  still detected and reported every run, just never deleted.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_regen_schema import (
    gcp_corrected_key, gcp_corrected_local, inject_description,
    azure_corrected_wire, azure_corrected_local, azure_corrected_service,
)
from extract_idents import scan_go, scan_py, scan_ts
import gen_provider_docs
from gen_provider_docs import generate_richer_provider, rebuild_provider_index, rebuild_provider_nav
from coverage_check import schema_entries_from_corrected, check_gaps, gap_count, print_report
from provenance_check import check_provenance, collect_provenance, schema_provenance_of, write_provenance_record
from corpus_index import scan_provider_corpus
from reconcile_stale_paths import apply_reconciliation
from acquire_descriptions import resolve_descriptions_path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_ROOT = REPO_ROOT
SCRATCH_DIR = "/tmp/regen-scratch"

PROVIDER_DISPLAY = {"gcp": "Google Cloud", "azure": "Microsoft Azure", "aws": "AWS", "kubernetes": "Kubernetes", "digitalocean": "DigitalOcean"}

# The real published SDK repo's own short name (sdk/providers/.ubx/config's
# own "NAMING" rule) -- differs from this docs repo's own internal
# provider key exactly once, for GCP ("gcp" here, "google" the real repo).
SDK_REPO_ID = {"gcp": "google", "azure": "azure", "aws": "aws", "kubernetes": "kubernetes", "digitalocean": "digitalocean"}

# The "already baked directly into the raw IR dump, do not re-inject"
# source tag is "vendor-spec" for every provider as of the docs-vendor/cfn
# rename below -- GCP/Azure/Kubernetes' artifacts used to write
# "docs-vendor"; AWS's descriptions.json (Phase 5) used to write "cfn"
# for the real CloudFormation registry text. Both tags named the exact
# same concept (the vendor's own machine-readable schema description
# field, confirmed live via byte-for-byte comparison against each
# provider's own real dump-ir output -- AWS's checked directly against
# /tmp/aws-ir-dump/aws/schema.json) under two different, provider-
# specific names -- one label now, everywhere. vendor-spec-sourced text
# is already present verbatim in each field's own real Description, so
# re-injecting it would be redundant (inject_description only fills
# empty Description fields, so this is a correctness/clarity match,
# not a behavior-critical one). Kubernetes' own OpenAPI spec carries
# real per-field descriptive text for essentially everything (UBI-176:
# the 21 resources recovered by the alpha/beta version-collision fix
# needed 0/122 fields individually described -- all already
# "vendor-spec", confirmed live against the real dump-ir output).
SKIP_INJECTION_SOURCE = {"gcp": "vendor-spec", "azure": "vendor-spec", "aws": "vendor-spec", "kubernetes": "vendor-spec", "digitalocean": "vendor-spec"}


def main():
    provider, dump_dir, sdk_dir, families_file = sys.argv[1:5]
    reconcile_stale_paths = "--reconcile-stale-paths" in sys.argv[5:]
    os.makedirs(SCRATCH_DIR, exist_ok=True)

    # UBI-214: real, one-time scan of the CURRENTLY COMMITTED corpus,
    # before this run writes anything -- the shared answer both real
    # fixes need: does this wire already have a page, and if so where
    # and in what bindings_status. See corpus_index.py's own doc
    # comment for why this has to run before the write loop, not after.
    wire_index = scan_provider_corpus(DOCS_ROOT, provider)
    print(f"{provider}: indexed {len(wire_index)} real, currently-committed page(s) by wire identity")

    here = os.path.dirname(os.path.abspath(__file__))
    desc_path = resolve_descriptions_path(provider, DOCS_ROOT, SDK_REPO_ID[provider])
    desc_raw = json.load(open(desc_path))
    skip_source = SKIP_INJECTION_SOURCE[provider]
    desc_by_key = {k: v for k, v in desc_raw.items() if v.get("source") != skip_source}

    intros_path = os.path.join(here, "..", "..", "artifacts", provider, "intros.json")
    intros_raw = json.load(open(intros_path))
    # intros.json's own real shape is {wire: intro_text}; some entries may
    # instead be {wire: {"text": ...}} depending on which Phase C batch
    # wrote them -- normalize once here rather than at every call site.
    intros = {k: (v if isinstance(v, str) else v.get("text", v.get("intro"))) for k, v in intros_raw.items()}

    # Azure's intros.json/descriptions.json were authored entirely
    # against the RAW (uncorrected) wire -- Azure never had a doubling
    # correction before this session, so real_intro_for's own lookup
    # (called deep inside generate_richer_provider, keyed by the
    # CORRECTED wire the schema dict now carries) would silently miss
    # every one of the ~282 wires this session's azure_corrected_wire
    # actually changes, falling back to the boilerplate intro. Alias the
    # raw entry onto its corrected key too, for exactly those wires --
    # inject_description (called locally, below) is fixed the same way
    # by injecting under the raw wire directly rather than aliasing.
    if provider == "azure":
        aliased = 0
        for raw_wire in list(intros.keys()):
            corrected_wire, changed = azure_corrected_wire(raw_wire)
            if changed and corrected_wire not in intros:
                intros[corrected_wire] = intros[raw_wire]
                aliased += 1
        print(f"aliased {aliased} azure intros from raw to corrected wire")

    intros_by_provider = {provider: intros}
    print(f"loaded {len(intros)} real intros for {provider}")

    families = [l.strip() for l in open(families_file) if l.strip()]
    print(f"{provider}: {len(families)} families to regenerate")

    # UBI-197: every real family's own dump-ir output AND its own
    # --lang go --out repo directory each carry a real PROVENANCE.json
    # (ubx sdk gen writes it as a sibling of both) -- refuses unless
    # every one found is present, clean, pushed, and the whole batch
    # names one agreed-on commit. A family whose own directory doesn't
    # exist at all is a real, separate "no dump"/"no local-sdk output"
    # gap the per-family loop below already reports (skipped_no_sdk) --
    # not counted here, since a missing directory isn't unclean
    # provenance, it's a different real problem with its own real
    # report.
    # UBI-199: ALSO refuses unless every real directory's own
    # PROVENANCE.json confirms the schema itself was genuinely pinned
    # (source/version), not a live schema_url fetch that could have
    # drifted between two separate ubx sdk gen invocations even against
    # a clean, pinned tool commit -- see provenance_check.py's own
    # updated doc comment for the real, confirmed Azure mechanism this
    # closes.
    allow_dirty_provenance = "--allow-dirty-provenance" in sys.argv[5:]
    allow_unpinned_schema = "--allow-unpinned-schema" in sys.argv[5:]
    provenance_dirs = []
    for family in families:
        for d in (os.path.join(dump_dir, family), os.path.join(sdk_dir, family)):
            if os.path.isdir(d):
                provenance_dirs.append(d)
    prov_pairs = collect_provenance(provenance_dirs)
    commit = check_provenance(prov_pairs, allow_dirty=allow_dirty_provenance, allow_unpinned_schema=allow_unpinned_schema)
    schema_source, schema_version = schema_provenance_of(prov_pairs)

    # Each real per-family [dynamic_providers.<family>] entry is its own
    # local_only `--only <family>` target, but its eventual published
    # home (referenced only in the go.mod replace comment, never claimed
    # as live) is still the SAME single provider-level repo the "google"/
    # "azure" top-level entries above already point at -- not a claim
    # that ubx-sdk-google/-azure actually contain this family today (the
    # published-repo overlap check earlier this session found most of
    # them don't).
    sdk_repo_id = {"gcp": "google", "azure": "azure", "aws": "aws", "kubernetes": "kubernetes", "digitalocean": "digitalocean"}[provider]
    # Real, confirmed live (UBI-189 follow-up): families_file's own Azure
    # entries carry the identical doubling azure_corrected_wire already
    # collapses for wire types (e.g. "azure_advisor_advisor", never a
    # real [dynamic_providers.<name>] section -- `ubx sdk gen --only
    # azure_advisor_advisor` silently matches zero providers, confirmed
    # live against the real CLI, while `--only azure_advisor` matches
    # the real one). schema_name feeds directly into every printed
    # `--only`/import-path string generate_richer_provider renders
    # (gen_provider_docs.py's own go_gen_cmd/go_pkg_import_path/
    # ts_import_path/py_gen_cmd, all schema_name verbatim, never
    # re-derived) -- collapsing here, at the one place a family name
    # enters that rendering, means every future regeneration renders a
    # command a reader can actually copy-paste and run, not just this
    # one already-published corpus.
    def azure_corrected_family(name):
        # Fixed-point, not a single pass: azure_corrected_wire's own
        # kusto one-off (a spurious leading "azure" token on top of the
        # real adjacent-repeat) needs two collapses for a wire
        # (azure_azure_kusto_kusto_cluster -> azure_kusto_kusto_cluster
        # -> azure_kusto_cluster, UBI-189 follow-up's own real, found-
        # live miss from stopping after one pass) -- no real declared
        # family needs a second pass today (verified against all 603
        # real azure_* [dynamic_providers.<name>] entries), but nothing
        # here guarantees a future families_file never repeats the
        # deeper form, and a second pass is a no-op on an
        # already-correct name.
        while True:
            new_name, changed = azure_corrected_wire(name)
            if not changed:
                return name
            name = new_name

    corrected_family_of = {}
    for family in families:
        corrected_family = azure_corrected_family(family) if provider == "azure" else family
        corrected_family_of[family] = corrected_family
        gen_provider_docs.REAL_SDK_REPO_ID.setdefault(corrected_family, sdk_repo_id)

    total_resources = 0
    total_services = set()
    wire_to_page = {}
    skipped_no_sdk = []
    per_family_counts = {}
    renamed_wires = []
    all_corrected = {}  # UBI-187: every wire this run actually regenerates, merged across families
    published_preserved = 0  # UBI-214: wires whose real existing "published" status carried forward
    stale_duplicates = []  # UBI-214: [(old_rel_path, new_rel_path, wire), ...]

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
                service = rec["service"]
                # GCP's descriptions.json was already authored against
                # the corrected key (an established Phase B rule), so
                # injection uses the corrected wire, same as before.
                inject_description(fields, wire, desc_by_key)
            elif provider == "azure":
                wire, wire_changed = azure_corrected_wire(raw_wire)
                local, local_changed = azure_corrected_local(rec["localName"])
                service = azure_corrected_service(rec["service"], family)
                if wire_changed or local_changed:
                    renamed_wires.append((raw_wire, wire))
                # Azure's descriptions.json was authored against the RAW
                # wire (no correction existed before this session) --
                # inject under raw_wire here, matching that, rather than
                # under the newly-corrected wire (which would silently
                # miss every changed entry).
                inject_description(fields, raw_wire, desc_by_key)
            else:
                # AWS/Kubernetes: no wire/local/service doubling exists
                # (confirmed live against artifacts/aws and artifacts/
                # kubernetes' own descriptions.json keys) -- the raw wire
                # straight out of --dump-ir needs no correction function.
                # descriptions.json/intros.json were authored directly
                # against this same raw wire for both.
                wire = raw_wire
                local = rec["localName"]
                service = rec["service"]
                inject_description(fields, raw_wire, desc_by_key)
            corrected[wire] = {"service": service, "localName": local, "ir": {"Fields": fields}}
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

        all_corrected.update(corrected)

        family_idents_path = os.path.join(SCRATCH_DIR, f"{family}.idents.json")
        json.dump(idents, open(family_idents_path, "w"))
        json.dump(corrected, open(family_schema_path, "w"))

        # UBI-214: real per-wire bindings_status -- a wire this batch is
        # about to regenerate that already has a real, currently-
        # committed page keeps that page's own real bindings_status; a
        # wire with no existing page (genuinely new) still gets the
        # honest "local_only" default. See generate_richer_provider's
        # own doc comment for why this is a {wire: status} map rather
        # than the single flat string every other real caller still
        # passes.
        per_wire_bindings_status = {
            wire: wire_index[wire]["bindings_status"]
            for wire in corrected if wire in wire_index
        }
        published_preserved += sum(
            1 for s in per_wire_bindings_status.values() if s == "published"
        )

        n_resources, n_services = generate_richer_provider(
            docs_root=DOCS_ROOT,
            scratch_dir=SCRATCH_DIR,
            provider=provider,
            schema_name=corrected_family_of[family],
            provider_display=PROVIDER_DISPLAY[provider],
            stack_name="example",
            schema_path=family_schema_path,
            idents_path=family_idents_path,
            bindings_status=per_wire_bindings_status,
            intros_by_provider=intros_by_provider,
        )
        total_resources += n_resources
        per_family_counts[family] = n_resources
        for wire, rec in corrected.items():
            slug = rec["localName"].replace("_", "-")
            new_path = f"resource-reference/{provider}/{rec['service']}/{slug}.mdx"
            wire_to_page[wire] = new_path
            total_services.add(rec["service"])
            # UBI-214: this same wire already had a real page, at a
            # DIFFERENT path -- the old one is now stale (this run just
            # wrote the current, correct one). Wire-identity match only
            # (same bar UBI-209 already used for 274 real page moves
            # this session), never content diffing.
            existing = wire_index.get(wire)
            if existing and existing["path"] != new_path:
                stale_duplicates.append((existing["path"], new_path, wire))

        if i % 20 == 0 or i == len(families):
            print(f"  [{i}/{len(families)}] {family}: {n_resources} resources ({total_resources} total so far)")

    print(f"\n{provider}: {total_resources} resource pages written across {len(total_services)} service dirs")
    if skipped_no_sdk:
        print(f"{provider}: {len(skipped_no_sdk)} families skipped entirely: {skipped_no_sdk}")
    if renamed_wires:
        print(f"{provider}: {len(renamed_wires)} wire/local names corrected for doubling")

    # UBI-214: always reported, zero or not -- a report that only speaks
    # when something is wrong reads the same as a report that isn't
    # running, which is exactly the failure mode that let 137 real
    # stale duplicates and the bindings_status default both go unnoticed
    # this long.
    print(f"{provider}: bindings_status preserved as published for {published_preserved} "
          f"already-published wire(s) this run touched")
    print(f"{provider}: {len(stale_duplicates)} stale duplicate page(s) found "
          f"(old path still on disk, same wire now regenerated at a different path)")
    if stale_duplicates:
        for old_p, new_p, wire in stale_duplicates[:20]:
            print(f"  {wire}: {old_p} -> {new_p}")
        if len(stale_duplicates) > 20:
            print(f"  ... and {len(stale_duplicates) - 20} more")
        if reconcile_stale_paths:
            result = apply_reconciliation(DOCS_ROOT, stale_duplicates, write=True)
            print(f"{provider}: reconciled {result['count']} stale duplicate(s), "
                  f"{result['nav_references_updated']} real docs.json nav reference(s) updated, "
                  f"old paths deleted, redirects added")
        else:
            print(f"{provider}: not deleted -- rerun with --reconcile-stale-paths to apply")

    # UBI-190 follow-up: generate_richer_provider itself no longer
    # touches resource-reference/<provider>/index.mdx or any
    # resource-reference/<provider>/<service>/index.mdx (see its own
    # doc comment -- this is the real fix for the GCP-landing-page and
    # google_dlp_job incidents). rebuild_provider_index is always safe
    # to call here, whether families above covers one real family or
    # every one of them: it derives both files from the REAL, current
    # file tree, never from this run's own families list alone, so it
    # can never discard a family this run didn't touch.
    rebuild_provider_index(docs_root=DOCS_ROOT, provider=provider, provider_display=PROVIDER_DISPLAY[provider])

    # UBI-137: same real-file-tree philosophy, for docs.json's own
    # resource-page nav groups -- see rebuild_provider_nav's own doc
    # comment for why nothing did this before. Runs unconditionally,
    # before the coverage gate below: correct and useful on its own for
    # a clean run or a manual/interactive one; an automated caller that
    # goes on to exclude gapped pages afterward (deleting their files)
    # re-runs this same function once more against the corrected tree,
    # which is exactly why this function reads reality instead of
    # trusting its own most recent call.
    docs_json_path = os.path.join(DOCS_ROOT, "docs.json")
    with open(docs_json_path) as f:
        doc = json.load(f)
    rebuild_provider_nav(docs_root=DOCS_ROOT, doc=doc, provider=provider, provider_display=PROVIDER_DISPLAY[provider])
    with open(docs_json_path, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")

    # UBI-187: refuse to let this run silently ship a page with no real
    # intro, no category, or a depth-0 field with no description --
    # exactly the "template text and blank fields" failure mode the
    # ticket names. Checked only against the wires this run itself just
    # regenerated (all_corrected), not the whole provider corpus: a
    # scoped regen has no business being blocked by a pre-existing,
    # already-known gap elsewhere in the provider it didn't touch.
    # check_disk=False because a page this run just wrote is trivially
    # "on disk" -- that check exists for the standalone corpus-wide
    # sweep, not a freshly-generated batch.
    coverage_result = None
    coverage_gaps = 0
    if all_corrected:
        coverage_entries = schema_entries_from_corrected(all_corrected)
        coverage_result = check_gaps(provider, coverage_entries, repo_root=DOCS_ROOT, check_disk=False)
        coverage_gaps = gap_count(coverage_result)

    # UBI-137: the manifest is written BEFORE the refusal below can
    # exit, not after -- real, found-in-review bug in the first version
    # of this fix: sys.exit(1) firing on a real gap meant this file
    # never got written at all on exactly the run a downstream staging
    # step most needs to read it (a clean run never needed the
    # exclusion list in the first place). coverage_result here is what
    # lets that step exclude the right files without recomputing the
    # same check this run already did.
    json.dump(
        {
            "wire_to_page": wire_to_page, "per_family_counts": per_family_counts,
            "skipped": skipped_no_sdk, "renamed_wires": renamed_wires,
            "coverage_result": coverage_result,
        },
        open(os.path.join(SCRATCH_DIR, f"{provider}_regen_result.json"), "w"),
        indent=2,
    )

    if all_corrected:
        if coverage_gaps:
            print(f"\n{provider}: UBI-187 coverage check found {coverage_gaps} gap(s) in this run's own batch:")
            print_report(coverage_result, quiet=False)
            if not os.environ.get("UBX_DOCS_ALLOW_COVERAGE_GAPS"):
                print(f"\n{provider}: refusing to finish with an uncovered page in this batch "
                      f"(set UBX_DOCS_ALLOW_COVERAGE_GAPS=1 to override and report only)")
                sys.exit(1)
        else:
            print(f"{provider}: UBI-187 coverage check clean for this run's {len(all_corrected)} regenerated wire(s)")

    if total_resources:
        prov_path = write_provenance_record(
            DOCS_ROOT, provider, commit, "resource pages",
            extra={"pages_written": total_resources, "families": len(families),
                   "schema_source": schema_source, "schema_version": schema_version},
        )
        print(f"{provider}: real provenance recorded ({commit}, schema {schema_source}@{schema_version}) -> {prov_path}")


if __name__ == "__main__":
    main()
