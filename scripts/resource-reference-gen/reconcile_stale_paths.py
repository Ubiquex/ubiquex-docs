#!/usr/bin/env python3
"""UBI-214: real cleanup for the stale-duplicate-page finding -- a wire
whose service-directory derivation changed since its page was first
generated gets a fresh page at the new, correct path on the next regen,
but nothing ever deleted the old one. Confirmed live: 137 of 146 new
pages a real AWS regen produced were exactly this, and the old path was
still live in docs.json navigation, not dead content.

apply_reconciliation is the one real function here, deliberately
importable rather than CLI-only: the caller that knows a wire's own
CURRENT correct path (regen_pages.py, mid-regen, having just written
it) is the only one with enough information to say which of two paths
for the same wire is stale -- this module never re-derives that itself,
it only acts on a caller-supplied (old_path, new_path, wire) list, the
same wire-identity bar (title match, not content diffing) UBI-209
already used to resolve 274 real page moves this session.

Nav/redirect mechanism mirrors that same UBI-209 work exactly: walk
docs.json's own navigation tree replacing every exact string match of
the old page path with the new one, and append a real
{"source": ..., "destination": ...} redirect entry for the old
published URL -- proven safe across 274 real moves already, promoted
here from scratch tooling into real, committed, reusable code.
"""
import json
import os


def mdx_to_url(rel):
    return "/" + rel[:-len(".mdx")] if rel.endswith(".mdx") else "/" + rel


def path_of(rel):
    return rel[:-len(".mdx")] if rel.endswith(".mdx") else rel


def replace_in_nav(node, old_p, new_p):
    """Walks docs.json's own navigation tree (nested dicts and lists),
    replacing every exact string match of the old page path with the
    new one -- real, in place, no assumption about tree shape."""
    count = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and v == old_p:
                node[k] = new_p
                count += 1
            else:
                count += replace_in_nav(v, old_p, new_p)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, str) and v == old_p:
                node[i] = new_p
                count += 1
            else:
                count += replace_in_nav(v, old_p, new_p)
    return count


def apply_reconciliation(docs_root, duplicates, write=False):
    """duplicates: [(old_rel_path, new_rel_path, wire), ...]. Always
    returns a real per-entry report (nav references updated, whether a
    redirect was added) whether or not write is set, so a caller can
    show the same detail in report-only mode as it would after really
    applying -- matching this codebase's own "report before applying"
    discipline for anything destructive.

    write=False (the default): computes and returns the full report,
    touches nothing on disk.
    write=True: deletes each real old_rel_path, updates docs.json's own
    real navigation tree and redirects array, and writes docs.json back."""
    docs_json_path = os.path.join(docs_root, "docs.json")
    doc = json.load(open(docs_json_path))

    report = []
    nav_updated_total = 0
    for old_rel, new_rel, wire in duplicates:
        old_p = path_of(old_rel)
        new_p = path_of(new_rel)
        nav_hits = 0
        if old_p != new_p:
            nav_hits = replace_in_nav(doc["navigation"], old_p, new_p)
        doc.setdefault("redirects", [])
        already_redirected = any(
            r.get("source") == mdx_to_url(old_rel) for r in doc["redirects"]
        )
        report.append({
            "wire": wire, "old_path": old_rel, "new_path": new_rel,
            "nav_references_updated": nav_hits,
            "redirect_already_present": already_redirected,
        })
        if not already_redirected:
            doc["redirects"].append({
                "source": mdx_to_url(old_rel), "destination": mdx_to_url(new_rel),
            })
        nav_updated_total += nav_hits

    if write:
        for old_rel, new_rel, wire in duplicates:
            old_full = os.path.join(docs_root, old_rel)
            if os.path.exists(old_full):
                os.remove(old_full)
        json.dump(doc, open(docs_json_path, "w"), indent=2)
        with open(docs_json_path, "a") as fh:
            fh.write("\n")

    return {
        "count": len(duplicates),
        "nav_references_updated": nav_updated_total,
        "entries": report,
    }
