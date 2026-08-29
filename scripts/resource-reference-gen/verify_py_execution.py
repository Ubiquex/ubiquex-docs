#!/usr/bin/env python3
"""UBI-208: real Python EXECUTION verification for every Python example
block across a set of generated pages -- ast.parse (verify_py_blocks.py)
only proves the block is syntactically valid Python, never that it runs
against the real SDK runtime. A dict literal where the real generated
binding expects a dataclass is syntactically fine and raises TypeError
the moment `ubx.resource(...)`'s own config actually gets serialized --
exactly the class of bug this ticket exists to fix, and exactly the
class ast.parse structurally cannot catch. This runs the page's own
literal, unmodified `if __name__ == "__main__": ubx.run(...)` block as a
real subprocess -- `ubx.run` is local, describe-only evaluation (see
sdk/py/ubx_sdk/__init__.py's own doc comment: stack(...).evaluate(),
never a real provider call), the same "never actually ship" boundary
this project's own CLAUDE.md already draws, just exercised for real
instead of assumed safe.

Usage:
  python3 verify_py_execution.py --ubx-sdk-root PATH --sdk-provider-py-root PATH \\
      [--local-sdk-root PATH] <page.mdx> [<page.mdx> ...]

--ubx-sdk-root: real local checkout of the ubx_sdk runtime package
  (e.g. ~/Ubiquex/ubiquex/sdk/py -- must contain ubx_sdk/__init__.py).
--sdk-provider-py-root: real local checkout of the provider's own
  published Python bindings (e.g. ~/Ubiquex/ubx-sdk-github/sdk/python) --
  no default, matching verify_go_blocks.py's own --provider-go-module.
--local-sdk-root: real directory shaped <schema>/sdk/python/... (a real
  `ubx sdk gen --lang py --out` tree) -- required only for local_only
  pages, whose own comment line says `PYTHONPATH=./local-sdk/<schema>/
  sdk/python`.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile


def verify(path, ubx_sdk_root, sdk_provider_py_root, local_sdk_root=None):
    content = open(path).read()
    m = re.search(r"```python\n(.*?)\n    ```", content, re.DOTALL)
    if not m:
        return "skip", "no python block found"
    body = m.group(1)
    body = "\n".join(l[4:] if l.startswith("    ") else l for l in body.split("\n"))

    is_local_only = "PYTHONPATH=./local-sdk" in body
    provider_root = sdk_provider_py_root
    if is_local_only:
        m2 = re.search(r"PYTHONPATH=\./local-sdk/(\S+?)/sdk/python", body)
        if not m2 or local_sdk_root is None:
            return "fail", "page needs a local_only PYTHONPATH but no --local-sdk-root was given"
        provider_root = os.path.join(local_sdk_root, m2.group(1), "sdk", "python")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as fh:
        fh.write(body)
        script_path = fh.name

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([ubx_sdk_root, provider_root])
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=30, env=env,
        )
        if result.returncode != 0:
            return "fail", result.stderr
        return "ok", None
    finally:
        os.unlink(script_path)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pages", nargs="+", help="generated .mdx pages, each with a real ```python block")
    p.add_argument("--ubx-sdk-root", required=True, help="real local checkout of the ubx_sdk runtime")
    p.add_argument("--sdk-provider-py-root", required=True,
                    help="real local checkout of the provider's own published Python bindings")
    p.add_argument("--local-sdk-root",
                    help="real directory shaped <schema>/sdk/python/... -- required only for "
                    "local_only pages")
    args = p.parse_args()

    fails = []
    checked = 0
    for path in args.pages:
        status, detail = verify(path, args.ubx_sdk_root, args.sdk_provider_py_root, args.local_sdk_root)
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
    print(f"\n--- {ok_count}/{checked} real python execution OK ---")
    if fails:
        print(f"{len(fails)} FAILED:")
        for p_ in fails:
            print(f"  {p_}")
        sys.exit(1)


if __name__ == "__main__":
    main()
