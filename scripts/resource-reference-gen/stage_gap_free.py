#!/usr/bin/env python3
"""UBI-137: given a provider's own just-finished regen_pages.py and/or
gen_all_data_source_pages.py run, excludes -- never stages -- any
resource or data source whose own coverage gate found a gap, instead
of discarding the whole provider's batch whenever a handful of new
resources are still waiting on an intro, category, or description.
UBI-216's own decided chain: artifacts are mandatory, batches stay
small, and re-doing the same already-clean work every run while one
resource's artifact is still being written defeats the point of
automating this at all.

UBI-234: exclusion never deletes a page that was already published
before this run. Two real, distinct incidents (401 pages, then 214)
both destroyed real, previously-good content because a single, wrong
coverage-check result on a single run was treated as grounds to
delete -- both times the check itself turned out to be reading a
stale or racing view of reality, not a genuine gap in what was
already live. The fix is structural, not "be more careful about
staleness": an artifact-coverage miss (missing_intro/missing_category/
missing_field_description) now only ever withholds THIS run's own
fresh draft -- if the wire already had a real page at HEAD, that page
is restored to exactly what was already published (git checkout HEAD,
discarding this run's own draft for it) rather than removed, and the
gap keeps getting reported the same way it always has, for a human to
close. A wire with no prior page has nothing to lose, so it is simply
never written, the original, harmless behavior.

The other real removal signal, a page whose wire no longer has ANY
matching schema entry at all (a genuine upstream rename or removal,
not an artifact gap), never triggers a delete either -- it is recorded
in a real, checked-in per-provider candidates file
(artifacts/<provider>/removal_candidates.json) the first time it's
seen, and only reported as ready for a human to actually remove once
the SAME wire shows up orphaned again on a SEPARATE, later run (a
different --run-id, never just a second check within the same run).
A transient orphan (this run's own schema fetch was incomplete, a
name-collision disambiguation landed differently this time) self-heals
out of the candidates file the next time that wire matches again,
rather than lingering forever or ever triggering an automatic delete.

Reads both generators' own real manifests
({scratch-dir}/{provider}_regen_result.json,
{scratch-dir}/{provider}_datasource_regen_result.json) rather than
recomputing coverage a second time -- the exact check_gaps() result
each generator already ran against its own freshly-written batch,
before this script ever runs. Either manifest is optional (a provider
this run touched only for data sources, or only for resources, has
just the one).

Corrects docs.json and the provider's own index.mdx against the real,
post-exclusion file tree: rebuild_provider_index/rebuild_provider_nav
for resources (see rebuild_provider_nav's own doc comment for why this
has to re-run rather than trust the generator's own most recent call).
A restored page needs no special nav handling -- it is back on disk
exactly as it was, so the same fresh-tree scan that already runs here
finds and keeps it. A genuinely deleted (never-before-published) data
source page still gets its own surgical nav-entry removal, since
gen_all_data_source_pages.py's own docs.json write already ran,
unconditionally, before this script did.

Emits a real, structured JSON summary to stdout ({"provider": ...,
"excluded_resources": [...], "excluded_data_sources": [...],
"restored_paths": [...], "deleted_paths": [...],
"removal_candidates_new": [...], "removal_candidates_confirmed": [...],
"kept_paths": [...]}) that the calling workflow uses to build both
`git add` and its own step-summary/PR-body text, so nothing has to
re-derive this by parsing print() output.

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
  python3 stage_gap_free.py <provider> [--scratch-dir /tmp/regen-scratch] [--docs-root PATH] [--run-id ID]
"""
import argparse
import contextlib
import datetime
import json
import os
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOCS_ROOT = os.path.dirname(os.path.dirname(HERE))

sys.path.insert(0, HERE)
from gen_provider_docs import rebuild_provider_index, rebuild_provider_nav
from corpus_index import provider_group, scan_provider_corpus


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


def published_at_head(docs_root, rel_path):
    """True if rel_path was already a real, committed file at HEAD --
    i.e. genuinely published before this run touched it, not a brand
    new draft this run alone produced. `git cat-file -e` is the cheap,
    correct check: no working-tree read, no diff, just "does this path
    exist in the HEAD tree.\""""
    result = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{rel_path}"],
        cwd=docs_root, capture_output=True,
    )
    return result.returncode == 0


def restore_published(docs_root, rel_path):
    """Discards this run's own draft for rel_path, restoring exactly
    what was already committed at HEAD -- the real fix for both real
    incidents this exists to prevent: an artifact-coverage miss is
    never, by itself, grounds to lose content a reader can already
    reach."""
    subprocess.run(
        ["git", "checkout", "HEAD", "--", rel_path],
        cwd=docs_root, check=True,
    )


