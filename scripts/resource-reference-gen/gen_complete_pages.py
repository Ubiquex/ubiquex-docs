#!/usr/bin/env python3
"""CLI entry point for UBI-144's own newer template -- complete,
runnable Go/TS/Python programs, a richer real field slice, a real
markdown scenario -- generated for one or more resources at a time and
SPLICED into each resource's own EXISTING page (only the "## Example"
section is replaced; Input properties/Output properties/See also, and
any other hand-tuned prose on that page, are left untouched). See
README.md for the real, full pipeline this expects to have already
run (schema dump -> extract_idents.py -> this).

Usage:
  python3 gen_complete_pages.py --schema-dir DIR --idents-path FILE \\
      [--docs-root PATH] [--provider aws] [--schema-name aws] \\
      [--provider-display AWS] [--stack-name payments] \\
      <wire_type> [<wire_type> ...]
  python3 gen_complete_pages.py --schema-dir DIR --idents-path FILE \\
      --wires-file wires.txt   # one real wire type per line

Real, deliberate scope, not silently assumed to generalize further:
KNOWN_FAMILY_MARKDOWN (gen_provider_docs.py) only names a real,
established multi-resource scenario for a small set of resource
families -- everything else gets a real, single-resource scenario
mechanically built from the same example fields the Go/TS/Python tabs
show, never an invented resource relationship.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_provider_docs import (
    build_resource_page_complete,
    wrap_markdown,
    pick_richer_example_fields,
    field_literal_with_preamble,
    KNOWN_FAMILY_MARKDOWN,
    render_generic_markdown_scenario,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Real, confirmed per-provider identity of the combined SDK repo
# (UBI-138 -- "ubx-sdk-<X>", one repo per provider, all three
# languages), verified directly against the real GitHub org, NEVER
# reconstructed from schema_name (which is the wire-type prefix / the
# repo's own INTERNAL path segment, not its identity -- diverges from
# this for Azure specifically: schema_name "azurerm", repo id
# "azure"). Every future provider must add a real, confirmed entry
# here before its own richer-template pages can be generated -- no
# inferred/guessed fallback, by design.
REAL_SDK_REPO_ID = {
    "aws": "aws",
    "google": "google",
    "azurerm": "azure",
    "kubernetes": "kubernetes",
}

INTRO_NOTE = "\n\n" + wrap_markdown(
    "Every tab below is a complete, runnable program, not a fragment, "
    "real enough to save and run exactly as shown."
)


def generate_one(wire, docs_root, schema_dir, idents_all, provider, schema_name,
                  provider_display, stack_name):
    schema_path = os.path.join(schema_dir, f"{wire}.json")
    if not os.path.isfile(schema_path):
        return "skip", f"no schema dump at {schema_path}"
    if wire not in idents_all:
        return "skip", "no identifier entry (run extract_idents.py first)"

    if schema_name not in REAL_SDK_REPO_ID:
        return "error", f"no real, confirmed SDK repo id for schema_name {schema_name!r} in REAL_SDK_REPO_ID -- add it (verified against the real GitHub org) before generating"
    sdk_repo_id = REAL_SDK_REPO_ID[schema_name]

    fields = json.load(open(schema_path))
    idents = idents_all[wire]

    go_service_dir = idents["go"]["service_dir"]
    # A real, found-in-review case: a Go package name that collides with
    # a Go keyword/convention ("default", "main") gets a real trailing
    # underscore in the real generated package name/import path
    # (go["service_dir"] == "default_"/"main_") -- but the real docs
    # directory itself was never given that escape, it's just
    # "default"/"main". Stripped ONLY for the doc output path below;
    # go["service_dir"] (used inside build_resource_page_complete for
    # the real Go import path) is untouched, still correctly carries
    # the trailing underscore the real import path needs.
    doc_service_dir = go_service_dir.rstrip("_") or go_service_dir
    go_local = os.path.splitext(os.path.basename(idents["go"]["file"]))[0]
    # UBI-151: the codegen's own _test.go-collision escape (sdk/codegen/
    # templates/go/go.go) appends a trailing "_" to the FILENAME only,
    # for a resource whose real, wire-derived local name ends in "_test"
    # -- the exported Go identifier (go["binding"]) is deliberately left
    # untouched. That trailing "_" is a pure Go-build artifact with no
    # bearing on the resource's own docs identity; undoing it here so
    # the derived slug/intent text still reads "...-test" (matching the
    # real, already-existing mechanical-tier page) instead of a bogus
    # "...-test-" that would never match any real page on disk.
    if go_local.endswith("_test_"):
        go_local = go_local[:-1]
    slug = go_local.replace("_", "-")
    out_path = os.path.join(docs_root, "resource-reference", provider, doc_service_dir, f"{slug}.mdx")
    if not os.path.isfile(out_path):
        return "skip", f"no existing page at {out_path} (run gen_mechanical_pages.py first)"

    example_fields = pick_richer_example_fields(fields)
    go_values_by_name = {}
    for f in example_fields:
        _, val = field_literal_with_preamble(f, "go")
        go_values_by_name[f["WireName"]] = val

    if wire in KNOWN_FAMILY_MARKDOWN:
        primary = wrap_markdown(
            render_generic_markdown_scenario(wire, example_fields, go_values_by_name).replace("\n", " ")
        )
        name_val = go_values_by_name.get("name", '"example"').strip('"')
        companion = wrap_markdown(KNOWN_FAMILY_MARKDOWN[wire](name_val))
        companion_markdown = primary + "\n\n" + companion
    else:
        companion_markdown = render_generic_markdown_scenario(wire, example_fields, go_values_by_name)

    try:
        _, example_section = build_resource_page_complete(
            wire=wire,
            service=go_service_dir,
            local=go_local,
            slug=go_local,
            fields=fields,
            go=idents["go"],
            py=idents["py"],
            ts=idents["ts"],
            provider=provider,
            schema_name=schema_name,
            provider_display=provider_display,
            stack_name=stack_name,
            intent_summary=f"{stack_name} own {go_local.replace('_', ' ')}",
            companion_markdown=companion_markdown,
            sdk_repo_id=sdk_repo_id,
        )
    except Exception as e:
        return "error", str(e)

    original = open(out_path).read()
    marker_start = "## Example\n"
    marker_end = "\n## Input properties"
    if marker_start not in original or marker_end not in original:
        return "error", "page doesn't match the expected splice shape"
    start = original.index(marker_start)
    end = original.index(marker_end)

    before = original[:start]
    after = original[end:]
    if INTRO_NOTE.strip() not in before:
        before = before.rstrip("\n") + INTRO_NOTE + "\n\n"

    new_page = before + example_section + after
    with open(out_path, "w") as fh:
        fh.write(new_page)
    return "ok", out_path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wires", nargs="*", help="real wire types, e.g. aws_iam_role aws_sqs_queue")
    p.add_argument("--wires-file", help="path to a file with one real wire type per line")
    p.add_argument("--schema-dir", required=True, help="dir of real per-resource IR schema JSON dumps (see README.md)")
    p.add_argument("--idents-path", required=True, help="real extract_idents.py output JSON")
    p.add_argument("--docs-root", default=REPO_ROOT, help="real ubiquex-docs checkout root (default: this repo)")
    p.add_argument("--provider", default="aws")
    p.add_argument("--schema-name", default="aws")
    p.add_argument("--provider-display", default="AWS")
    p.add_argument("--stack-name", default="payments")
    args = p.parse_args()

    wires = list(args.wires)
    if args.wires_file:
        wires += [l.strip() for l in open(args.wires_file) if l.strip()]
    if not wires:
        p.error("no wire types given -- pass some as arguments or via --wires-file")

    idents_all = json.load(open(args.idents_path))

    results = []
    for wire in wires:
        status, detail = generate_one(
            wire, args.docs_root, args.schema_dir, idents_all,
            args.provider, args.schema_name, args.provider_display, args.stack_name,
        )
        print(f"{status.upper()} {wire}: {detail}")
        results.append((wire, status, detail))

    ok = [r for r in results if r[1] == "ok"]
    print(f"\n--- {len(ok)}/{len(wires)} generated ---")
    for wire, status, detail in results:
        if status != "ok":
            print(f"  {status}: {wire} -- {detail}")


if __name__ == "__main__":
    main()
