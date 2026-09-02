#!/usr/bin/env python3
"""UBI-102: exports a real, portable, qualifier-free description corpus
from artifacts/<provider>/descriptions.json -- the raw form both
`ubx sdk gen` (code comments) and this docs pipeline (rendered pages)
can read directly, replacing the two independently-maintained copies
(sdk/providers/descriptions/<provider>.json and this same artifacts
file) that caused UBI-102's own real 49,479-description gap.

Two real, baked-in transforms get reversed here, neither a guess:

1. A qualifier suffix ("Required."/"Optional."/"Optional; if omitted,
   computed by X."/"Computed by X after `ship`.") that field_desc()
   (gen_provider_docs.py) computes fresh and appends at render time --
   confirmed live, empirically, not assumed: sdk/providers/descriptions/
   datadog.json's own entry for datadog_dashboard.default_timeframe.from
   is qualifier-free ("...in epoch milliseconds."), the live, currently
   committed page for that exact field reads "...in epoch milliseconds.
   Optional; if omitted, computed by Datadog." -- appended exactly once,
   at render time, on top of the clean text. This file's own stored
   copy of the same entry already has the qualifier baked in -- a real
   artifact of how `migrate_descriptions.py` populated it (parsing
   already-rendered MDX for datadog/github, capturing whatever
   field_desc() had already produced, not the pre-qualifier original).
   All 437 real overlapping keys between the two files matched exactly
   once this suffix is stripped, zero content drift -- checked, not
   assumed.

2. `normalize_schema_description`'s own MDX-safety HTML-entity escaping
   (`<`/`>`/`{`/`}` to `&lt;`/`&gt;`/`&#123;`/`&#125;`) -- also baked in
   permanently by the same migration, also confirmed live (a real
   comparator field's stored text had `&gt;`/`&lt;` where the sdk-side
   copy had literal `>`/`<`). Reversed here since a code comment should
   show literal characters, not raw HTML entities -- docs' own render
   path re-escapes via the same `normalize_schema_description` call it
   already makes unconditionally, so storing the raw form here changes
   nothing for docs, and fixes it for code comments.

`vendor-spec` entries are excluded by default -- that text is assumed
to already live natively in the schema dump itself (the real provider's
own wire response), so re-exporting it would ordinarily be redundant.
Confirmed true for datadog/github (byte-identical output with or
without them, since ubx-provider-dynamic's own schema translation
already supplies the same text natively, and --descriptions-dir only
ever fills a field the schema left undescribed).

AWS is a real, confirmed exception (UBI-102): a direct --dump-ir check
with --descriptions-dir disabled entirely showed 11,954 of AWS's own
vendor-spec-labeled fields (e.g. aws_dms_replication_instance.kms_key_id)
come back with DescriptionSource "" -- ubx-provider-dynamic's own
cloudformation/smithy translation does not natively carry this text the
way docs' own separate schema dump does. These are not a real gap in
docs (the exact same text is already there, labeled vendor-spec, and
already rendering correctly on pages, since SKIP_INJECTION_SOURCE
already skips injecting it a second time) -- but excluding them from
the raw export would silently regress `ubx sdk gen`'s own generated
code comments the moment sdk/providers/descriptions/aws.json is
retired, from a real, accurate (AI-inferred-labeled) comment down to no
comment at all. --include-vendor-spec keeps them in the raw export for
exactly this reason: harmless where the schema already covers a field
natively (descriptions-dir never overrides a real source), load-bearing
where it doesn't.

Output shape: {key: {"source": ..., "text": <raw, qualifier-free,
unescaped>}} -- same flat key shape (resource.field.path for a
resource, data_resource.field.path for a data source) this repo's own
descriptions.json already uses, so both consumers change only WHERE
they read from, never the shape they parse.

UBI-222: strip_qualifier's own real bug, found live against a real
published corpus, not in review -- a blind trailing-string match has no
way to tell a genuine render-time-duplicate suffix (safe to strip) from
a field's own real content that simply happens to END in one of the
same four exact phrases (never a redundant qualifier at all -- real
prose, coincidentally). Confirmed live: DigitalOcean's own real "IQN
(iSCSI Qualified Name) of the iSCSI target. Required." lost "Required."
this way, even though the field is genuinely Optional+Computed, not
Required, per its own real, current schema -- the AI's own generated
text just happened to end in that exact word. A full cross-provider
recount (STATE.md's own entry has the real numbers) found 9 further
real, confirmed cases the same way, across kubernetes/github/gcp.
AWS/Azure were never at risk -- their own corpora came from a
different, non-MDX-scraping source that never had a render-time
qualifier baked in to begin with.

Fixed by requiring a real, fresh --dump-root (a `ubx sdk gen --dump-ir`
directory for this exact provider) and only stripping a candidate
suffix when it matches that SAME field's own real, current,
schema-derived qualifier -- computed via gen_provider_docs.py's own
qualifier_for, the exact function field_desc() itself calls at render
time, imported directly rather than reimplemented, so the two can never
drift apart again. A field not found in the fresh dump (renamed/removed
since the corpus text was written) is left completely untouched --
refusing to guess, matching this script's own existing discipline
everywhere else.

UBI-240 slice 5: --descriptions-path and --nested-out let this same,
already-tested script serve a migrated provider directly -- point
--descriptions-path at a sibling ubx-sdk-<provider> checkout's own
artifacts/<provider>/descriptions.json, and --nested-out at that same
checkout's own artifacts/<provider>/<provider>.json (the exact
{resource: {relPath: text}} shape --descriptions-dir reads), and the
regen session commits both descriptions.json and <provider>.json
together -- no pin, no separate release, no network fetch at codegen
time. See UBI-102's own comment thread for why the pin never actually
reached a real regen.

Usage:
  python3 export_raw_descriptions.py <provider> <provider-display> --dump-root <dir> [--out PATH]

  <dir> is the real, current generated-resource directory for THIS
  provider specifically (e.g. `ubx sdk gen --only google --dump-ir
  /tmp/dump`'s own `/tmp/dump/google`, not `/tmp/dump` itself) -- the
  caller resolves which real release name a provider's own docs key
  maps to (gcp -> google is the one real mismatch in this org), the
  same way `provider`/`provider_display` are already explicit,
  un-mapped CLI args rather than baked-in lookups.
"""
import argparse
import json
import os

