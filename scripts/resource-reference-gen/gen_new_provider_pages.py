#!/usr/bin/env python3
"""CLI entry point for onboarding a brand-new provider (no existing
resource-reference/<provider> pages at all) --
gen_provider_docs.generate_richer_provider. Every real page this
writes is a complete, runnable program (real package main/func main,
real stack()/export default wrapper, real if __name__ == "__main__":),
identical in shape to the rest of the corpus -- there is no sparse
"mechanical" output any more. That tier (build_resource_page,
gen_mechanical_pages.py) was removed entirely: a real `go build`
against its own literal output failed outright ("expected 'package',
found 'import'"), and a resource whose example can't compile as shown
must never be selectable as final output again. See README.md for the
real, full pipeline (schema dump -> extract_idents.py -> this).

Usage:
  python3 gen_new_provider_pages.py <provider> <schema-name> <provider-display> \\
      <schema.json> <idents.json> \\
      [--docs-root PATH] [--scratch-dir PATH] [--stack-name example] \\
      [--bindings-status published|local_only]

Example (the real command this session used for Datadog):
  python3 gen_new_provider_pages.py datadog datadog Datadog \\
      /tmp/datadog-ir-dump/datadog/schema.json /tmp/datadog_idents.json \\
      --bindings-status local_only
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_provider_docs import generate_richer_provider

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("provider", help='doc URL slug, e.g. "datadog" (resource-reference/datadog/...)')
    p.add_argument("schema_name", help='real wire prefix, e.g. "datadog" -- also the REAL_SDK_REPO_ID key')
    p.add_argument("provider_display", help='e.g. "Datadog"')
    p.add_argument("schema_path", help="real IR schema dump JSON (see README.md)")
    p.add_argument("idents_path", help="real extract_idents.py output JSON")
    p.add_argument("--docs-root", default=REPO_ROOT, help="real ubiquex-docs checkout root (default: this repo)")
    p.add_argument("--scratch-dir", default="/tmp", help="where to write the real nav fragment JSON (default: /tmp)")
    p.add_argument("--stack-name", default="example", help="real example stack name used across every generated program")
    p.add_argument("--intros-path", default=None,
                    help="artifacts/<provider>/intros.json (real, keyed by wire -- see real_intro_for) "
                         "to replace the generic boilerplate intro/frontmatter description. Omit to keep the boilerplate.")
    p.add_argument("--bindings-status", choices=["published", "local_only"], default="published",
                    help='"local_only" (no ubx-sdk-<provider>{,-go,-py,-ts} repo published or even created yet -- '
                         "confirmed live for datadog/github via `gh repo view`, not assumed) renders every "
                         "language's example with the real `ubx sdk gen --only <name> --lang <lang>` command "
                         "(plus, for Go, a real go.mod replace directive) instead of a remote import that would "
                         'reference a repo that doesn\'t exist. Default "published" matches every already-shipped page.')
    args = p.parse_args()

    intros_by_provider = None
    if args.intros_path:
        intros_by_provider = {args.provider: json.load(open(args.intros_path))}

    n_resources, n_services = generate_richer_provider(
        docs_root=args.docs_root,
        scratch_dir=args.scratch_dir,
        provider=args.provider,
        schema_name=args.schema_name,
        provider_display=args.provider_display,
        stack_name=args.stack_name,
        schema_path=args.schema_path,
        idents_path=args.idents_path,
        bindings_status=args.bindings_status,
        intros_by_provider=intros_by_provider,
    )
    print(f"generated {n_resources} resource pages across {n_services} services for {args.provider}")


if __name__ == "__main__":
    main()
