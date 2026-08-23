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
      [--provider-display AWS] [--stack-name example] \\
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
    resolve_page_path,
    REAL_SDK_REPO_ID,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# REAL_SDK_REPO_ID is defined once, in gen_provider_docs.py -- imported
# above, not redeclared here, since generate_richer_provider (this
# tool's own sibling for onboarding a brand-new provider) needs the
# identical real table and a second, drifting copy is worse than none.

INTRO_NOTE = "\n\n" + wrap_markdown(
    "Every tab below is a complete, runnable program, not a fragment, "
    "real enough to save and run exactly as shown."
)


def generate_one(wire, docs_root, schema_dir, idents_all, provider, schema_name,
                  provider_display, stack_name, bindings_status, add_intro_note=True,
                  sdk_repo_id_override=None, out_path_override=None):
    schema_path = os.path.join(schema_dir, f"{wire}.json")
    if not os.path.isfile(schema_path):
        return "skip", f"no schema dump at {schema_path}"
    if wire not in idents_all:
        return "skip", "no identifier entry (run extract_idents.py first)"

    if sdk_repo_id_override:
        # Azure/GCP declare one [dynamic_providers.<family>] config entry
        # per real resource family -- schema_name here is that family
        # name (e.g. "google_billingbudgets"), which REAL_SDK_REPO_ID
        # was never populated with (it only ever held the bare provider
        # identity). Its own repo id is still the same real, constant
        # per-provider value regardless of family (see
        # gen_provider_docs.py's own REAL_SDK_REPO_ID comment), so the
        # caller passes it directly rather than this function trying to
        # rediscover per-family entries that were never declared.
        sdk_repo_id = sdk_repo_id_override
    elif schema_name not in REAL_SDK_REPO_ID:
        return "error", f"no real, confirmed SDK repo id for schema_name {schema_name!r} in REAL_SDK_REPO_ID -- add it (verified against the real GitHub org) before generating"
    else:
        sdk_repo_id = REAL_SDK_REPO_ID[schema_name]

    fields = json.load(open(schema_path))
    idents = idents_all[wire]

    if out_path_override:
        # GCP/Azure: the go/py/ts identifiers' OWN service_dir/filename
        # still carry whatever raw, possibly-doubled name Discover()
        # produced (the doc-generation-time correction, gcp_corrected_
        # key/_local, was never applied to the generated SDK code
        # itself) -- resolve_page_path's own derivation from those
        # would recompute the WRONG, pre-correction path. The real,
        # already-correct path comes from the wire's own existing page
        # title instead (built by the caller from a real directory
        # scan), and go_local for intent_summary comes from that same
        # real page's own current filename, not from the go file.
        out_path = out_path_override
        go_local = os.path.splitext(os.path.basename(out_path))[0].replace("-", "_")
    else:
        out_path, doc_service_dir, go_local, slug = resolve_page_path(docs_root, provider, idents)
    if not os.path.isfile(out_path):
        return "skip", (
            f"no existing page at {out_path} -- this tool only touches up an "
            "already-generated resource, it cannot onboard a new one; use "
            "gen_new_provider_pages.py for a provider with no pages yet"
        )

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
            service=idents["go"]["service_dir"],
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
            bindings_status=bindings_status,
        )
    except Exception as e:
        return "error", str(e)

    original = open(out_path).read()
    marker_start = "## Example\n"
    # Two real, live page shapes follow "## Example": most resources
    # split "## Input properties" / "## Output properties"; a real
    # minority (every one of a resource's own fields is both readable
    # and writable, so there's nothing to split) instead has a single
    # "## Properties" section. Both are genuine, current templates, not
    # a legacy one to migrate away from -- splice up to whichever one
    # this page actually has.
    end_markers = ["\n## Input properties", "\n## Properties"]
    marker_end = next((m for m in end_markers if m in original), None)
    if marker_start not in original or marker_end is None:
        return "error", "page doesn't match the expected splice shape"
    start = original.index(marker_start)
    end = original.index(marker_end)

    before = original[:start]
    after = original[end:]
    if add_intro_note and INTRO_NOTE.strip() not in before:
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
    p.add_argument("--schema-name", default="aws",
                    help="ignored per-wire when --schema-name-map is given")
    p.add_argument("--schema-name-map",
                    help="path to a real {wire: schema_name} JSON map, for providers (Azure, GCP) "
                         "that declare one config entry per resource family rather than one for "
                         "the whole provider -- each wire's own existing page already names its "
                         "real family in its 'ubx sdk gen --only <family>' comment; that value "
                         "must be preserved exactly, never collapsed to one global --schema-name")
    p.add_argument("--sdk-repo-id",
                    help="required together with --schema-name-map -- the real, constant "
                         "per-provider SDK repo id (e.g. 'google', 'azure') that REAL_SDK_REPO_ID "
                         "was never populated with per-family entries for")
    p.add_argument("--provider-display", default="AWS")
    p.add_argument("--stack-name", default="example")
    p.add_argument("--bindings-status", default="local_only", choices=["local_only", "published"],
                    help="must match the EXISTING page's own real bindings_status (check its own "
                         "'ubx sdk gen --only ...' vs 'jsr:@ubx/...' import comment first) -- "
                         "build_resource_page_complete's own default ('published') silently "
                         "produces the WRONG import style if this doesn't match")
    p.add_argument("--no-intro-note", action="store_true",
                    help="skip inserting INTRO_NOTE ('Every tab below is a complete, runnable "
                         "program...') even when the existing page doesn't have it yet -- for a "
                         "narrowly-scoped splice that must not add unrelated prose")
    p.add_argument("--out-path-map",
                    help="path to a real {wire: existing_mdx_path} JSON map -- for GCP/Azure, "
                         "whose generated SDK code's own service_dir/filename were never "
                         "corrected the way the wire type was, so resolve_page_path's normal "
                         "derivation would compute the wrong, pre-correction path")
    args = p.parse_args()
    if args.schema_name_map and not args.sdk_repo_id:
        p.error("--schema-name-map requires --sdk-repo-id")

    wires = list(args.wires)
    if args.wires_file:
        wires += [l.strip() for l in open(args.wires_file) if l.strip()]
    if not wires:
        p.error("no wire types given -- pass some as arguments or via --wires-file")

    idents_all = json.load(open(args.idents_path))
    schema_name_map = json.load(open(args.schema_name_map)) if args.schema_name_map else {}
    out_path_map = json.load(open(args.out_path_map)) if args.out_path_map else {}

    results = []
    for wire in wires:
        schema_name = schema_name_map.get(wire, args.schema_name)
        status, detail = generate_one(
            wire, args.docs_root, args.schema_dir, idents_all,
            args.provider, schema_name, args.provider_display, args.stack_name,
            args.bindings_status, add_intro_note=not args.no_intro_note,
            sdk_repo_id_override=args.sdk_repo_id,
            out_path_override=out_path_map.get(wire),
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
