#!/usr/bin/env python3
"""UBI-187: coverage check comparing the current schema dump against
the committed artifacts, per provider. Runs against reality (a real
--dump-ir schema.json and the real, on-disk resource-reference/ tree),
not against any artifact's own self-reported manifest.json summary --
the ticket's own point: the manifest tracks coverage, but nothing runs
it against reality.

Per provider, reports:
  - resources and data sources with no intro entry (artifacts/<p>/intros.json)
  - resources with no categories entry (artifacts/<p>/categories.json),
    falling to default derivation
  - depth-0 fields with no description from any source (either baked
    into the raw schema dump, or artifacts/<p>/descriptions.json) --
    reported at depth-0 ONLY, matching the scoping decision already
    made (nothing deeper renders without a click). UBI-222: a depth-0
    field with no dedicated text of its own is exempt from this,
    though, when it is a pure object-typed wrapper and every one of
    its own real children is itself covered (recursively, at whatever
    depth they live) -- see field_is_covered's own doc comment for the
    precise rule. A wrapper whose real content already lives, fully
    described, on its children needs no separate text to be honest; a
    wrapper with even one undescribed descendant, or a plain scalar
    field, is still reported exactly as before.
  - pages on disk with no corresponding schema entry (the reverse case
    -- a page orphaned by upstream schema shrinkage or a rename)
  - schema entries with no page at all

exclusions.json's real, deliberate skips (skip_descriptions,
skip_page) are honored throughout -- a deliberate skip is not a gap.

Fails loud, never silent: exits 1 if any real gap is found (0 if
clean), so this is safe to wire into CI or a pre-commit generation
step without a human having to read the output to know something's
wrong.

Usage:
  python3 coverage_check.py [--dump-root /tmp/docs-dump] [--only aws,gcp] [--json out.json] [--quiet]

Exit codes:
  0 -- zero gaps found across every provider checked
  1 -- at least one real gap found
  2 -- a real usage/setup error (missing dump, missing artifacts) -- distinct from 1
       so a caller can tell "the check ran and found problems" from "the check
       could not run at all"
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

sys.path.insert(0, HERE)
from build_regen_schema import gcp_corrected_key, gcp_corrected_local, azure_corrected_wire, azure_corrected_local
from gen_provider_docs import is_object_ish, object_fields_of
import providers as providers_registry

# dump_dir differs from the artifacts/resource-reference key only for
# gcp -- read from providers.py's own shared registry (Tier 2), the
# single place this mapping now lives, not a separately-maintained
# copy (that drift is exactly what let DigitalOcean's own onboarding
# silently miss this file for a real turn -- UBI-222).
DUMP_DIR = {k: providers_registry.schema_name_of(k) for k in providers_registry.all_docs_keys()}
ALL_PROVIDERS = list(DUMP_DIR.keys())


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def normalize_intro_value(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v.get("text") or v.get("intro") or ""
    return ""


def read_page_title(path):
    """The real wire type, straight from the page's own frontmatter --
    ground truth, not a guess reconstructed from the filename (a slug
    is lossy: hyphens replace underscores, and some services have real
    local-name collisions a naive reversal can't disambiguate)."""
    with open(path) as fh:
        head = [fh.readline() for _ in range(5)]
    for line in head:
        line = line.rstrip("\n")
        if line.startswith('title: "') and line.endswith('"'):
            return line[len('title: "'):-1]
    return None


def scan_disk_pages(provider, repo_root=REPO_ROOT):
    """Returns {(wire, is_data_source): path} for every real page on
    disk under resource-reference/<provider>/, excluding every
    index.mdx landing page (those never correspond to a schema entry
    by design).

    is_data_source classification is by real path DEPTH, not a bare
    "/data/" substring check -- AWS's own real, confirmed collision
    (AWS::DataZone/DataPipeline/DataBrew/DataSync/DataExchange
    resources live at resource-reference/aws/data/<file>.mdx, ONE
    level shallower than a real data source page at
    resource-reference/aws/data/<service_dir>/<file>.mdx) makes a
    substring check silently misclassify 39 real AWS resources as data
    sources -- found live twice already this project, in two separate
    investigations, before this check ever existed. parts[-3]=="data"
    (four segments after resource-reference/: provider/data/service/
    slug.mdx) is the one, real, depth-exact test -- not "in path"."""
    root = os.path.join(repo_root, "resource-reference", provider)
    out = {}
    for path in glob.glob(os.path.join(root, "**", "*.mdx"), recursive=True):
        if os.path.basename(path) == "index.mdx":
            continue
        rel = os.path.relpath(path, repo_root)
        parts = rel.split(os.sep)
        # parts: ["resource-reference", provider, ...segments..., "slug.mdx"]
        is_ds = len(parts) >= 5 and parts[2] == "data"
        wire = read_page_title(path)
        if wire is None:
            out[(f"<unparseable:{rel}>", is_ds)] = rel
            continue
        out[(wire, is_ds)] = rel
    return out


def depth0_fields(rec):
    return rec.get("ir", {}).get("Fields", []) or []


def field_is_covered(f, pw, path, descriptions):
    """UBI-222: a field counts as covered by its own, dedicated
    description (native to the schema, or a real descriptions.json
    entry under its own exact dotted path -- checked at whatever depth
    it actually lives at, the same convention inject_description()
    itself already uses) OR, for a pure object-typed wrapper with
    neither, by every one of its own real children being covered under
    this same rule, recursively.

    Precise on purpose, per the founder's own correction: a wrapper
    described in its first child's own words is wrong, not merely
    thin -- rebuilding that borrowing was rejected. This only ever
    exempts a wrapper that has genuinely NOTHING of its own to say
    because its real content already lives, fully described, on its
    children -- never a substitute for real text the wrapper itself
    should carry. A wrapper with even one undescribed descendant
    (scalar or object) is still a real, reportable gap. A scalar field
    is only ever covered by its own text -- it has no children to
    borrow coverage from. An object field with zero real children
    (a genuinely empty type) is treated the same as an undescribed
    scalar: nothing here describes it, so it isn't covered."""
    if f.get("Description"):
        return True
    entry = descriptions.get(f"{pw}.{path}")
    text = entry.get("text") if isinstance(entry, dict) else entry
    if text:
        return True
    t = f.get("Type") or {}
    if not is_object_ish(t):
        return False
    children = object_fields_of(t)
    if not children:
        return False
    return all(
        field_is_covered(c, pw, f"{path}.{c['WireName']}", descriptions)
        for c in children
    )


def load_artifacts(provider, repo_root=REPO_ROOT):
    """Loads the four real artifacts/<provider>/*.json files a coverage
    check needs. Shared by the standalone dump-root check and by any
    generator wiring that already has an in-memory schema and just
    needs the artifact side."""
    artifacts_root = os.path.join(repo_root, "artifacts", provider)
    intros_raw = load_json(os.path.join(artifacts_root, "intros.json"), {})
    intros = {k: normalize_intro_value(v) for k, v in intros_raw.items()}
    categories = load_json(os.path.join(artifacts_root, "categories.json"), {"overrides": {}})
    overrides = categories.get("overrides", {})
    descriptions = load_json(os.path.join(artifacts_root, "descriptions.json"), {})
    exclusions = load_json(os.path.join(artifacts_root, "exclusions.json"), {})
    skip_descriptions = set(exclusions.get("skip_descriptions", {}).keys())
    skip_page = set(exclusions.get("skip_page", {}).keys())
    return intros, overrides, descriptions, skip_descriptions, skip_page


def _widen_candidates(provider, wire, rec):
    """UBI-236: the one real place a wire's real candidate identities
    get computed, shared by both callers below instead of being kept
    in step by hand. GCP/Azure have a real, known doubling pathology
    in RAW dump-ir wire keys (build_regen_schema.py's own
    gcp_corrected_key/azure_corrected_wire, applied by regen_pages.py
    before a page is ever written). A schema entry's real, correct
    identity is therefore sometimes the raw wire and sometimes the
    corrected one -- confirmed live, both directions: google_dlp_dlp_job's
    real, published page is filed under the CORRECTED google_dlp_job
    (the raw form is a genuine synthesis bug, already fixed upstream),
    but google_dns_dns_key's real, published page is filed under the
    RAW, UNCORRECTED wire -- "DnsKey" is Cloud DNS's own real resource
    name, not a doubling artifact, and gcp_corrected_key's mechanical
    token-repeat heuristic cannot tell the two cases apart from the
    string alone. Rather than trust the corrector's own output as the
    one truth (it is real, but not infallible, and the already-
    published corpus is a genuine historical mix of both forms), every
    lookup tries BOTH the raw and the corrected wire and treats a
    match on EITHER as covered -- a real gap is only ever a wire that
    matches under neither form.

    Idempotent, so this is safe to call whether `wire` is genuinely
    raw or was already corrected by the caller: applying
    gcp_corrected_key/azure_corrected_wire to a wire that is already
    in corrected form finds no doubling left to collapse and returns
    the same string unchanged, contributing no spurious second
    candidate. AWS/Kubernetes/GitHub/Datadog have no such step
    (regen_pages.py's own explicit comment: no doubling exists for
    any of them) -- raw is the only candidate there."""
    candidates = {wire}
    if provider == "gcp":
        candidates.add(gcp_corrected_key(wire, rec.get("service", "")))
    elif provider == "azure":
        corrected, _ = azure_corrected_wire(wire)
        candidates.add(corrected)
    return candidates


def build_schema_entries(provider, schema):
    """Turns a raw --dump-ir schema.json dict ({wire: {service,
    localName, namespace, ir}}) into {(raw_wire, is_ds): (candidates,
    rec)}, widening each key via _widen_candidates to also try its
    doubling-corrected form. See _widen_candidates's own doc comment
    for why both forms are tried."""
    schema_entries = {}
    for key, rec in schema.items():
        is_ds = rec.get("namespace") == "data" or key.startswith("data_")
        raw = key[len("data_"):] if is_ds and key.startswith("data_") else key
        schema_entries[(raw, is_ds)] = (_widen_candidates(provider, raw, rec), rec)
    return schema_entries


def schema_entries_from_corrected(provider, records, is_ds=False):
    """UBI-236: for a caller (regen_pages.py, gen_all_data_source_pages.py)
    that has a {wire: rec} dict built directly from a real schema dump
    rather than the standalone CLI's own on-disk schema.json --
    widened via the identical _widen_candidates build_schema_entries
    uses, not a separate, narrower single-candidate assumption.

    That narrower assumption used to hold here: this function's own
    original contract was "the caller already corrected `wire`, so it
    is the only real candidate" -- true for regen_pages.py's own
    `all_corrected` dict (built by gcp_corrected_key/azure_corrected_wire
    before a page is ever written), but never true for gen_all_data_
    source_pages.py's own `written_records`, keyed by the RAW wire
    scanned straight from generated Go source (regen_pages.py's own
    doc comment: scan_go/py/ts output is keyed by the raw, uncorrected
    WireType, before any GCP/Azure doubling-correction). Calling the
    single-candidate version of this function against a raw wire meant
    a data source's real artifact entry, filed under whichever of the
    raw/corrected forms the corpus's own history happened to use,
    could go unmatched -- confirmed live: this is what let the
    google_dns_key rename orphan its own page. Now identical for both
    callers, since _widen_candidates is safe to call regardless of
    whether `wire` started raw or already corrected."""
    return {(wire, is_ds): (_widen_candidates(provider, wire, rec), rec) for wire, rec in records.items()}


def check_gaps(provider, schema_entries, repo_root=REPO_ROOT, check_disk=True):
    """The real coverage-comparison core: given schema_entries (see
    build_schema_entries/schema_entries_from_corrected) and this
    provider's real artifacts, reports missing intros/categories/
    depth-0 descriptions, and (when check_disk) the two reverse-
    reachability gaps against the real on-disk page tree. Shared by
    the standalone CLI check and by generator-side wiring that only
    wants to check the batch it just wrote (check_disk=False -- a
    freshly-written page is trivially "on disk", so that check would
    be a no-op noise source there, not a real gap)."""
    intros, overrides, descriptions, skip_descriptions, skip_page = load_artifacts(provider, repo_root)

    def canonical(candidates):
        # Corrected form preferred for display when it differs from
        # raw -- it's the one a fresh regeneration would actually
        # write to, so it's the more useful identity to report a real
        # NEW gap under. Purely cosmetic: matching logic above already
        # tried every candidate equally.
        return sorted(candidates, key=len, reverse=True)[0]

    missing_intro = []
    missing_category = []
    missing_field_desc = []  # (page_wire, field_name)
    total_depth0_fields = 0

    for (raw_wire, is_ds), (candidates, rec) in schema_entries.items():
        display_wire = canonical(candidates)
        page_wire_candidates = {f"data_{c}" if is_ds else c for c in candidates}
        display_page_wire = f"data_{display_wire}" if is_ds else display_wire

        if not any(intros.get(pw, "").strip() for pw in page_wire_candidates):
            missing_intro.append(display_page_wire)

        if not is_ds and not any(c in overrides for c in candidates):
            missing_category.append(display_wire)

        if candidates & skip_descriptions:
            continue
        for f in depth0_fields(rec):
            total_depth0_fields += 1
            covered = any(
                field_is_covered(f, pw, f["WireName"], descriptions)
                for pw in page_wire_candidates
            )
            if not covered:
                missing_field_desc.append(f"{display_page_wire}.{f['WireName']}")

    schema_no_page = []
    pages_no_schema_entry = []
    pages_on_disk = 0
    if check_disk:
        disk_pages = scan_disk_pages(provider, repo_root)
        pages_on_disk = len(disk_pages)
        matched_disk_keys = set()
        for (raw_wire, is_ds), (candidates, rec) in schema_entries.items():
            display_wire = canonical(candidates)
            if raw_wire in skip_page or display_wire in skip_page:
                continue
            hit = next((c for c in candidates if (c, is_ds) in disk_pages), None)
            if hit is None:
                schema_no_page.append(f"data_{display_wire}" if is_ds else display_wire)
            else:
                matched_disk_keys.add((hit, is_ds))
        schema_no_page.sort()
        pages_no_schema_entry = sorted(
            path for key, path in disk_pages.items() if key not in matched_disk_keys
        )

    return {
        "provider": provider,
        "totals": {
            "schema_resources": sum(1 for (_, is_ds) in schema_entries if not is_ds),
            "schema_data_sources": sum(1 for (_, is_ds) in schema_entries if is_ds),
            "depth0_fields": total_depth0_fields,
            "pages_on_disk": pages_on_disk,
        },
        "missing_intro": sorted(missing_intro),
        "missing_category": sorted(missing_category),
        "missing_field_description": sorted(missing_field_desc),
        "pages_with_no_schema_entry": pages_no_schema_entry,
        "schema_entries_with_no_page": schema_no_page,
    }


def check_provider(provider, dump_root, repo_root=REPO_ROOT, check_disk=True):
    """Standalone entry point: loads a real --dump-ir schema.json for
    `provider` from dump_root and runs the full check.

    UBI-240: dump_dir falls back to `provider` itself when the provider
    is not (yet) a real key in providers.py's own registry (DUMP_DIR),
    rather than a hard KeyError -- the registry's own real job is
    reconciling the few genuine name mismatches this org has (gcp's own
    docs key vs. its real "google" repo name), not gatekeeping which
    providers this check can run against at all. A provider whose own
    artifacts live in its own ubx-sdk-<provider> repo (repo_root
    pointed there via --artifacts-root) has no such mismatch by
    construction -- its own dump_dir is always its own name -- so this
    check runs against it with zero registry entry needed, closing the
    exact "unknown provider" failure DigitalOcean's own onboarding hit
    here first (TRAPS.md's own "a hardcoded provider allowlist" entry).
    check_disk defaults True (both reachability directions against the
    real on-disk resource-reference/ page tree) but should be passed
    False for a provider with no such tree at all -- an SDK-repo-only
    target has no Mintlify pages to reconcile against."""
    dump_dir = DUMP_DIR.get(provider, provider)
    schema_path = os.path.join(dump_root, dump_dir, "schema.json")
    schema = load_json(schema_path)
    if schema is None:
        return {"provider": provider, "error": f"no schema dump at {schema_path!r} -- run `ubx sdk gen --dump-ir` first"}
    schema_entries = build_schema_entries(provider, schema)
    return check_gaps(provider, schema_entries, repo_root=repo_root, check_disk=check_disk)


def gap_count(result):
    if "error" in result:
        return None
    return (
        len(result["missing_intro"])
        + len(result["missing_category"])
        + len(result["missing_field_description"])
        + len(result["pages_with_no_schema_entry"])
        + len(result["schema_entries_with_no_page"])
    )


def print_report(result, quiet):
    provider = result["provider"]
    if "error" in result:
        print(f"[{provider}] ERROR: {result['error']}")
        return
    t = result["totals"]
    gaps = gap_count(result)
    status = "clean" if gaps == 0 else f"{gaps} gap(s)"
    print(f"[{provider}] {t['schema_resources']} resources, {t['schema_data_sources']} data sources, "
          f"{t['depth0_fields']} depth-0 fields, {t['pages_on_disk']} pages on disk -- {status}")
    if quiet and gaps == 0:
        return

    def section(label, items, cap=20):
        if not items:
            return
        print(f"  {label}: {len(items)}")
        for item in items[:cap]:
            print(f"    - {item}")
        if len(items) > cap:
            print(f"    ... and {len(items) - cap} more")

    section("missing intro", result["missing_intro"])
    section("missing category (default derivation)", result["missing_category"])
    section("missing depth-0 field description", result["missing_field_description"])
    section("page on disk, no schema entry", result["pages_with_no_schema_entry"])
    section("schema entry, no page", result["schema_entries_with_no_page"])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dump-root", default="/tmp/docs-dump", help="directory holding <dump_dir>/schema.json per provider (ubx sdk gen --dump-ir's own output root)")
    p.add_argument("--only", help="comma-separated provider list to restrict to (default: every real provider)")
    p.add_argument("--ubiquex-config", help="path to a real ubiquex checkout's sdk/providers/.ubx/config -- when given, --only omitted means the real, live provider set (Tier 1), not this file's own Tier-2-only default, and a provider missing its own REGISTRY entry fails loudly rather than silently")
    p.add_argument("--artifacts-root", help="UBI-240: check a provider's own artifacts/<provider>/ directly in a sibling ubx-sdk-<provider> checkout instead of this repo's own artifacts/ -- for a provider whose artifacts live there, not here. Implies --skip-disk-check (an SDK-repo-only target has no resource-reference/ page tree to reconcile against) and skips the registry-membership gate below (a provider need not be a real providers.py key to be checked this way -- see check_provider's own doc comment)")
    p.add_argument("--skip-disk-check", action="store_true", help="skip both on-disk page-reachability checks (page-with-no-schema-entry, schema-entry-with-no-page) -- only meaningful against this repo's own resource-reference/ tree; set automatically by --artifacts-root")
    p.add_argument("--json", help="also write the full, machine-readable report to this path")
    p.add_argument("--quiet", action="store_true", help="only print per-provider summary lines when clean; still prints full detail for any provider with gaps")
    args = p.parse_args()

    if args.artifacts_root and not args.only:
        print("--artifacts-root requires --only (the one real provider that root belongs to -- omitting it would silently check this repo's own default provider set against the wrong root)", file=sys.stderr)
        sys.exit(2)

    repo_root = args.artifacts_root if args.artifacts_root else REPO_ROOT
    check_disk = not (args.skip_disk_check or args.artifacts_root)

    all_providers = providers_registry.all_docs_keys(args.ubiquex_config) if args.ubiquex_config else ALL_PROVIDERS
    providers = args.only.split(",") if args.only else all_providers
    if not args.artifacts_root:
        for p_name in providers:
            if p_name not in DUMP_DIR:
                print(f"unknown provider {p_name!r} -- one of {all_providers}", file=sys.stderr)
                sys.exit(2)

    results = [check_provider(p_name, args.dump_root, repo_root=repo_root, check_disk=check_disk) for p_name in providers]

    for r in results:
        print_report(r, args.quiet)

    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=2)
            f.write("\n")
        print(f"\nfull report written to {args.json}")

    if any("error" in r for r in results):
        sys.exit(2)
    total_gaps = sum(gap_count(r) for r in results)
    print(f"\ntotal gaps across {len(results)} provider(s): {total_gaps}")
    sys.exit(1 if total_gaps > 0 else 0)


if __name__ == "__main__":
    main()
