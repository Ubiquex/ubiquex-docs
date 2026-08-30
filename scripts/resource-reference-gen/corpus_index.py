#!/usr/bin/env python3
"""UBI-214: a real, wire-identity index of the CURRENTLY COMMITTED
resource-reference/<provider> tree, built once per provider by reading
each real .mdx page's own frontmatter title and TypeScript import
block -- the shared foundation both real fixes this ticket named need,
since both are answered by the same question: "does this wire already
have a page, and if so, where and in what bindings_status."

Two real, distinct problems this closes, confirmed live against a real
full AWS regen (1715 resources, `regen_pages.py` against a fresh
schema dump):

1. bindings_status data loss (the data-loss risk): `regen_pages.py`
   used to hardcode bindings_status="local_only" for every page it
   wrote, unconditionally -- a real regen would silently downgrade
   every one of the 9,623 pages UBI-196 deliberately, verifiably
   flipped to "published" back to local_only, discarding real,
   already-verified work. Fixed by looking up the wire's OWN existing
   bindings_status here first, before deciding what to write.

2. Stale duplicate pages (the corpus-rot risk): a wire whose service-
   directory derivation improves (an established, recurring pattern in
   this pipeline -- azure_corrected_wire's own collapsing, UBI-151's
   escape-undo, the real appflow/appsync-style collapses this ticket's
   own diagnostic regen surfaced) gets a fresh page at the new,
   correct path on the next regen, but nothing ever deletes the old
   one -- confirmed live: 137 of 146 new pages a real AWS regen
   produced (94%, 8% of AWS's own 1715-resource corpus on one
   snapshot) were exactly this, and the old path was still live in
   docs.json navigation, not dead/unreachable content. This index is
   what lets a caller ask "does this wire already live somewhere
   else," the same wire-identity bar (title match, not content diffing)
   UBI-209 already used to resolve 274 real page moves this session.
"""
import os
import re

import providers as providers_registry

TITLE_RE = re.compile(r'title:\s*"([^"]+)"')

# UBI-214: real, found-in-review bug in this file's own first version --
# a resource and its own same-named data source (e.g. the real,
# settable aws_ssm_service_setting resource and its own real, read-only
# data_aws_ssm_service_setting lookup) share the identical BARE title
# text in their own frontmatter (neither carries a "data_" prefix in
# `title:` -- that prefix only exists in the wire's own internal schema
# key, gen_all_data_source_pages.py's own real page never renders it).
# Indexing by bare title alone silently conflated the two: whichever
# one a sorted directory walk visited last would overwrite the other's
# own real bindings_status in the index, and check_duplicate_wires.py's
# own first version flagged 48 of these as false-positive "stale
# duplicates" on AWS alone -- genuinely different wires, not corpus rot.
#
# Real disambiguator: gen_all_data_source_pages.py's own main() driver
# always writes a data source under resource-reference/<provider>/data/
# <service_dir>/<slug>.mdx -- service_dir is always a REAL, separate
# directory component, never collapsed into the filename. A resource
# whose own real service happens to be named "data" (real, confirmed
# live: AWS DataBrew's pre-correction service_dir, e.g.
# resource-reference/aws/data/brew-dataset.mdx) sits directly inside
# data/ with no further subdirectory. The real test is therefore
# "does 'data/' have another real directory between it and the file,"
# not "does the path contain 'data/' anywhere."
DATA_SOURCE_PATH_RE = re.compile(r'/data/[^/]+/[^/]+\.mdx$')


def real_wire_of(rel_path, title):
    """The real, globally-unique wire identity for rel_path -- title
    alone is NOT sufficient (see the module-level note above); a data
    source gets its own real "data_" prefix restored, matching its own
    real internal schema key, so it can never collide with a same-
    named resource in this index."""
    return ("data_" + title) if DATA_SOURCE_PATH_RE.search(rel_path.replace(os.sep, "/")) else title

# UBI-214: the real, only-ever-manually-set marker this codebase has
# used to distinguish local_only from published (gen_complete_pages.py's
# own --bindings-status flag doc comment names the same exact check --
# a "// ubx sdk gen --only ... --out ./local-sdk" comment above a
# "./local-sdk/..." import means local_only; a bare "@ubx/sdk-<repo
# id>/..." import with no such comment means published). This is the
# first place that check is automated rather than a human reading the
# page by hand.
LOCAL_ONLY_MARKER = "--out ./local-sdk"


def detect_bindings_status(content):
    """Real, direct read of a committed page's own TypeScript import
    block -- never inferred from a provider-level default, since a
    provider can genuinely have a mix (a resource UBI-196 verified and
    published sitting next to one that's still local_only)."""
    return "local_only" if LOCAL_ONLY_MARKER in content else "published"


