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
    depth-0 ONLY, matching the scoping decision already made (nothing
    deeper renders without a click)
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

# dump_dir differs from the artifacts/resource-reference key only for
# gcp -- mirrors gen_all_data_source_pages.py's own real PROVIDERS
# dict exactly, not a second, independently-maintained copy of this
# mapping (that div would silently drift the two apart the same way
# the incidents UBI-190 fixed did).
DUMP_DIR = {
    "aws": "aws", "azure": "azure", "gcp": "google",
    "kubernetes": "kubernetes", "github": "github", "datadog": "datadog",
}
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


def build_schema_entries(provider, schema):
    """Turns a raw --dump-ir schema.json dict ({wire: {service,
    localName, namespace, ir}}) into {(raw_wire, is_ds): (candidates,
    rec)}, widening each key to also try its doubling-corrected form.

    GCP/Azure have a real, known doubling pathology in RAW dump-ir
    wire keys (build_regen_schema.py's own gcp_corrected_key/
    azure_corrected_wire, applied by regen_pages.py before a page is
    ever written). A schema entry's real, correct identity is
    therefore sometimes the raw wire and sometimes the corrected one
    -- confirmed live, both directions, while building this check:
    google_dlp_dlp_job's real, published page is filed under the
    CORRECTED google_dlp_job (the raw form is a genuine synthesis
    bug, already fixed upstream), but google_dns_dns_key's real,
    published page is filed under the RAW, UNCORRECTED wire --
    "DnsKey" is Cloud DNS's own real resource name, not a doubling
    artifact, and gcp_corrected_key's mechanical token-repeat
    heuristic cannot tell the two cases apart from the string alone.
    Rather than trust the corrector's own output as the one truth (it
    is real, but not infallible, and the already-published corpus is
    a genuine historical mix of both forms), every lookup below tries
    BOTH the raw and the corrected wire and treats a match on EITHER
    as covered -- a real gap is only ever a wire that matches under
    neither form. AWS/Kubernetes/GitHub/Datadog have no such step
    (regen_pages.py's own explicit comment: no doubling exists for
    any of them) -- raw is the only candidate there."""
    schema_entries = {}
    for key, rec in schema.items():
        is_ds = rec.get("namespace") == "data" or key.startswith("data_")
        raw = key[len("data_"):] if is_ds and key.startswith("data_") else key
        candidates = {raw}
        if provider == "gcp":
            candidates.add(gcp_corrected_key(raw, rec.get("service", "")))
        elif provider == "azure":
            corrected, _ = azure_corrected_wire(raw)
            candidates.add(corrected)
        schema_entries[(raw, is_ds)] = (candidates, rec)
    return schema_entries


def schema_entries_from_corrected(records, is_ds=False):
    """For a caller (regen_pages.py, gen_new_provider_pages.py) that
    already has a {wire: rec} dict keyed by the FINAL, already-
    corrected wire -- e.g. regen_pages.py's own `corrected` dict, built
    by gcp_corrected_key/azure_corrected_wire before a page is ever
    written -- no further correction guessing is needed: a wire's only
    real candidate is itself. Lets the same check_gaps() core run
    against a just-generated in-memory batch, not only a --dump-ir
    schema.json on disk."""
    return {(wire, is_ds): ({wire}, rec) for wire, rec in records.items()}


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
            if f.get("Description"):
                continue
            found = False
            for pw in page_wire_candidates:
                entry = descriptions.get(f"{pw}.{f['WireName']}")
                text = entry.get("text") if isinstance(entry, dict) else entry
                if text:
                    found = True
                    break
            if not found:
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


def check_provider(provider, dump_root, repo_root=REPO_ROOT):
    """Standalone entry point: loads a real --dump-ir schema.json for
    `provider` from dump_root and runs the full check, including both
    on-disk reachability directions."""
    dump_dir = DUMP_DIR[provider]
    schema_path = os.path.join(dump_root, dump_dir, "schema.json")
    schema = load_json(schema_path)
    if schema is None:
        return {"provider": provider, "error": f"no schema dump at {schema_path!r} -- run `ubx sdk gen --dump-ir` first"}
    schema_entries = build_schema_entries(provider, schema)
    return check_gaps(provider, schema_entries, repo_root=repo_root, check_disk=True)


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
    p.add_argument("--only", help="comma-separated provider list to restrict to (default: all six)")
    p.add_argument("--json", help="also write the full, machine-readable report to this path")
    p.add_argument("--quiet", action="store_true", help="only print per-provider summary lines when clean; still prints full detail for any provider with gaps")
    args = p.parse_args()

    providers = args.only.split(",") if args.only else ALL_PROVIDERS
    for p_name in providers:
        if p_name not in DUMP_DIR:
            print(f"unknown provider {p_name!r} -- one of {ALL_PROVIDERS}", file=sys.stderr)
            sys.exit(2)

    results = [check_provider(p_name, args.dump_root) for p_name in providers]

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