from build_regen_schema import azure_corrected_wire
from gen_provider_docs import qualifier_for

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS_ROOT = os.path.dirname(os.path.dirname(HERE))


def qualifiers_for(provider_display):
    return [
        "Required.",
        f"Optional; if omitted, computed by {provider_display}.",
        "Optional.",
        f"Computed by {provider_display} after `ship`.",
    ]


def unescape_entities(text):
    return (
        text
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&#123;", "{")
        .replace("&#125;", "}")
    )


def strip_qualifier(text, qualifiers, real_qualifier):
    """Strips a trailing qualifier suffix ONLY when it's genuinely THIS
    field's own real, current, schema-derived qualifier (UBI-222) --
    real_qualifier is None when the field wasn't found at all in the
    fresh dump (renamed/removed since this text was written), in which
    case nothing is ever stripped, matching this module's own doc
    comment. A text ending in one of the four exact phrases as real,
    coincidental content (not a captured render-time duplicate) never
    matches its own field's real qualifier by construction -- schema-
    derived requiredness is real and specific, an AI's own word choice
    is not -- so this is a real distinguishing check, not a coin flip."""
    if real_qualifier is None:
        return text
    for q in qualifiers:
        suffix = " " + q
        if text.endswith(suffix) and q == real_qualifier:
            return text[: -len(suffix)]
    return text


def to_raw(text, qualifiers, real_qualifier):
    return unescape_entities(strip_qualifier(text, qualifiers, real_qualifier)).strip()


def build_field_index(dump_root):
    """Walks every real, freshly generated <wire>.json in dump_root (a
    `ubx sdk gen --dump-ir` directory for one specific provider) into a
    flat {"<wire>.<dotted.path>": field} map -- the identical real walk
    build_regen_schema.py's own inject_description already does (depth-
    first through Type.Object/Type.Element.Object), so a lookup here
    means exactly what it means there. Used to answer "what is this
    field's own real, current, schema-derived qualifier" -- never to
    guess at content."""
    field_by_key = {}
    for fn in os.listdir(dump_root):
        if not fn.endswith(".json") or fn == "PROVENANCE.json":
            continue
        wire = fn[:-5]
        fields = json.load(open(os.path.join(dump_root, fn), encoding="utf-8"))
        if not isinstance(fields, list):
            continue

        def walk(flist, prefix):
            for f in flist:
                if "WireName" not in f:
                    continue
                path = f"{prefix}{f['WireName']}"
                field_by_key[f"{wire}.{path}"] = f
                t = f.get("Type") or {}
                obj = t.get("Object")
                if not obj and t.get("Element"):
                    obj = t["Element"].get("Object")
                if obj:
                    walk(obj, path + ".")

        walk(fields, "")
    return field_by_key


def azure_corrected_key(key):
    """Azure's own artifacts/azure/descriptions.json was authored
    directly against the RAW (doubled) wire (regen_pages.py's own doc
    comment) -- "azure_advisor_advisor_..." where the real, corrected
    resource type is "azure_advisor_...". sdk/providers/descriptions/
    azure.json's own keys are already the corrected form (confirmed:
    all 851 of its real fields matched a corrected-key lookup here,
    zero left over). ubx sdk gen's own generated code is keyed by the
    corrected wire too, so the raw export has to apply the same
    correction docs' own regen_pages.py already applies at render time
    (via inject_description's raw_wire aliasing) -- otherwise the pin
    would carry 90k+ real entries that never match anything ubx sdk gen
    actually generates."""
    prefix = "data_" if key.startswith("data_") else ""
    rest = key[len(prefix):]
    res, _, field = rest.partition(".")
    corrected_res, _ = azure_corrected_wire(res)
    corrected_rest = f"{corrected_res}.{field}" if field else corrected_res
    return prefix + corrected_rest