def load_removal_candidates(docs_root, provider):
    path = os.path.join(docs_root, "artifacts", provider, "removal_candidates.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_removal_candidates(docs_root, provider, candidates):
    path = os.path.join(docs_root, "artifacts", provider, "removal_candidates.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(candidates, f, indent=2, sort_keys=True)
        f.write("\n")


def update_removal_candidates(docs_root, provider, current_orphans, run_id):
    """current_orphans: {wire: rel_path} for every page still on disk
    this run whose wire matches no schema entry at all in either
    manifest this run read -- the real "might genuinely be gone"
    signal, distinct from an artifact-coverage miss.

    A wire is only ever reported ready for a human to remove once it
    shows up here on a run whose own run_id differs from the run that
    first recorded it -- never within the same run, and never on the
    strength of one run alone, since both real incidents this file
    guards against were single-run artifacts (a stale checkout, a
    same-run schema-fetch hiccup). A previously-recorded candidate
    that is no longer orphaned this run is dropped, not carried
    forward -- a transient miss should heal, not accumulate.

    Returns (new_this_run, confirmed_this_run), and persists the
    updated candidates file as a side effect."""
    candidates = load_removal_candidates(docs_root, provider)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    new_this_run = []
    confirmed_this_run = []
    updated = {}
    for wire, rel_path in sorted(current_orphans.items()):
        existing = candidates.get(wire)
        if existing is None:
            updated[wire] = {"path": rel_path, "first_seen_run": run_id, "first_seen_at": now}
            new_this_run.append(wire)
        elif existing.get("first_seen_run") != run_id:
            updated[wire] = existing
            confirmed_this_run.append(wire)
        else:
            # same run recorded this wire once already (both a
            # resource and data-source manifest touched it, or a
            # local/manual re-run reused a run_id) -- one run is still
            # only one signal.
            updated[wire] = existing

    save_removal_candidates(docs_root, provider, updated)
    return new_this_run, confirmed_this_run


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
    p.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID") or uuid.uuid4().hex,
                   help="identifies THIS run for the two-separate-runs removal-candidate check "
                        "below -- defaults to $GITHUB_RUN_ID in CI, a fresh random id otherwise, "
                        "so a local/manual invocation never accidentally confirms a real "
                        "candidate by coincidentally reusing another run's own id")
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
        restored_paths = []
        for wire in excluded_resources:
            rel = resource_wire_to_page.get(wire)
            if rel is None:
                continue
            full = os.path.join(args.docs_root, rel)
            if not os.path.exists(full):
                continue
            if published_at_head(args.docs_root, rel):
                # UBI-234: already real, already live -- an artifact
                # gap withholds this run's own draft, it does not cost
                # the reader the page that was already there.
                restore_published(args.docs_root, rel)
                restored_paths.append(rel)
            else:
                os.remove(full)
                deleted_paths.append(rel)

        docs_json_path = os.path.join(args.docs_root, "docs.json")
        doc = None
        for wire in excluded_data_sources:
            rel = ds_wire_to_page.get(wire)
            if rel is None:
                continue
            full = os.path.join(args.docs_root, rel)
            if not os.path.exists(full):
                continue
            if published_at_head(args.docs_root, rel):
                restore_published(args.docs_root, rel)
                restored_paths.append(rel)
                continue
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

        # UBI-234: the other real removal signal -- a page still on
        # disk whose wire matches no entry at all in this run's own
        # fresh schema, checked only for whichever category (resource,
        # data source) this run actually has a manifest for, never
        # inferred from an empty manifest meaning "nothing exists."
        # Never deletes; see update_removal_candidates's own doc
        # comment for the two-separate-runs rule.
        disk_wires = scan_provider_corpus(args.docs_root, args.provider)
        current_orphans = {}
        if resource_wire_to_page:
            for wire, info in disk_wires.items():
                if not wire.startswith("data_") and wire not in resource_wire_to_page:
                    current_orphans[wire] = info["path"]
        if ds_wire_to_page:
            for wire, info in disk_wires.items():
                if wire.startswith("data_") and wire not in ds_wire_to_page:
                    current_orphans[wire] = info["path"]
        removal_candidates_new, removal_candidates_confirmed = update_removal_candidates(
            args.docs_root, args.provider, current_orphans, args.run_id
        )

    kept_paths = sorted(set(resource_wire_to_page.values()) | set(ds_wire_to_page.values()))
    kept_paths = [p for p in kept_paths if p not in deleted_paths]

    summary = {
        "provider": args.provider,
        "excluded_resources": excluded_resources,
        "excluded_data_sources": excluded_data_sources,
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
        "removal_candidates_new": removal_candidates_new,
        "removal_candidates_confirmed": removal_candidates_confirmed,
        "kept_paths": kept_paths,
        "docs_json_touched": doc is not None,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
