#!/usr/bin/env python3
"""One-off driver, UBI-186's own real "validate on one category" proof:
generates the 10 real AWS Amplify data source pages from a real
`ubx sdk gen --dump-ir` schema dump, using gen_data_source_pages.py's own
real build_data_source_page. Not a general-purpose entry point (the real
one, covering all six providers, is real follow-up work once this one
category's own pattern is confirmed to validate cleanly) -- a small,
throwaway driver scoped to exactly this proof, matching how
gen_new_provider_pages.py itself stayed a thin driver over the real
shared builder.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_provider_docs import pascal
from gen_data_source_pages import build_data_source_page


def real_wire_type(go_file):
    """The dump-ir dict key (e.g. "data_aws_amplify_branches") is a real,
    but internal, dump-only disambiguator (cli/sdk.go's own "data_"
    prefix, added ONLY so a data source's own dump-ir output file never
    collides with its same-named resource's -- see UBI-178 piece 4's own
    doc comment). It was never meant to be the page's own real wire type
    -- confirmed live: the real generated binding's own WireType field
    (ubx.DataSourceBinding{WireType: "aws_amplify_branches", ...}) has no
    such prefix at all. Read directly from the real generated Go source
    -- ground truth, not re-derived or guessed."""
    text = open(go_file).read()
    m = re.search(r'WireType:\s*"([^"]+)"', text)
    if not m:
        raise RuntimeError(f"no WireType found in {go_file}")
    return m.group(1)

DUMP_DIR = "/tmp/amplify-test/dumpir"
GEN_DIR = "/tmp/amplify-test/gen/aws_data_amplify/sdk"
OUT_DIR = "resource-reference/aws/data/amplify"

os.makedirs(DUMP_DIR + "/aws_data_amplify", exist_ok=True)


def idents_for(local):
    pascal_name = pascal(local)
    return (
        {"service_dir": "amplify", "package": "amplify", "binding": pascal_name, "config": f"{pascal_name}Config",
         "file": f"{GEN_DIR}/go/aws_data_amplify/data/amplify/{local}.go"},
        {"service_dir": "amplify", "binding": pascal_name,
         "file": f"{GEN_DIR}/typescript/aws_data_amplify/data/amplify/{local}.ts"},
        {"service_dir": "amplify", "binding": pascal_name,
         "file": f"{GEN_DIR}/python/ubx/aws_data_amplify/data/amplify/{local}.py"},
    )


def main():
    schema = json.load(open("/tmp/aws-full-probe/aws/schema.json"))
    amplify_ds = {k: v for k, v in schema.items() if v.get("namespace") == "data" and v.get("service") == "amplify"}
    os.makedirs(OUT_DIR, exist_ok=True)

    for _, meta in sorted(amplify_ds.items()):
        local = meta["localName"]
        fields = meta["ir"]["Fields"]
        go, ts, py = idents_for(local)
        wire = real_wire_type(go["file"])
        page = build_data_source_page(
            wire=wire, service="amplify", local=local, slug=local.replace("_", "-"),
            fields=fields, go=go, ts=ts, py=py,
            provider="aws", schema_name="aws", provider_display="AWS",
            stack_name="example", sdk_repo_id="aws",
        )
        out_path = os.path.join(OUT_DIR, f"{local.replace('_', '-')}.mdx")
        with open(out_path, "w") as f:
            f.write(page)
        print("wrote", out_path)


if __name__ == "__main__":
    main()