def scan_provider_corpus(docs_root, provider):
    """Walks the real, current resource-reference/<provider>/ tree once,
    returns {wire_title: {"path": <repo-relative .mdx path>,
    "bindings_status": "published"|"local_only"}}.

    Reads each file's own full content (not just a head slice) --
    bindings_status detection needs the TypeScript block, which sits
    well past a typical frontmatter-only read window on a real page
    with a long description or intro paragraph first.

    A title appearing more than once in the real, current tree (the
    exact "stale duplicate" case this index exists to find) keeps
    whichever path is encountered LAST in a deterministic (sorted)
    walk -- callers doing real reconciliation must not rely on which
    one "wins" here to decide what's stale; that decision belongs to
    the caller, which knows the CURRENT correct path for a wire it's
    about to write, not this scan alone. See check_duplicate_wires.py
    for the tool that surfaces every such collision explicitly, rather
    than silently picking one.
    """
    index = {}
    root = os.path.join(docs_root, "resource-reference", provider)
    if not os.path.isdir(root):
        return index
    for dirpath, _, files in sorted(os.walk(root)):
        for fn in sorted(files):
            if fn == "index.mdx" or not fn.endswith(".mdx"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                content = open(full, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            m = TITLE_RE.search(content[:400])
            if not m:
                continue
            rel = os.path.relpath(full, docs_root)
            wire = real_wire_of(rel, m.group(1))
            index[wire] = {
                "path": rel,
                "bindings_status": detect_bindings_status(content),
            }
    return index


def all_titles_with_paths(docs_root, provider):
    """Like scan_provider_corpus, but returns EVERY path per title
    (not just the last one) -- {wire_title: [rel_path, ...]} -- what
    check_duplicate_wires.py needs to report a real collision, not just
    know one exists."""
    by_title = {}
    root = os.path.join(docs_root, "resource-reference", provider)
    if not os.path.isdir(root):
        return by_title
    for dirpath, _, files in sorted(os.walk(root)):
        for fn in sorted(files):
            if fn == "index.mdx" or not fn.endswith(".mdx"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                head = open(full, encoding="utf-8", errors="replace").read(400)
            except OSError:
                continue
            m = TITLE_RE.search(head)
            if not m:
                continue
            rel = os.path.relpath(full, docs_root)
            wire = real_wire_of(rel, m.group(1))
            by_title.setdefault(wire, []).append(rel)
    return by_title


# UBI-137: moved here from gen_all_data_source_pages.py (its original,
# still-real caller) so gen_provider_docs.py's own rebuild_provider_nav
# can share the identical docs.json lookup rather than a second,
# possibly-diverging copy -- gen_provider_docs.py is itself imported BY
# gen_all_data_source_pages.py, so the shared home has to be a module
# neither one imports the other through. corpus_index.py is already the
# "real, current tree" ground-truth module both resource and nav
# rebuilding need; providers.py is the equivalent ground truth for
# which providers exist at all, so importing it here has no
# circularity risk either. Read from providers.py's own shared
# registry (Tier 2), not a separately-maintained copy.
PROVIDER_TAB_NAMES = {k: providers_registry.tab_name(k) for k in providers_registry.all_docs_keys()}


def provider_group(doc, provider_key):
    target_tab = PROVIDER_TAB_NAMES[provider_key]
    for t in doc["navigation"]["tabs"]:
        if t.get("tab") != "SDK Reference":
            continue
        for g in t["groups"]:
            if g.get("group") == target_tab:
                return g["pages"]
    raise RuntimeError(f"no {target_tab!r} group found in docs.json")


def resource_pages_of(subgroup):
    """A subgroup's own real, flat resource page list -- whether it's
    still a plain {"group": X, "pages": [str, ...]} (never touched by
    this nesting pattern) or already {"group": X, "pages":
    [{"group": "Resources", ...}, {"group": "Data sources", ...}]} (a
    re-run)."""
    pages = subgroup.get("pages", [])
    if pages and isinstance(pages[0], dict):
        resources_sub = next((p for p in pages if p.get("group") == "Resources"), None)
        return resources_sub["pages"] if resources_sub else []
    return pages


def set_resource_pages(subgroup, new_pages):
    """resource_pages_of's own write-side mirror (UBI-137) -- updates
    ONLY the resource half of subgroup["pages"] in place, leaving an
    already-present "Data sources" sub-list (gen_all_data_source_pages.py's
    own real write shape) untouched either way."""
    pages = subgroup.get("pages", [])
    if pages and isinstance(pages[0], dict):
        resources_sub = next((p for p in pages if p.get("group") == "Resources"), None)
        if resources_sub is not None:
            resources_sub["pages"] = new_pages
        else:
            pages.insert(0, {"group": "Resources", "pages": new_pages})
    else:
        subgroup["pages"] = new_pages