def nested_shape(flat):
    """Reshapes to_raw's own flat {"<resource>.<relPath>": {"source",
    "text"}} output into {resource: {relPath: text}} -- the exact real
    shape ubiquex's own cli/sdkdescribe.go loadCheckedInDescriptions
    reads via --descriptions-dir/<provider>.json (UBI-102's own
    resolveDescriptionsDir does this identical reshape in Go today, for
    a corpus fetched over the network; this is the same transform, for
    a corpus already sitting on local disk post-UBI-240-slice-5
    migration -- one real reshape, applied wherever the corpus happens
    to be). Data-source-keyed entries are dropped, matching
    resolveDescriptionsDir's own real scope limit exactly: codegen-time
    enrichment has only ever covered resources, never data sources."""
    nested = {}
    for key, entry in flat.items():
        if key.startswith("data_"):
            continue
        resource, sep, rel_path = key.partition(".")
        if not sep:
            continue
        nested.setdefault(resource, {})[rel_path] = entry["text"]
    return nested


def export_raw_descriptions(provider, provider_display, dump_root, include_vendor_spec=False, descriptions_path=None):
    desc_path = descriptions_path or os.path.join(DOCS_ROOT, "artifacts", provider, "descriptions.json")
    desc_raw = json.load(open(desc_path, encoding="utf-8"))
    qualifiers = qualifiers_for(provider_display)
    correct_key = azure_corrected_key if provider == "azure" else (lambda k: k)
    field_by_key = build_field_index(dump_root)

    out = {}
    not_found = 0
    for key, entry in desc_raw.items():
        if entry.get("source") == "vendor-spec" and not include_vendor_spec:
            continue
        lookup_key = correct_key(key)
        field = field_by_key.get(lookup_key)
        if field is None:
            not_found += 1
        real_qualifier = qualifier_for(field, provider_display) if field is not None else None
        out[lookup_key] = {"source": entry["source"], "text": to_raw(entry["text"], qualifiers, real_qualifier)}
    if not_found:
        print(f"{provider}: {not_found} real entries had no matching field in --dump-root (renamed/removed since written) -- left completely unstripped")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("provider")
    ap.add_argument("provider_display")
    ap.add_argument("--dump-root", required=True, help="a real, fresh `ubx sdk gen --dump-ir` directory for THIS provider specifically (e.g. .../google, not the parent dump-ir root) -- required so a stripped qualifier can be verified against this same field's own real, current, schema-derived qualifier before being removed (UBI-222)")
    ap.add_argument("--out", default=None, help="output path, default stdout")
    ap.add_argument(
        "--descriptions-path",
        default=None,
        help="path to a provider's own descriptions.json, default artifacts/<provider>/descriptions.json under this repo -- UBI-240 slice 5: pass a sibling ubx-sdk-<provider> checkout's own artifacts/<provider>/descriptions.json once that provider has migrated off this repo's own copy",
    )
    ap.add_argument(
        "--nested-out",
        default=None,
        help="ALSO write the {resource: {relPath: text}} shape ubiquex's own --descriptions-dir/<provider>.json reads directly (UBI-240 slice 5) -- the real replacement for the pin's own resolveDescriptionsDir reshape, run once here instead of once per regen over the network. Data-source entries are dropped (never enriched at codegen time, matching the pin's own existing scope).",
    )
    ap.add_argument(
        "--include-vendor-spec",
        action="store_true",
        help="keep vendor-spec-sourced entries in the export instead of excluding them as redundant with the schema dump -- pass this only when confirmed the target's own ubx-provider-dynamic schema translation does NOT already carry this text natively (AWS, UBI-102)",
    )
    args = ap.parse_args()

    raw = export_raw_descriptions(args.provider, args.provider_display, args.dump_root, args.include_vendor_spec, args.descriptions_path)
    by_prefix = {"resource": 0, "data_source": 0}
    for k in raw:
        by_prefix["data_source" if k.startswith("data_") else "resource"] += 1
    print(
        f"{args.provider}: exported {len(raw)} real, qualifier-free entries "
        f"({by_prefix['resource']} resource, {by_prefix['data_source']} data source)"
    )

    text = json.dumps(raw, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.out}")
    elif not args.nested_out:
        print(text)

    if args.nested_out:
        nested = nested_shape(raw)
        nested_text = json.dumps(nested, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        with open(args.nested_out, "w", encoding="utf-8") as f:
            f.write(nested_text)
        field_count = sum(len(v) for v in nested.values())
        print(f"wrote {args.nested_out} ({len(nested)} resources, {field_count} real fields)")


if __name__ == "__main__":
    main()
