#!/usr/bin/env python3
"""General driver, the real "scale to all six providers" follow-on to
gen_amplify_data_source_pages.py's own one-category proof: generates
Resources/Data sources nested docs pages for every remaining real
service group, across all six providers, from the real, post-UBI-181-
fix `ubx sdk gen --dump-ir` schema dumps.

Real WireType comes from stripping dump-ir's own "data_" dict-key
prefix (UBI-178 piece 4's own real dump-only disambiguator -- see
gen_amplify_data_source_pages.py's own real_wire_type doc comment for
the full account) and matching that directly against the real generated
Go source's own WireType field (scan_go_data below) -- ground truth,
never re-derived from schema.json's own "service"/"localName" fields
directly. That distinction matters: a real, live-found finding this
driver's own first version got wrong is that AWS's (and some Azure)
real on-disk directory convention truncates a multi-word service name
to its own FIRST TOKEN only (confirmed live: "AWS IAM Access Analyzer"'s
own real resource pages live under "aws/access/analyzer-*", not
"aws/access_analyzer/*" -- schema.json's own "service" field is
"access_analyzer", the full name, un-truncated) -- grouping or matching
by schema.json's own raw service field instead of the real scanned
service_dir silently missed hundreds of real, existing groups on the
first attempt. Matching by real WireType (equivalently: real
service_dir straight from the real generated file's own directory)
sidesteps this entirely.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_provider_docs import pascal
from gen_data_source_pages import build_data_source_page
from build_regen_schema import inject_description
from coverage_check import schema_entries_from_corrected, check_gaps, gap_count, print_report
from provenance_check import check_provenance, collect_provenance, schema_provenance_of, write_provenance_record
from extract_idents import scan_py_data
from acquire_descriptions import resolve_descriptions_path as _resolve_descriptions_path
from corpus_index import provider_group, resource_pages_of

DOCS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRATCH_DIR = "/tmp/regen-scratch"  # UBI-137: same directory regen_pages.py's own manifest lives in


def resolve_descriptions_path(provider_key, release_name=None):
    return _resolve_descriptions_path(provider_key, DOCS_ROOT, release_name)

# UBI-199: dump_dir/go_root deliberately do NOT live here. They used to
# (hardcoded /tmp/reconcile2-<provider> scratch paths, decoupled from
# `ubiquex`'s own sdk/providers/.ubx/config), which meant this driver
# could read output generated from a live, unpinned fetch even after the
# config itself was pinned -- nothing forced the two to correspond. Now
# required as real CLI arguments every invocation (matching
# regen_pages.py's own already-established --dump-dir/--go-root shape,
# never a silently-reused default), and check_provenance below refuses
# unless that directory's own PROVENANCE.json confirms the schema was
# genuinely pinned, not just that the ubx-provider-dynamic tool was
# clean. go_dir/schema_name/provider_display/sdk_repo_id are real,
# stable identity, not paths -- unaffected, stay here.
PROVIDERS = {
    "aws": dict(go_dir="aws", schema_name="aws", provider_display="AWS", sdk_repo_id="aws"),
    "azure": dict(go_dir="azure", schema_name="azure", provider_display="Microsoft Azure", sdk_repo_id="azure"),
    "gcp": dict(go_dir="google", schema_name="google", provider_display="Google Cloud", sdk_repo_id="google"),
    "kubernetes": dict(go_dir="kubernetes", schema_name="kubernetes", provider_display="Kubernetes", sdk_repo_id="kubernetes"),
    "github": dict(go_dir="github", schema_name="github", provider_display="GitHub", sdk_repo_id="github"),
    "datadog": dict(go_dir="datadog", schema_name="datadog", provider_display="Datadog", sdk_repo_id="datadog"),
}


def resolve_config_name(text, binding):
    naive = binding + "Config"
    if re.search(r"\btype " + re.escape(naive) + r" struct\b", text):
        return naive
    if re.search(r"\btype " + re.escape(naive) + r"_ struct\b", text):
        return naive + "_"
    return naive


def scan_go_data(root, provider_dir):
    """extract_idents.scan_go's own real pattern, matching
    ubx.DataSourceBinding instead of ubx.ResourceBinding, scoped to the
    real /data/ subtree every data-source-mode file lands under. Keyed
    by the real WireType field -- ground truth. UBI-203: sorted glob +
    a loud refusal on a genuine same-wire collision, matching the fix
    applied to extract_idents.py's own scan_go/scan_py/scan_ts (this
    function was already immune to THAT ticket's specific resource-vs-
    data-source collision, since it only ever matches DataSourceBinding
    files in the first place -- this is the same defense-in-depth
    against glob.glob()'s own undefined order, for the separate,
    narrower case of two data sources sharing one wire)."""
    out = {}
    for f in sorted(glob.glob(root + f"/{provider_dir}/data/**/*.go", recursive=True)):
        text = open(f).read()
        m = re.search(r'WireType:\s*"([^"]+)"', text)
        if not m:
            continue
        wire = m.group(1)
        bm = re.search(r"var (\w+) = ubx\.DataSourceBinding\{", text)
        if not bm:
            continue
        binding = bm.group(1)
        pkg_m = re.search(r"^package (\w+)", text, re.M)
        rel = os.path.relpath(f, root)
        parts = rel.split("/")
        service_dir = parts[2]  # "<provider>/data/<service_dir>/<file>.go"
        local_slug = os.path.splitext(parts[-1])[0]
        if wire in out:
            raise SystemExit(
                f"scan_go_data: {wire!r} claimed by both {out[wire]['file']!r} and {rel!r} -- "
                "two real DataSourceBinding files sharing one WireType, refusing rather than "
                "silently picking one (UBI-203)"
            )
        out[wire] = {
            "file": rel,
            "package": pkg_m.group(1) if pkg_m else None,
            "service_dir": service_dir,
            "local_slug": local_slug,
            "binding": binding,
            "config": resolve_config_name(text, binding),
        }
    return out


def idents_for(local_slug, service_dir, binding, config, nested_fields=None, py_module=None, py_config=None):
    go = {"service_dir": service_dir, "package": service_dir, "binding": binding, "config": config,
          "file": f"{service_dir}/{local_slug}.go"}
    # UBI-209: real, confirmed live -- datadog_case_link's own real Go
    # package directory is "case_" (Go escapes "case" as a reserved
    # switch-statement keyword, mirroring the identical real divergence
    # UBI-211 already found for aws_ssm_maintenance_windows_), but the
    # real published Python AND TypeScript directories are both plain
    # "case" -- neither language reserves it. Reusing the go-scanned
    # service_dir for Python's own primary import path produced a real
    # ModuleNotFoundError, and for TypeScript's own import path a real
    # deno check "module not found" -- the same class of bug UBI-211
    # already fixed for Python's own NESTED-class import specifically;
    # this closes the identical gap for the PRIMARY import path in both
    # languages. The real scanned py_module (built from the real python
    # file's own path, see scan_py_data) is ground truth when available;
    # TypeScript is assumed to agree with Python's own escaping decision
    # here rather than Go's, confirmed true for every real divergence
    # found so far (Go is consistently the one applying reserved-word
    # escaping that Python/TS don't need) -- not verified against a
    # dedicated real TS directory scan, since none exists for data
    # sources the way scan_py_data now does for Python.
    py_service_dir = service_dir
    if py_module:
        parts = py_module.split(".")
        if len(parts) >= 2:
            py_service_dir = parts[-2]
    ts = {"service_dir": py_service_dir, "binding": binding, "file": f"{py_service_dir}/{local_slug}.ts"}
    py = {"service_dir": py_service_dir, "binding": binding, "file": f"{py_service_dir}/{local_slug}.py",
          "nested_fields": nested_fields, "module": py_module,
          # UBI-211: real, confirmed live -- aws_kendra_query_suggestions'
          # own real Config class is genuinely named
          # QuerySuggestionsConfig_ (trailing-underscore-suffixed, a
          # real collision with the SEPARATE aws_kendra_query_suggestions_
          # config data source's own binding, also named
          # QuerySuggestionsConfig at package level) -- the naive
          # `binding + "Config"` guess this replaces silently imported
          # and called the WRONG symbol (a DataSourceBinding instance,
          # not the Config class), a real TypeError at execution.
          "config": py_config if py_config is not None else config}
    return go, ts, py


# UBI-137: provider_group/resource_pages_of moved to corpus_index.py so
# gen_provider_docs.py's own rebuild_provider_nav can share them without
# a circular import (this module already imports FROM gen_provider_docs.py).


def _norm(s):
    return s.replace("_", "").replace("-", "").lower()


def best_matching_group(groups, service_dir, local_slug):
    """Finds every existing service subgroup whose own resource pages
    live under a directory that real-world-matches service_dir, then --
    for the real, live-found case where MORE THAN ONE distinct group
    shares that same directory (AWS's own real "app" directory alone
    holds "AWS App Mesh"/"AWS App Runner"/"AWS AppConfig"/"AWS AppSync",
    four genuinely distinct products, confirmed live) -- picks the one
    whose own resource basenames share the longest leading run of
    "_"-split tokens with local_slug.

    "real-world-matches" is deliberately not plain equality: AWS's own
    real resource-side directory naming (derived from CFN's own
    typeName, a genuinely different real pipeline from the Smithy-
    derived data-source directory naming) does not always agree with a
    data source's own real service_dir for the identical real product --
    confirmed live two distinct ways: "acm_pca" (data) vs "acmpca"
    (resource, underscore dropped entirely) and "account_access" (data)
    vs "account" (resource, truncated to a leading token, the rest
    folded into each resource's own local-name prefix instead). Matching
    on the underscore/hyphen-stripped form, by equality OR either side
    being a leading-prefix of the other, catches both real shapes
    without guessing which one applies per service. Returns
    (group_index, matched_dir_segment) or (None, None)."""
    norm_target = _norm(service_dir)
    candidates = []
    for gi, g in enumerate(groups):
        for p in resource_pages_of(g):
            if not isinstance(p, str):
                continue
            parts = p.split("/")
            if len(parts) < 4:
                continue
            norm_dir = _norm(parts[2])
            if norm_dir == norm_target or norm_target.startswith(norm_dir) or norm_dir.startswith(norm_target):
                candidates.append((gi, norm_dir, parts[3]))
    if not candidates:
        return None, None

    # Prefer the CLOSEST directory match (smallest normalized-length
    # gap to service_dir) before anything else -- a short, generic
    # resource directory like "app" or "ds" is a real, valid prefix of
    # many genuinely unrelated longer service_dir values purely by
    # character overlap; the closest-length match is the one actually
    # naming the same real product, not a coincidental substring hit.
    min_gap = min(abs(len(norm_dir) - len(norm_target)) for _, norm_dir, _ in candidates)
    candidates = [c for c in candidates if abs(len(c[1]) - len(norm_target)) == min_gap]

    seen_groups = {gi for gi, _, _ in candidates}
    if len(seen_groups) == 1:
        return candidates[0][0], service_dir

    local_tokens = local_slug.split("_")

    def score(basename):
        toks = basename.replace("-", "_").split("_")
        n = 0
        for a, b in zip(local_tokens, toks):
            if a != b:
                break
            n += 1
        return n

    best_gi, best_score = None, -1
    for gi, _, basename in candidates:
        s = score(basename)
        if s > best_score:
            best_gi, best_score = gi, s
    return best_gi, service_dir


def main():
    # UBI-199: dump_dir/go_root are real, required, explicit CLI
    # arguments -- matching regen_pages.py's own established
    # --dump-dir/--go-root shape exactly, never a hardcoded scratch
    # default. An operator names a real directory every invocation,
    # consciously, rather than a stale default silently getting reused.
    if len(sys.argv) < 4 or sys.argv[1].startswith("--"):
        sys.exit(
            "usage: gen_all_data_source_pages.py <provider> <dump_dir> <go_root> "
            "[--allow-dirty-provenance] [--allow-unpinned-schema]\n"
            "  dump_dir: the real --dump-ir output directory for <provider> "
            "(a real ubx sdk gen --dump-ir run's own <dir>/<provider>)\n"
            "  go_root:  the real --lang go --out output's own sdk/go directory "
            "for <provider> (<dir>/<provider>/sdk/go)"
        )
    provider_key, dump_dir_path, go_root = sys.argv[1:4]
    allow_dirty_provenance = "--allow-dirty-provenance" in sys.argv[4:]
    allow_unpinned_schema = "--allow-unpinned-schema" in sys.argv[4:]
    cfg = PROVIDERS[provider_key]

    # UBI-197: this batch draws from two SEPARATE real `ubx sdk gen`
    # invocations (--dump-ir for schema.json, --lang go --out for
    # go_root) -- refuses unless both are present, clean, pushed, and
    # name the identical commit, since two individually-clean halves
    # from different commits are not one coherent batch. UBI-199: ALSO
    # refuses unless both confirm the schema itself was genuinely
    # pinned (source/version), not a live schema_url fetch that could
    # have drifted between the two separate invocations even against a
    # clean, pinned tool commit -- the real, confirmed Azure mechanism
    # that produced 908 miscategorized pages the first time.
    go_repo_dir = os.path.dirname(os.path.dirname(go_root))
    prov_pairs = collect_provenance([dump_dir_path, go_repo_dir])
    commit = check_provenance(
        prov_pairs,
        allow_dirty=allow_dirty_provenance,
        allow_unpinned_schema=allow_unpinned_schema,
    )
    schema_source, schema_version = schema_provenance_of(prov_pairs)

    schema_path = os.path.join(dump_dir_path, "schema.json")
    schema = json.load(open(schema_path))
    ds_entries = {k: v for k, v in schema.items() if v.get("namespace") == "data"}

    go_idents = scan_go_data(go_root, cfg["go_dir"])
    # UBI-211: sibling of go_root under the same real multi-lang `ubx sdk
    # gen` output (<dir>/<provider>/sdk/{go,python,typescript}) -- the
    # same layout build_resource_idents already relies on in ubi208_regen.py.
    py_root = os.path.join(os.path.dirname(go_root), "python")
    py_data_idents = scan_py_data(py_root, cfg["schema_name"])

    docs_json_path = os.path.join(DOCS_ROOT, "docs.json")
    doc = json.load(open(docs_json_path))
    groups = provider_group(doc, provider_key)

    # Data-source-specific intro/description artifact entries -- keyed
    # data_<wire>, never the bare wire, because most providers' data
    # sources share their resource's own literal wire type (confirmed
    # live: 687/690 Azure, 44/46 AWS, 42/48 GitHub exact-path matches
    # ARE the identical wire, not just a same-shaped one -- Kubernetes'
    # 68/68 is the extreme case, not the exception). The bare-wire key
    # already belongs to that resource's own real intro/description;
    # writing data-source content under it would silently overwrite or
    # collide with real, already-published resource content instead of
    # adding new, separate content.
    intros_path = os.path.join(DOCS_ROOT, "artifacts", provider_key, "intros.json")
    intros = json.load(open(intros_path)) if os.path.exists(intros_path) else {}
    desc_path = resolve_descriptions_path(provider_key, cfg["sdk_repo_id"])
    desc_raw = json.load(open(desc_path)) if os.path.exists(desc_path) else {}
    desc_by_key = {k: v for k, v in desc_raw.items() if k.startswith("data_")}

    # dump-ir's own dict key, "data_" stripped, IS the real WireType --
    # verified live against the real generated Go source (this driver's
    # own doc comment). Build (wire -> meta) directly from that, no
    # per-entry re-derivation.
    by_wire = {}
    for k, meta in ds_entries.items():
        wire = k[len("data_"):] if k.startswith("data_") else k
        by_wire[wire] = meta

    written = 0
    skipped_no_ident = []
    skipped_no_group = []
    new_pages_by_group = {}
    written_records = {}  # UBI-187: wire -> meta for every page actually written this run
    wire_to_page = {}  # UBI-137: data_<wire> -> real page path, mirrors regen_pages.py's own manifest

    for wire, ident in sorted(go_idents.items()):
        meta = by_wire.get(wire)
        if meta is None:
            skipped_no_ident.append(wire)
            continue

        gi, matched_dir = best_matching_group(groups, ident["service_dir"], ident["local_slug"])

        local = meta["localName"]
        fields = meta["ir"]["Fields"]
        data_key = f"data_{wire}"
        inject_description(fields, data_key, desc_by_key)
        slug = ident["local_slug"].replace("_", "-")
        # UBI-211: py_module comes from the real SCANNED python file path
        # (scan_py_data), not reconstructed from the go-scanned
        # local_slug -- the two languages' own codegen make independent
        # collision-avoidance naming decisions (real, confirmed live:
        # aws_ssm_maintenance_windows's own real Go file is
        # maintenance_windows_.go, trailing-underscore-suffixed for a Go-
        # side collision, while the real published Python file is
        # maintenance_windows.py, no suffix at all -- reusing the go-side
        # name for the python import path is a real, wrong guess).
        py_data_ident = py_data_idents.get(wire, {})
        nested_fields = py_data_ident.get("nested_fields")
        py_module = py_data_ident.get("module")
        py_config = py_data_ident.get("config")
        go, ts, py = idents_for(
            ident["local_slug"], ident["service_dir"], ident["binding"], ident["config"],
            nested_fields=nested_fields, py_module=py_module, py_config=py_config,
        )
        page = build_data_source_page(
            wire=wire, service=meta["service"], local=local, slug=slug,
            fields=fields, go=go, ts=ts, py=py,
            provider=provider_key, schema_name=cfg["schema_name"],
            provider_display=cfg["provider_display"], stack_name="example",
            sdk_repo_id=cfg["sdk_repo_id"], intro_text=intros.get(data_key),
        )
        out_dir = os.path.join(DOCS_ROOT, "resource-reference", provider_key, "data", ident["service_dir"])
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{slug}.mdx")
        with open(out_path, "w") as f:
            f.write(page)
        written += 1
        written_records[wire] = meta
        wire_to_page[data_key] = os.path.relpath(out_path, DOCS_ROOT)

        # Orphans (no sibling Resources group to nest under) were
        # already placed into docs.json on their own, standalone group
        # by UBI-189's separate placement pass (8ae6f8ae) -- this
        # driver only needs to refresh their real page CONTENT at their
        # real, already-existing path, never touch their nav placement.
        if gi is None:
            skipped_no_group.append(wire)
            continue
        new_pages_by_group.setdefault(gi, []).append(
            f"resource-reference/{provider_key}/data/{ident['service_dir']}/{slug}"
        )

    for gi, new_pages in new_pages_by_group.items():
        g = groups[gi]
        resources_pages = resource_pages_of(g)
        existing_data = []
        pages = g.get("pages", [])
        if pages and isinstance(pages[0], dict):
            data_sub = next((p for p in pages if p.get("group") == "Data sources"), None)
            if data_sub:
                existing_data = [p for p in data_sub["pages"] if p not in new_pages]
        g["pages"] = [
            {"group": "Resources", "pages": resources_pages},
            {"group": "Data sources", "pages": sorted(set(existing_data) | set(new_pages))},
        ]

    with open(docs_json_path, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")

    print(f"{provider_key}: wrote {written} pages across {len(new_pages_by_group)} groups")
    if skipped_no_group:
        print(f"{provider_key}: {len(skipped_no_group)} orphan data sources written (content only, nav placement untouched, no matching Resources group): {sorted(skipped_no_group)[:30]}{'...' if len(skipped_no_group) > 30 else ''}")
    if skipped_no_ident:
        print(f"{provider_key}: {len(skipped_no_ident)} real Go data sources with no schema.json match: {skipped_no_ident[:20]}{'...' if len(skipped_no_ident) > 20 else ''}")

    # UBI-187: same refusal regen_pages.py/gen_new_provider_pages.py
    # apply -- report/fail rather than let this run silently ship a
    # data source page with no real intro or an undescribed depth-0
    # field. check_disk=False: this run's own pages were just written,
    # so on-disk reachability is trivially satisfied here. No category
    # check applies (schema_entries_from_corrected's is_ds=True makes
    # check_gaps skip it, matching that categories.json is
    # resource-only -- data sources always fall to default derivation
    # by design, never a real gap).
    coverage_result = None
    if written_records:
        coverage_entries = schema_entries_from_corrected(written_records, is_ds=True)
        coverage_result = check_gaps(provider_key, coverage_entries, repo_root=DOCS_ROOT, check_disk=False)
        coverage_gaps = gap_count(coverage_result)
        if coverage_gaps:
            print(f"\n{provider_key}: UBI-187 coverage check found {coverage_gaps} gap(s) in this run's own batch:")
            print_report(coverage_result, quiet=False)
            if not os.environ.get("UBX_DOCS_ALLOW_COVERAGE_GAPS"):
                print(f"\n{provider_key}: refusing to finish with an uncovered page in this batch "
                      f"(set UBX_DOCS_ALLOW_COVERAGE_GAPS=1 to override and report only)")
                sys.exit(1)
        else:
            print(f"{provider_key}: UBI-187 coverage check clean for this run's {len(written_records)} data source(s)")

    # UBI-137: mirrors regen_pages.py's own {provider}_regen_result.json --
    # wire_to_page plus this run's own coverage_result, written even when
    # the coverage gate above already exited nonzero (Python only reaches
    # this line if it didn't), so a genuinely clean run still leaves a
    # real manifest a downstream staging step can read without having to
    # recompute the same check a second time.
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    json.dump(
        {"wire_to_page": wire_to_page, "coverage_result": coverage_result},
        open(os.path.join(SCRATCH_DIR, f"{provider_key}_datasource_regen_result.json"), "w"),
        indent=2,
    )

    if written:
        prov_path = write_provenance_record(
            DOCS_ROOT, provider_key, commit, "data sources",
            extra={"pages_written": written, "schema_source": schema_source, "schema_version": schema_version},
        )
        print(f"{provider_key}: real provenance recorded ({commit}, schema {schema_source}@{schema_version}) -> {prov_path}")


if __name__ == "__main__":
    main()
