#!/usr/bin/env python3
"""Real go build verification for every Go example block across a set
of generated pages -- gofmt only checks syntax, never unresolved
imports/undefined identifiers, which is exactly the class of real bug
this session's own manual review caught once already (a preamble that
needed encoding/json, missed by an import-detection check scoped too
narrowly to the FIRST preamble that needed it). Extracts each block
into a real, throwaway module requiring + replacing the real local
ubx-sdk-go/ubx-sdk-<provider> checkouts, runs a real `go build`.

Usage:
  python3 verify_go_blocks.py --sdk-go-root PATH --sdk-provider-go-root PATH \\
      --provider-go-module github.com/ubiquex/ubx-sdk-<provider>/sdk/go \\
      <page.mdx> [<page.mdx> ...]

--provider-go-module is REQUIRED, no default -- real per-provider
values: github.com/ubiquex/ubx-sdk-aws/sdk/go,
github.com/ubiquex/ubx-sdk-google/sdk/go,
github.com/ubiquex/ubx-sdk-azure/sdk/go,
github.com/ubiquex/ubx-sdk-kubernetes/sdk/go (see gen_complete_pages.py's
own REAL_SDK_REPO_ID for the same, single source of truth).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile


def verify(path, sdk_go_root, sdk_provider_go_root, provider_go_module):
    content = open(path).read()
    m = re.search(r"```go\n(.*?)\n    ```", content, re.DOTALL)
    if not m:
        return "skip", "no go block found"
    body = m.group(1)
    body = "\n".join(l[4:] if l.startswith("    ") else l for l in body.split("\n"))

    tmpdir = tempfile.mkdtemp(prefix="resource-reference-gen-gobuild-")
    try:
        with open(os.path.join(tmpdir, "main.go"), "w") as fh:
            fh.write(body)
        gomod = f"""module resourcereferencegenverify

go 1.23

require github.com/ubiquex/ubx-sdk-go v0.0.0
require {provider_go_module} v0.0.0

replace github.com/ubiquex/ubx-sdk-go => {sdk_go_root}
replace {provider_go_module} => {sdk_provider_go_root}
"""
        with open(os.path.join(tmpdir, "go.mod"), "w") as fh:
            fh.write(gomod)
        tidy = subprocess.run(["go", "mod", "tidy"], cwd=tmpdir, capture_output=True, text=True, timeout=60)
        if tidy.returncode != 0:
            return "fail", "go mod tidy: " + tidy.stderr
        result = subprocess.run(["go", "build", "."], cwd=tmpdir, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return "fail", result.stderr
        return "ok", None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pages", nargs="+", help="generated .mdx pages, each with a real ```go block")
    p.add_argument("--sdk-go-root", required=True, help="real local checkout of the ubx-sdk-go runtime")
    p.add_argument("--sdk-provider-go-root", required=True,
                    help="real local checkout of the provider's own Go bindings (e.g. ~/Ubiquex/ubx-sdk-aws/sdk/go)")
    p.add_argument("--provider-go-module", required=True,
                    help="the real Go module path the pages' own import lines use -- "
                    "no default: a wrong-but-plausible value (e.g. always defaulting to "
                    "AWS's own module regardless of which provider is being verified) "
                    "silently masks a real per-provider import-path bug instead of "
                    "catching it (this is exactly how a real, live GCP bug -- every "
                    "generated page importing github.com/ubiquex/ubx-sdk-aws/sdk/go "
                    "instead of .../ubx-sdk-google/sdk/go -- went undetected across "
                    "1328 already-committed pages)")
    args = p.parse_args()

    fails = []
    for path in args.pages:
        status, detail = verify(path, args.sdk_go_root, args.sdk_provider_go_root, args.provider_go_module)
        if status == "ok":
            print(f"OK {path}")
        else:
            print(f"{status.upper()} {path}\n{detail}")
            if status == "fail":
                fails.append(path)

    ok_count = len(args.pages) - len(fails)
    print(f"\n--- {ok_count}/{len(args.pages)} real go build OK ---")
    if fails:
        print(f"{len(fails)} FAILED:")
        for p_ in fails:
            print(f"  {p_}")
        sys.exit(1)


if __name__ == "__main__":
    main()
