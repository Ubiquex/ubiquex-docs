#!/usr/bin/env python3
"""Real ast.parse verification for every Python example block across a
set of generated pages. Python blocks aren't auto-verified at
generation time the way Go/TS are (gofmt_lines/deno_fmt_lines run
inline in gen_provider_docs.py); this closes that gap as its own real
pass, same discipline.

Usage:
  python3 verify_py_blocks.py <page.mdx> [<page.mdx> ...]
"""
import ast
import re
import sys


def main():
    paths = sys.argv[1:]
    if not paths:
        print("usage: verify_py_blocks.py <page.mdx> [<page.mdx> ...]", file=sys.stderr)
        sys.exit(2)

    fails, oks = [], []
    for path in paths:
        content = open(path).read()
        m = re.search(r"```python\n(.*?)\n    ```", content, re.DOTALL)
        if not m:
            print(f"SKIP {path}: no python block found")
            continue
        body = m.group(1)
        body = "\n".join(l[4:] if l.startswith("    ") else l for l in body.split("\n"))
        try:
            ast.parse(body)
            oks.append(path)
        except SyntaxError as e:
            fails.append((path, str(e)))
            print(f"FAIL {path}: {e}\n{body}")

    print(f"\n--- {len(oks)}/{len(paths)} python ast.parse OK ---")
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
