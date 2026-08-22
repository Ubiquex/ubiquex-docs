#!/usr/bin/env python3
"""UBI-175 Phase D: three-bucket redirect analysis, same methodology as
the GCP Compute/Kubernetes/AWS Phase 4 precedents -- CLEAN (old wire
name maps exactly to a real new page), PROBABLE (naming convention
differs but it's clearly the same resource), ORPHANED (old page has no
real successor at all). Never writes redirects or deletes anything --
report only, per the founder's own explicit instruction this session.

"New universe" = every currently-live page under resource-reference/
<provider> whose own frontmatter title does NOT match the old
boilerplate description marker -- this naturally includes both the
freshly-regenerated pages (this session) and the already-live GCP
Compute / Azure Compute pages regenerated in an earlier Phase 6 session
(both already new-style, confirmed by direct inspection this session).

Usage:
  python3 redirect_diff.py gcp
  python3 redirect_diff.py azure
"""
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TITLE_RE = re.compile(r'^title:\s*"([^"]+)"', re.MULTILINE)
OLD_MARKER = "Real, generated bindings for"


def normalize(w):
    return w.replace("_", "").replace("-", "").lower()


def tokens(w):
    return [t for t in w.lower().split("_") if t]


def token_suffix_match(old_tokens, new_tokens):
    """True iff old_tokens appears as a real trailing TOKEN sequence of
    new_tokens -- found-in-review defect in the earlier character-level
    normalize().endswith() check: 'api_connection' (azurerm_api_
    connection, a Logic App connector) character-matched against
    '...openapi_connection' (azure_automation_openapi_connection, an
    unrelated resource) purely because 'openapi' happens to end in the
    substring 'api' -- a real, wrong pairing. Token-boundary comparison
    can't cross a word boundary like that."""
    if not old_tokens or len(old_tokens) > len(new_tokens):
        return False
    return new_tokens[-len(old_tokens):] == old_tokens


def main():
    provider = sys.argv[1]
    prefix_old = {"gcp": "google_", "azure": "azurerm_"}[provider]

    old_pages = {}   # wire -> relpath
    new_pages = {}   # wire -> relpath
    for path in glob.glob(os.path.join(REPO_ROOT, "resource-reference", provider, "**", "*.mdx"), recursive=True):
        if os.path.basename(path) == "index.mdx":
            # a service-level CardGroup landing page (generate_richer_
            # provider's own title = service.title(), e.g. "Apimanagement")
            # -- a real page, but not a per-resource one, so it must never
            # participate in per-resource redirect matching (found in
            # review: it was matching stray old resource names against
            # landing-page titles like "Apimanagement"/"Datafactory").
            continue
        text = open(path).read()
        m = TITLE_RE.search(text)
        if not m:
            continue
        wire = m.group(1)
        rel = os.path.relpath(path, REPO_ROOT)
        if OLD_MARKER in text:
            old_pages[wire] = rel
        else:
            new_pages[wire] = rel

    print(f"{provider}: {len(old_pages)} old-style pages, {len(new_pages)} new-style pages (live universe)")

    clean, probable, orphaned = [], [], []
    new_by_norm = {}
    for w, p in new_pages.items():
        new_by_norm.setdefault(normalize(w), []).append((w, p))

    for old_wire, old_path in sorted(old_pages.items()):
        if old_wire in new_pages:
            clean.append((old_wire, old_path, old_wire, new_pages[old_wire]))
            continue
        norm = normalize(old_wire)
        candidates = new_by_norm.get(norm, [])
        if len(candidates) == 1:
            probable.append((old_wire, old_path, candidates[0][0], candidates[0][1]))
            continue
        if len(candidates) > 1:
            probable.append((old_wire, old_path, "AMBIGUOUS:" + ",".join(c[0] for c in candidates), ""))
            continue
        # Azure's old corpus uses "azurerm_" where the new source uses
        # "azure_<service>_<...>" -- a real, known prefix-family
        # divergence (not just a string-prefix swap: the new source also
        # re-groups by its own service taxonomy), so also try dropping
        # the old "azurerm_"/"google_" prefix and normalized-matching
        # against new wire SUFFIXES before calling it orphaned.
        old_suffix = tokens(old_wire[len(prefix_old):]) if old_wire.startswith(prefix_old) else tokens(old_wire)
        suffix_candidates = [
            (w, p) for w, p in new_pages.items()
            if len(old_suffix) >= 2 and token_suffix_match(old_suffix, tokens(w))
        ]
        if len(suffix_candidates) == 1:
            probable.append((old_wire, old_path, suffix_candidates[0][0], suffix_candidates[0][1]))
            continue
        orphaned.append((old_wire, old_path))

    print(f"\nCLEAN: {len(clean)}")
    print(f"PROBABLE: {len(probable)}")
    print(f"ORPHANED: {len(orphaned)}")

    out = {
        "provider": provider,
        "old_count": len(old_pages),
        "new_count": len(new_pages),
        "clean": [{"old_wire": a, "old_path": b, "new_wire": c, "new_path": d} for a, b, c, d in clean],
        "probable": [{"old_wire": a, "old_path": b, "new_wire": c, "new_path": d} for a, b, c, d in probable],
        "orphaned": [{"old_wire": a, "old_path": b} for a, b in orphaned],
    }
    out_path = f"/tmp/regen-scratch/{provider}_redirect_diff.json"
    json.dump(out, open(out_path, "w"), indent=2)
    print(f"\nwrote full detail -> {out_path}")

    print("\n--- sample PROBABLE (first 15) ---")
    for a, b, c, d in probable[:15]:
        print(f"  {a} -> {c}")
    print("\n--- sample ORPHANED (first 25) ---")
    for a, b in orphaned[:25]:
        print(f"  {a}")


if __name__ == "__main__":
    main()
