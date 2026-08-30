#!/usr/bin/env python3
"""UBI-137: given a provider's own just-finished regen_pages.py and/or
gen_all_data_source_pages.py run, excludes -- deletes the just-written
file for, never stages -- any resource or data source whose own
coverage gate found a gap, instead of discarding the whole provider's
batch whenever a handful of new resources are still waiting on an
intro, category, or description. UBI-216's own decided chain: artifacts
are mandatory, batches stay small, and re-doing the same already-clean
work every run while one resource's artifact is still being written
defeats the point of automating this at all.

Reads both generators' own real manifests
({scratch-dir}/{provider}_regen_result.json,
{scratch-dir}/{provider}_datasource_regen_result.json) rather than
recomputing coverage a second time -- the exact check_gaps() result
each generator already ran against its own freshly-written batch,
before this script ever runs. Either manifest is optional (a provider
this run touched only for data sources, or only for resources, has
just the one).

Deletes each excluded wire's own just-written file, then corrects
docs.json and the provider's own index.mdx against the real,
post-exclusion file tree: rebuild_provider_index/rebuild_provider_nav
for resources (see rebuild_provider_nav's own doc comment for why this
has to re-run rather than trust the generator's own most recent call),
plus a surgical removal of any excluded data source's own nav entry,
since gen_all_data_source_pages.py's own docs.json write already ran,
unconditionally, before this script did.

Never touches git itself -- emits a real, structured JSON summary to
stdout ({"provider": ..., "excluded_resources": [...],
"excluded_data_sources": [...], "kept_paths": [...]}) that the calling
workflow uses to build both `git add` and its own step-summary/PR-body
text, so nothing has to re-derive this by parsing print() output.

rebuild_provider_index/rebuild_provider_nav (imported from
gen_provider_docs.py) print their own real progress lines -- fine for
their other caller, regen_pages.py, which has no stdout contract, but
this script's own stdout contract is pure JSON, one caller-visible
value. Everything before the final print() has to run under
redirect_stdout(sys.stderr) so a caller doing json.loads(stdout) isn't
handed those log lines ahead of the JSON blob and fail to parse them
as one value -- a real, found-live bug: every prior manual run of this
script LOOKED fine (the JSON was there, just preceded by real log
text a human skims past), and it was never actually fed through
json.loads by anything until regen_all.py's own real orchestration
run did exactly that and failed immediately.

Usage:
  python3 stage_gap_free.py <provider> [--scratch-dir /tmp/regen-scratch] [--docs-root PATH]
"""
import argparse
import contextlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOCS_ROOT = os.path.dirname(os.path.dirname(HERE))

sys.path.insert(0, HERE)
from gen_provider_docs import rebuild_provider_index, rebuild_provider_nav
from corpus_index import provider_group


def gapped_wires(coverage_result):
    """The real set of wire identities check_gaps found a gap for --
    missing_field_description entries are "wire.field_name", the wire
    itself is everything before the FIRST dot (a wire never contains
    one, only a field path appended after it does)."""
    if not coverage_result:
        return set()
    wires = set(coverage_result.get("missing_intro", [])) | set(coverage_result.get("missing_category", []))
    for entry in coverage_result.get("missing_field_description", []):
        wires.add(entry.split(".", 1)[0])
    return wires


def load_manifest(scratch_dir, filename):
    path = os.path.join(scratch_dir, filename)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def remove_data_source_page(doc, provider, page_path):
    """Surgical removal, not a full rebuild: gen_all_data_source_pages.py
    inserts a new page into a service subgroup's own "Data sources"
    sub-list via a real union merge (existing ∪ new), never a from-
    scratch derivation the way resource pages now have in
    rebuild_provider_nav -- undoing one excluded page the identical way
    it was added keeps this consistent with how that file already
    works, rather than introducing a second, differently-shaped nav
    mechanism for data sources alone."""
    removed = False
    for g in provider_group(doc, provider):
        pages = g.get("pages", [])
        if not (pages and isinstance(pages[0], dict)):
            continue
        data_sub = next((p for p in pages if p.get("group") == "Data sources"), None)
        if data_sub and page_path in data_sub.get("pages", []):
            data_sub["pages"].remove(page_path)
            removed = True
    return removed


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("provider")
    p.add_argument("--scratch-dir", default="/tmp/regen-scratch")
    p.add_argument("--docs-root", default=DEFAULT_DOCS_ROOT)
    p.add_argument("--provider-display", default=None,
                   help="required only if this provider's own resource manifest exists "
                        "(rebuild_provider_index/rebuild_provider_nav need it); "
                        "omit for a data-source-only run")
    args = p.parse_args()

    resource_manifest = load_manifest(args.scratch_dir, f"{args.provider}_regen_result.json")
    ds_manifest = load_manifest(args.scratch_dir, f"{args.provider}_datasource_regen_result.json")

    resource_wire_to_page = resource_manifest.get("wire_to_page", {})
    ds_wire_to_page = ds_manifest.get("wire_to_page", {})

    excluded_resources = sorted(gapped_wires(resource_manifest.get("coverage_result")))
    excluded_data_sources = sorted(gapped_wires(ds_manifest.get("coverage_result")))

    # This script's own stdout contract is pure JSON (see the module doc
    # comment) -- rebuild_provider_index/rebuild_provider_nav below print
    # their own real progress lines, so everything through the docs.json
    # write runs with stdout redirected to stderr, and only the final
    # summary print (outside this block) reaches real stdout.
    with contextlib.redirect_stdout(sys.stderr):
        deleted_paths = []
        for wire in excluded_resources:
            rel = resource_wire_to_page.get(wire)
            if rel is None:
                continue
            full = os.path.join(args.docs_root, rel)
            if os.path.exists(full):
                os.remove(full)
                deleted_paths.append(rel)

        docs_json_path = os.path.join(args.docs_root, "docs.json")
        doc = None
        for wire in excluded_data_sources:
            rel = ds_wire_to_page.get(wire)
            if rel is None:
                continue
            full = os.path.join(args.docs_root, rel)
            if os.path.exists(full):
                os.remove(full)
                deleted_paths.append(rel)
            if doc is None:
                with open(docs_json_path) as f:
                    doc = json.load(f)
            remove_data_source_page(doc, args.provider, rel)

        # Correct index.mdx and docs.json's own resource nav against the
        # real, post-exclusion tree -- only meaningful (and only possible:
        # provider_display is required) if this run touched resource pages
        # at all. A data-source-only run's own nav is already correct as
        # written, minus whatever this script just surgically removed above.
        if resource_wire_to_page:
            if not args.provider_display:
                sys.exit(f"stage_gap_free: {args.provider} has a resource manifest but no --provider-display given")
            rebuild_provider_index(docs_root=args.docs_root, provider=args.provider, provider_display=args.provider_display)
            if doc is None:
                with open(docs_json_path) as f:
                    doc = json.load(f)
            rebuild_provider_nav(docs_root=args.docs_root, doc=doc, provider=args.provider, provider_display=args.provider_display)

        if doc is not None:
            with open(docs_json_path, "w") as f:
                json.dump(doc, f, indent=2)
                f.write("\n")

    kept_paths = sorted(set(resource_wire_to_page.values()) | set(ds_wire_to_page.values()))
    kept_paths = [p for p in kept_paths if p not in deleted_paths]

    summary = {
        "provider": args.provider,
        "excluded_resources": excluded_resources,
        "excluded_data_sources": excluded_data_sources,
        "deleted_paths": deleted_paths,
        "kept_paths": kept_paths,
        "docs_json_touched": doc is not None,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
