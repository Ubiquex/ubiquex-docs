#!/usr/bin/env python3
"""UBI-152: splices ONLY the Input properties/Output properties sections
of an existing resource-reference page with real, schema-sourced field
descriptions (sdk/codegen/ir.Field.Description, threaded through from
the real provider's own wire response -- provider/schema.go). Mirrors
gen_complete_pages.py's own "splice this one section, leave everything
else on the page untouched" discipline exactly, applied to a different
section of the same page.

Real, confirmed live (see STATE.md UBI-152 entry): hashicorp/google and
hashicorp/kubernetes both populate real, rich Description text on the
wire; hashicorp/aws and hashicorp/azurerm both report this genuinely
empty for nearly every real attribute -- for those, field_desc's
existing flag-derived sentence is unchanged, so running this tool
against an AWS/Azure page is expected to be a real no-op (confirm via
the produced diff, don't just assume).

Usage:
  python3 gen_field_descriptions.py --schema-dir DIR --idents-path FILE \\
      [--docs-root PATH] [--provider gcp] [--provider-display GCP] \\
      <wire_type> [<wire_type> ...]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_provider_docs import (
    eff_flags,
    render_response_field,
    resolve_page_path,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The exact, known set of mechanical-tier description sentences
# field_desc has ever produced (pre-UBI-152), for a real provider_display.
# A real, found-in-review case (aws_iam_role): NOT every existing page's
# Input/Output properties section is this generic placeholder -- some
# carry real, hand-authored prose from an earlier phase of this project
# ("The role's own name. Conflicts with `name_prefix`.") that
# gen_complete_pages.py's own Example-only splice was deliberately built
# to never touch. Blindly regenerating Input/Output properties would
# silently destroy that real content wherever it exists. This function
# is the safety gate: only pages where EVERY existing top-level
# description line is already one of the known mechanical placeholders
# are safe to regenerate; anything else is skipped, flagged for a real,
# human decision, never silently overwritten.
def known_placeholder_lines(provider_display):
    return {
        "Required.",
        f"Optional; if omitted, computed by {provider_display}.",
        "Optional.",
        f"Computed by {provider_display} after `ship`.",
    }


def find_hand_tuned_lines(section_body, provider_display):
    """Returns real, non-mechanical description lines found in an
    existing Input/Output properties section body -- text lines that
    are direct children of a top-level <ResponseField>, not the tag
    lines/Expandable structure themselves, matching exactly what
    field_desc/render_response_field ever emit at the top level."""
    known = known_placeholder_lines(provider_display)
    hand_tuned = []
    depth = 0
    for raw in section_body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("<ResponseField"):
            depth += 1
            continue
        if line.startswith("</ResponseField>"):
            depth -= 1
            continue
        if line.startswith("<Expandable") or line.startswith("</Expandable>"):
            continue
        # A top-level ResponseField's own description line sits
        # immediately inside it, at depth 1 -- matching render_
        # response_field's own "if not nested" (only the OUTERMOST
        # ResponseField ever gets a description line at all).
        if depth == 1 and line not in known:
            hand_tuned.append(line)
    return hand_tuned


def generate_one(wire, docs_root, schema_dir, idents_all, provider, provider_display, dry_run=False):
    schema_path = os.path.join(schema_dir, f"{wire}.json")
    if not os.path.isfile(schema_path):
        return "skip", f"no schema dump at {schema_path}"
    if wire not in idents_all:
        return "skip", "no identifier entry (run extract_idents.py first)"

    fields = json.load(open(schema_path))
    idents = idents_all[wire]
    out_path, _, _, _ = resolve_page_path(docs_root, provider, idents)
    if not os.path.isfile(out_path):
        return "skip", f"no existing page at {out_path}"

    input_fields = sorted(
        [f for f in fields if f["Required"] or eff_flags(f)[1]], key=lambda f: f["WireName"]
    )
    output_fields = sorted(
        [f for f in fields if eff_flags(f)[2]], key=lambda f: f["WireName"]
    )
    input_block = "\n\n".join(render_response_field(f, 0, False, provider_display) for f in input_fields)
    output_block = "\n\n".join(render_response_field(f, 0, False, provider_display) for f in output_fields)

    original = open(out_path).read()
    # Split on real, top-level "## " section headers only (a page can
    # carry a "## See also" -- or any other -- section AFTER Output
    # properties, e.g. resource-reference/aws/iam/role.mdx; a naive
    # "everything after Output properties" replace would silently
    # delete it). re.split with a capturing group keeps every header
    # text in the result list, interleaved with its own body, so every
    # section this splice doesn't own passes through byte-identical.
    parts = re.split(r"(?m)^(## .+)$", original)
    if "## Input properties" not in parts or "## Output properties" not in parts:
        return "error", "page doesn't match the expected Input/Output properties shape"

    input_idx = parts.index("## Input properties") + 1
    output_idx = parts.index("## Output properties") + 1

    hand_tuned = find_hand_tuned_lines(parts[input_idx], provider_display)
    hand_tuned += find_hand_tuned_lines(parts[output_idx], provider_display)
    if hand_tuned:
        sample = "; ".join(repr(l) for l in hand_tuned[:3])
        return "skip-handtuned", f"{len(hand_tuned)} real, non-mechanical description line(s) already on this page, not overwriting -- e.g. {sample}"

    parts[input_idx] = "\n\n" + input_block + "\n\n"
    # A trailing "\n\n" (blank-line separator before the next "## "
    # header) is only correct when a next section actually exists --
    # Output properties is the LAST real section on most pages (no
    # "## See also"), so blindly always adding one would grow a real,
    # unnecessary trailing blank line at EOF every single run,
    # compounding on every future regen. original's own real trailing
    # newline convention (exactly one, confirmed against every other
    # already-approved richer-tier page) is preserved instead.
    output_body = "\n\n" + output_block
    output_body += "\n\n" if output_idx + 1 < len(parts) else "\n"
    parts[output_idx] = output_body
    new_page = "".join(parts)
    if new_page == original:
        return "unchanged", out_path
    if dry_run:
        return "would-change", out_path
    with open(out_path, "w") as fh:
        fh.write(new_page)
    return "ok", out_path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wires", nargs="*")
    p.add_argument("--wires-file")
    p.add_argument("--schema-dir", required=True)
    p.add_argument("--idents-path", required=True)
    p.add_argument("--docs-root", default=REPO_ROOT)
    p.add_argument("--provider", default="aws")
    p.add_argument("--provider-display", default="AWS")
    p.add_argument("--dry-run", action="store_true", help="classify only, never write")
    p.add_argument("--quiet", action="store_true", help="suppress per-wire lines, print summary only")
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
            wire, args.docs_root, args.schema_dir, idents_all, args.provider, args.provider_display,
            dry_run=args.dry_run,
        )
        if not args.quiet:
            print(f"{status.upper()} {wire}: {detail}")
        results.append((wire, status, detail))

    ok = [r for r in results if r[1] in ("ok", "would-change", "unchanged")]
    print(f"\n--- {len(ok)}/{len(wires)} processed ---")
    for wire, status, detail in results:
        if status not in ("ok", "would-change", "unchanged"):
            print(f"  {status}: {wire} -- {detail}")


if __name__ == "__main__":
    main()
