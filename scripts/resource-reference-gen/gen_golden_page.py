#!/usr/bin/env python3
"""UBI-175 Phase 6: generates ONE real resource page, fresh, against the
real schema dump + idents + artifacts/<provider>/intros.json, using the
exact same per-resource logic generate_richer_provider uses (example
field selection, Go/TS/Python/Markdown rendering, gofmt/deno fmt
verification) -- but with the real intro spliced in via
build_resource_page_complete's own intro_text parameter, replacing the
generic three-line boilerplate paragraph.

This writes ONLY into golden/<provider>/<slug>.mdx (this directory),
never into resource-reference/<provider>/... -- a golden page is a
candidate reference to be hand-reviewed and committed deliberately, not
a live doc page. No regeneration of the real corpus happens here or is
implied by running this script.

Usage:
  python3 gen_golden_page.py <provider> <schema_name> <provider_display> <wire> \\
      --schema-dir /tmp/schema-dump --idents-path /tmp/<schema_name>_idents.json \\
      --intros-path <path-to-artifacts>/<provider>/intros.json \\
      [--stack-name example] [--bindings-status published|local_only] \\
      [--out-dir golden]

Example (this session's real AWS candidate):
  python3 gen_golden_page.py aws aws AWS aws_launch_template \\
      --schema-dir /tmp/schema-dump --idents-path /tmp/aws_idents.json \\
      --intros-path ../../../ubiquex-docs/artifacts/aws/intros.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_provider_docs import (
    build_resource_page_complete,
    pick_richer_example_fields,
    field_literal_with_preamble,
    render_generic_markdown_scenario,
    wrap_markdown,
    KNOWN_FAMILY_MARKDOWN,
    REAL_SDK_REPO_ID,
)


# UBI-175 Phase 6: the real, shared generation core -- both this file's
# own CLI (writes straight to golden/<provider>/<slug>.mdx) and
# verify_against_golden.py (regenerates into memory, diffs against an
# already-committed golden file, never writes it) call this one real
# function, so there is exactly one place that decides what a
# freshly-generated golden page looks like, not two that could drift.
def generate(provider, schema_name, provider_display, wire, schema_dir, idents_path,
             intros_path, stack_name="example", bindings_status="published"):
    """Returns (page_text, slug, fields, intro_text_or_None). Raises
    SystemExit with a real, specific reason on any missing/mismatched
    real input -- never silently substitutes a guess."""
    if schema_name not in REAL_SDK_REPO_ID:
        raise SystemExit(f"no REAL_SDK_REPO_ID entry for schema_name {schema_name!r}")
    sdk_repo_id = REAL_SDK_REPO_ID[schema_name]

    schema_path = os.path.join(schema_dir, schema_name, "schema.json")
    fields_path = os.path.join(schema_dir, schema_name, f"{wire}.json")
    schema = json.load(open(schema_path))
    fields = json.load(open(fields_path))
    idents = json.load(open(idents_path))
    intros = json.load(open(intros_path))

    if wire not in schema:
        raise SystemExit(f"{wire!r} not present in {schema_path} -- not a real, currently-dumped resource")
    rec = schema[wire]
    service, local = rec["service"], rec["localName"]
    slug = local.replace("_", "-")

    if wire not in idents:
        raise SystemExit(
            f"{wire!r} not present in {idents_path} -- real idents/schema-dump key mismatch, "
            "not something this tool should silently paper over (see README.md's own service-boundary discipline)"
        )
    go, py, ts = idents[wire]["go"], idents[wire]["py"], idents[wire]["ts"]

    intro_text = intros.get(wire)
    if not intro_text:
        print(f"WARNING: no real intro for {wire!r} in {intros_path} -- falling back to generic boilerplate paragraph", file=sys.stderr)

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

    page, _ = build_resource_page_complete(
        wire=wire, service=service, local=local, slug=slug, fields=fields,
        go=go, py=py, ts=ts, provider=provider, schema_name=schema_name,
        provider_display=provider_display, stack_name=stack_name,
        intent_summary=f"{stack_name} own {local.replace('_', ' ')}",
        companion_markdown=companion_markdown, sdk_repo_id=sdk_repo_id,
        bindings_status=bindings_status, intro_text=intro_text,
    )
    return page, slug, fields, intro_text


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("provider", help='doc URL slug, e.g. "aws"')
    p.add_argument("schema_name", help='real wire prefix used in the schema dump, e.g. "aws"/"google"/"azure"')
    p.add_argument("provider_display", help='e.g. "AWS"')
    p.add_argument("wire", help='the exact wire resource type, e.g. "aws_launch_template"')
    p.add_argument("--schema-dir", required=True, help="directory containing <schema_name>/schema.json and <schema_name>/<wire>.json (see README.md)")
    p.add_argument("--idents-path", required=True, help="real extract_idents.py output JSON for this provider")
    p.add_argument("--intros-path", required=True, help="real artifacts/<provider>/intros.json path")
    p.add_argument("--stack-name", default="example")
    p.add_argument("--bindings-status", choices=["published", "local_only"], default="published")
    p.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "golden"))
    args = p.parse_args()

    page, slug, fields, _ = generate(
        args.provider, args.schema_name, args.provider_display, args.wire,
        args.schema_dir, args.idents_path, args.intros_path,
        args.stack_name, args.bindings_status,
    )

    out_dir = os.path.join(args.out_dir, args.provider)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{slug}.mdx")
    with open(out_path, "w") as fh:
        fh.write(page)
    print(f"wrote {out_path} ({len(page)} bytes, {len(fields)} top-level fields)")


if __name__ == "__main__":
    main()
