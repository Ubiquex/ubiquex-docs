#!/usr/bin/env python3
"""UBI-208: real `deno check` verification for every TypeScript example
block across a set of generated pages -- `deno fmt` (already run inline
at generation time by deno_fmt_lines) only checks syntax/formatting,
never unresolved imports or a real structural type mismatch, which is
exactly the class of bug this ticket's own scope calls out ("add
TypeScript type-checking to the verification set, since its absence is
why this went unnoticed"): a nested object literal missing a field the
real generated interface declares as required type-checks as invalid
TypeScript even though `deno fmt` accepts it as syntactically valid.

Resolves the real bare-specifier imports every generated page uses
(`@ubx/sdk`, `@ubx/sdk-<repo id>/...`) against real local package
checkouts via a Deno workspace -- `deno check` has no equivalent of Go's
`replace` directive for a plain import map entry pointing at a bare
package name with export subpaths, so this builds a small, throwaway
workspace root and SYMLINKS the two real checkouts into it (Deno
requires workspace members to be nested under the workspace root; a
symlink keeps this pointed at the real, unmodified source rather than a
copy).

Usage:
  python3 verify_ts_blocks.py --sdk-ts-root PATH --sdk-provider-ts-root PATH \\
      <page.mdx> [<page.mdx> ...]

--sdk-ts-root: real local checkout of ubx-sdk-typescript (the runtime;
  must contain runtime/deno.json exporting "@ubx/sdk").
--sdk-provider-ts-root: real local checkout of the provider's own
  TypeScript bindings (e.g. ~/Ubiquex/ubx-sdk-google-ts; must contain its
  own deno.json exporting "@ubx/sdk-<repo id>" with per-resource
  subpaths) -- no default, matching verify_go_blocks.py's own
  --provider-go-module: a wrong-but-plausible default risks silently
  checking the wrong provider's bindings instead of catching a real
  per-provider mismatch.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile


def verify(path, sdk_ts_root, sdk_provider_ts_root, local_sdk_root=None):
    """Checks the LITERAL, unmodified page content -- no synthetic
    wrapper, ever, matching verify_go_blocks.py's own real, hard-learned
    discipline (its own doc comment: a wrapped fragment only ever proves
    the wrapper compiles, not the real page content copy-pasted exactly
    as shown)."""
    content = open(path).read()
    m = re.search(r"```typescript\n(.*?)\n    ```", content, re.DOTALL)
    if not m:
        return "skip", "no typescript block found"
    body = m.group(1)
    body = "\n".join(l[4:] if l.startswith("    ") else l for l in body.split("\n"))

    tmpdir = tempfile.mkdtemp(prefix="resource-reference-gen-tscheck-")
    try:
        members_dir = os.path.join(tmpdir, "members")
        os.makedirs(members_dir)
        runtime_link = os.path.join(members_dir, "runtime")
        provider_link = os.path.join(members_dir, "provider")
        os.symlink(os.path.join(sdk_ts_root, "runtime"), runtime_link)
        os.symlink(sdk_provider_ts_root, provider_link)

        with open(os.path.join(tmpdir, "deno.json"), "w") as fh:
            fh.write('{\n  "workspace": ["./members/runtime", "./members/provider"]\n}\n')

        # local_only pages import via a real relative path, "./local-
        # sdk/<schema>/sdk/typescript/...", matching the exact "ubx sdk
        # gen --out ./local-sdk" comment line every such page carries --
        # not a bare specifier the workspace above resolves at all.
        # local_sdk_root is expected to already have this same shape
        # (<schema>/sdk/typescript/...), so a single symlink at
        # "./local-sdk" makes every such import resolve to real,
        # freshly-generated source.
        if "./local-sdk/" in body:
            if local_sdk_root is None:
                return "fail", "page imports ./local-sdk/... but no --local-sdk-root was given"
            os.symlink(local_sdk_root, os.path.join(tmpdir, "local-sdk"))

        with open(os.path.join(tmpdir, "main.ts"), "w") as fh:
            fh.write(body)

        result = subprocess.run(
            ["deno", "check", "--no-remote", "main.ts"],
            cwd=tmpdir, capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return "fail", result.stderr
        return "ok", None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pages", nargs="+", help="generated .mdx pages, each with a real ```typescript block")
    p.add_argument("--sdk-ts-root", required=True, help="real local checkout of ubx-sdk-typescript")
    p.add_argument("--sdk-provider-ts-root", required=True,
                    help="real local checkout of the provider's own TypeScript bindings "
                    "(e.g. ~/Ubiquex/ubx-sdk-google-ts) -- no default, see module docstring")
    p.add_argument("--local-sdk-root",
                    help="real directory shaped <schema>/sdk/typescript/... (a real 'ubx sdk gen "
                    "--lang ts --out' tree) -- required only for local_only pages, which import "
                    "via a real relative './local-sdk/...' path rather than a bare specifier")
    args = p.parse_args()

    fails = []
    checked = 0
    for path in args.pages:
        status, detail = verify(path, args.sdk_ts_root, args.sdk_provider_ts_root, args.local_sdk_root)
        if status == "skip":
            print(f"SKIP {path}: {detail}")
            continue
        checked += 1
        if status == "ok":
            print(f"OK {path}")
        else:
            print(f"{status.upper()} {path}\n{detail}")
            fails.append(path)

    ok_count = checked - len(fails)
    print(f"\n--- {ok_count}/{checked} real deno check OK ---")
    if fails:
        print(f"{len(fails)} FAILED:")
        for p_ in fails:
            print(f"  {p_}")
        sys.exit(1)


if __name__ == "__main__":
    main()
