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

DOCS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROVIDERS = {
    "aws": dict(dump_dir="aws", go_root="/tmp/reconcile2-aws/aws/sdk/go", go_dir="aws",
                schema_name="aws", provider_display="AWS", sdk_repo_id="aws"),
    "azure": dict(dump_dir="azure", go_root="/tmp/reconcile2-azure/azure/sdk/go", go_dir="azure",
                  schema_name="azure", provider_display="Microsoft Azure", sdk_repo_id="azure"),
    "gcp": dict(dump_dir="google", go_root="/tmp/reconcile2-gcp/google/sdk/go", go_dir="google",
                schema_name="google", provider_display="Google Cloud", sdk_repo_id="google"),
    "kubernetes": dict(dump_dir="kubernetes", go_root="/tmp/reconcile2-k8s/kubernetes/sdk/go", go_dir="kubernetes",
                        schema_name="kubernetes", provider_display="Kubernetes", sdk_repo_id="kubernetes"),
    "github": dict(dump_dir="github", go_root="/tmp/reconcile2-github/github/sdk/go", go_dir="github",
                    schema_name="github", provider_display="GitHub", sdk_repo_id="github"),
    "datadog": dict(dump_dir="datadog", go_root="/tmp/reconcile2-datadog/datadog/sdk/go", go_dir="datadog",
                     schema_name="datadog", provider_display="Datadog", sdk_repo_id="datadog"),
}

DUMP_ROOT = "/tmp/docs-dump"


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
    by the real WireType field -- ground truth."""
    out = {}
    for f in glob.glob(root + f"/{provider_dir}/data/**/*.go", recursive=True):
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
        out[wire] = {
            "file": rel,
            "package": pkg_m.group(1) if pkg_m else None,
            "service_dir": service_dir,
            "local_slug": local_slug,
            "binding": binding,
            "config": resolve_config_name(text, binding),
        }
    return out


def idents_for(local_slug, service_dir, binding, config):
    go = {"service_dir": service_dir, "package": service_dir, "binding": binding, "config": config,
          "file": f"{service_dir}/{local_slug}.go"}
    ts = {"service_dir": service_dir, "binding": binding, "file": f"{service_dir}/{local_slug}.ts"}
    py = {"service_dir": service_dir, "binding": binding, "file": f"{service_dir}/{local_slug}.py"}
    return go, ts, py


def provider_group(doc, provider_key):
    tab_names = {
        "aws": "AWS", "azure": "Azure", "gcp": "GCP",
        "kubernetes": "Kubernetes", "github": "GitHub", "datadog": "Datadog",
    }
    target_tab = tab_names[provider_key]
    for t in doc["navigation"]["tabs"]:
        if t.get("tab") != "SDK Reference":
            continue
        for g in t["groups"]:
            if g.get("group") == target_tab:
                return g["pages"]
    raise RuntimeError(f"no {target_tab!r} group found in docs.json")


def resource_pages_of(subgroup):
    """A subgroup's own real, flat resource page list -- whether it's
    still a plain {"group": X, "pages": [str, ...]} (never touched by
    this nesting pattern) or already {"group": X, "pages":
    [{"group": "Resources", ...}, {"group": "Data sources", ...}]} (a
    re-run)."""
    pages = subgroup.get("pages", [])
    if pages and isinstance(pages[0], dict):
        resources_sub = next((p for p in pages if p.get("group") == "Resources"), None)
        return resources_sub["pages"] if resources_sub else []
    return pages


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
    provider_key = sys.argv[1]
    cfg = PROVIDERS[provider_key]

    schema_path = os.path.join(DUMP_ROOT, cfg["dump_dir"], "schema.json")
    schema = json.load(open(schema_path))
    ds_entries = {k: v for k, v in schema.items() if v.get("namespace") == "data"}

    go_idents = scan_go_data(cfg["go_root"], cfg["go_dir"])

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
    desc_path = os.path.join(DOCS_ROOT, "artifacts", provider_key, "descriptions.json")
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

    for wire, ident in sorted(go_idents.items()):
        meta = by_wire.get(wire)
        if meta is None:
            skipped_no_ident.append(wire)
            continue

        gi, matched_dir = best_matching_group(groups, ident["service_dir"], ident["local_slug"])
        if gi is None:
            skipped_no_group.append(wire)
            continue

        local = meta["localName"]
        fields = meta["ir"]["Fields"]
        data_key = f"data_{wire}"
        inject_description(fields, data_key, desc_by_key)
        slug = ident["local_slug"].replace("_", "-")
        go, ts, py = idents_for(ident["local_slug"], ident["service_dir"], ident["binding"], ident["config"])
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
        new_pages_by_group.setdefault(gi, []).append(
            f"resource-reference/{provider_key}/data/{ident['service_dir']}/{slug}"
        )
        written += 1

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
        print(f"{provider_key}: {len(skipped_no_group)} data sources with no matching Resources group: {sorted(skipped_no_group)[:30]}{'...' if len(skipped_no_group) > 30 else ''}")
    if skipped_no_ident:
        print(f"{provider_key}: {len(skipped_no_ident)} real Go data sources with no schema.json match: {skipped_no_ident[:20]}{'...' if len(skipped_no_ident) > 20 else ''}")


if __name__ == "__main__":
    main()
