#!/usr/bin/env python3
"""CLI entry point for the ORIGINAL, full-provider mechanical-tier
generator (gen_provider_docs.generate_mechanical_provider) -- the tool
that produced the AWS/GCP/Azure/Kubernetes corpus's own initial 4649
pages. See README.md for the real, full pipeline (schema dump ->
extract_idents.py -> this).

Usage:
  python3 gen_mechanical_pages.py <provider> <schema-name> <provider-display> \\
      <go-module> <ts-repo> <ts-published:0|1> <schema.json> <idents.json> \\
      [--docs-root PATH] [--scratch-dir PATH]

Example (GCP, real args used to generate the real, live GCP corpus):
  python3 gen_mechanical_pages.py gcp google GCP \\
      github.com/ubiquex/ubx-sdk-google-go ubx-sdk-google-ts 0 \\
      /tmp/gcp_schema_all.json /tmp/gcp_idents.json
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_provider_docs import generate_mechanical_provider

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("provider", help='doc URL slug, e.g. "gcp" (resource-reference/gcp/...)')
    p.add_argument("schema_name", help='real wire prefix, e.g. "google" (hashicorp/google)')
    p.add_argument("provider_display", help='e.g. "GCP"')
    p.add_argument("go_module", help="e.g. github.com/ubiquex/ubx-sdk-google-go")
    p.add_argument("ts_repo", help="e.g. ubx-sdk-google-ts")
    p.add_argument("ts_published", choices=["0", "1"], help="1 if the TS package is real and published on jsr")
    p.add_argument("schema_path", help="real IR schema dump JSON (see README.md)")
    p.add_argument("idents_path", help="real extract_idents.py output JSON")
    p.add_argument("--docs-root", default=REPO_ROOT, help="real ubiquex-docs checkout root (default: this repo)")
    p.add_argument("--scratch-dir", default="/tmp", help="where to write the real nav fragment JSON (default: /tmp)")
    p.add_argument("--bindings-status", choices=["published", "local_only"], default="published",
                    help='"local_only" (no ubx-sdk-<provider>{,-go,-py,-ts} repo published or even created yet -- '
                         "confirmed live for datadog/github via `gh repo view`, not assumed) renders every "
                         "language's example with the real `ubx sdk gen --only <name> --lang <lang>` command "
                         "instead of a remote import/clone that would reference a repo that doesn't exist. "
                         'Default "published" reproduces every existing provider page unchanged.')
    args = p.parse_args()

    n_resources, n_services = generate_mechanical_provider(
        docs_root=args.docs_root,
        scratch_dir=args.scratch_dir,
        provider=args.provider,
        schema_name=args.schema_name,
        provider_display=args.provider_display,
        go_module=args.go_module,
        ts_repo=args.ts_repo,
        ts_published=args.ts_published == "1",
        schema_path=args.schema_path,
        idents_path=args.idents_path,
        bindings_status=args.bindings_status,
    )
    print(f"generated {n_resources} resource pages across {n_services} services for {args.provider}")


if __name__ == "__main__":
    main()
