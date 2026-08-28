#!/usr/bin/env python3
"""Real, hermetic verification for provenance_check.py -- constructs real
PROVENANCE.json fixtures on disk (the exact shape ubx sdk gen writes,
verified against this session's own real, live-tested output) and
exercises every real branch: all clean, one missing, one dirty, one
unpushed, two disagreeing commits, and the allow_dirty escape hatch.
No mocks -- real files, real json, matching this directory's own
verify_*.py convention (verify_scope_guard.py, verify_regen_corpus.py).

Usage: python3 verify_provenance_check.py
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from provenance_check import ProvenanceError, check_provenance, check_staleness, collect_provenance, schema_provenance_of, write_provenance_record

# UBI-199: every fixture below carries a real, pinned schema_pinned/
# schema_source/schema_version -- these existing cases are about the
# TOOL-provenance checks (dirty/unpushed/disagreeing commit), so they
# need to stay pinned-clean on the schema axis or the new check (added
# below, tested separately) would refuse them for an unrelated reason.
CLEAN = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False, "unpushed": False,
         "schema_pinned": True, "schema_source": "ubiquex/azure", "schema_version": "1.0.0"}
DIRTY = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": True, "unpushed": False,
         "schema_pinned": True, "schema_source": "ubiquex/azure", "schema_version": "1.0.0"}
UNPUSHED = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False, "unpushed": True,
            "schema_pinned": True, "schema_source": "ubiquex/azure", "schema_version": "1.0.0"}
OTHER_COMMIT = {"source": "local-checkout", "repo_path": "/repo", "commit": "bbb222", "dirty": False, "unpushed": False,
                "schema_pinned": True, "schema_source": "ubiquex/azure", "schema_version": "1.0.0"}

# UBI-199: schema-provenance-specific fixtures.
NO_SCHEMA_FIELD = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False, "unpushed": False}
LIVE_SCHEMA = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False, "unpushed": False,
               "schema_pinned": False, "schema_url": "https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/x.json"}
PINNED_OTHER_VERSION = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False, "unpushed": False,
                         "schema_pinned": True, "schema_source": "ubiquex/azure", "schema_version": "0.9.0"}


_case_counter = [0]


def make_dirs(root, records):
    # Each call gets its own fresh case subdirectory -- reusing bare
    # "d0"/"d1" names across calls left a stale PROVENANCE.json from an
    # earlier case's "clean" dir sitting where a later case's "missing"
    # dir expected none, a real bug this comment exists because it was
    # caught live running this exact script.
    _case_counter[0] += 1
    case_root = os.path.join(root, f"case{_case_counter[0]}")
    dirs = []
    for i, rec in enumerate(records):
        d = os.path.join(case_root, f"d{i}")
        os.makedirs(d, exist_ok=True)
        if rec is not None:
            with open(os.path.join(d, "PROVENANCE.json"), "w") as fh:
                json.dump(rec, fh)
        dirs.append(d)
    return dirs


def expect_ok(label, fn):
    try:
        result = fn()
        print(f"PASS {label}: {result}")
    except Exception as e:
        print(f"FAIL {label}: expected success, got {type(e).__name__}: {e}")
        sys.exit(1)


def expect_error(label, fn, must_contain=None):
    try:
        result = fn()
        print(f"FAIL {label}: expected ProvenanceError, got success: {result}")
        sys.exit(1)
    except ProvenanceError as e:
        if must_contain and must_contain not in str(e):
            print(f"FAIL {label}: error didn't mention {must_contain!r}: {e}")
            sys.exit(1)
        print(f"PASS {label}: refused as expected ({e})")
    except Exception as e:
        print(f"FAIL {label}: expected ProvenanceError, got {type(e).__name__}: {e}")
        sys.exit(1)


def main():
    root = tempfile.mkdtemp(prefix="provcheck-")
    try:
        dirs = make_dirs(root, [CLEAN, CLEAN, CLEAN])
        expect_ok("all clean, same commit", lambda: check_provenance(collect_provenance(dirs)))

        dirs = make_dirs(root, [CLEAN, None, CLEAN])
        expect_error("one missing", lambda: check_provenance(collect_provenance(dirs)), "no PROVENANCE.json")

        dirs = make_dirs(root, [CLEAN, DIRTY])
        expect_error("one dirty", lambda: check_provenance(collect_provenance(dirs)), "unclean provenance")

        dirs = make_dirs(root, [CLEAN, UNPUSHED])
        expect_error("one unpushed", lambda: check_provenance(collect_provenance(dirs)), "unclean provenance")

        dirs = make_dirs(root, [CLEAN, OTHER_COMMIT])
        expect_error("disagreeing commits", lambda: check_provenance(collect_provenance(dirs)), "disagree on commit")

        dirs = make_dirs(root, [CLEAN, DIRTY])
        expect_ok("dirty allowed via allow_dirty=True", lambda: check_provenance(collect_provenance(dirs), allow_dirty=True))

        # UBI-199: schema-source provenance -- the whole reason it exists,
        # a live fetch was invisible to every check above (a clean, pushed
        # tool commit says nothing about the schema it fetched).
        dirs = make_dirs(root, [CLEAN, NO_SCHEMA_FIELD])
        expect_error("one missing schema_pinned field (pre-UBI-199 record)",
                     lambda: check_provenance(collect_provenance(dirs)), "unpinned schema provenance")

        dirs = make_dirs(root, [CLEAN, LIVE_SCHEMA])
        expect_error("one real live schema_url fetch",
                     lambda: check_provenance(collect_provenance(dirs)), "unpinned schema provenance")

        dirs = make_dirs(root, [CLEAN, PINNED_OTHER_VERSION])
        expect_error("two real pinned sources disagreeing on version",
                     lambda: check_provenance(collect_provenance(dirs)), "disagree on schema source/version")

        dirs = make_dirs(root, [CLEAN, LIVE_SCHEMA])
        expect_ok("live schema allowed via allow_unpinned_schema=True",
                  lambda: check_provenance(collect_provenance(dirs), allow_unpinned_schema=True))

        dirs = make_dirs(root, [CLEAN, CLEAN])
        pairs = collect_provenance(dirs)
        check_provenance(pairs)
        schema_source, schema_version = schema_provenance_of(pairs)
        if schema_source != "ubiquex/azure" or schema_version != "1.0.0":
            print(f"FAIL schema_provenance_of: got ({schema_source!r}, {schema_version!r}), want the real, agreed pin")
            sys.exit(1)
        print(f"PASS schema_provenance_of: ({schema_source}, {schema_version})")

        dirs = make_dirs(root, [CLEAN, CLEAN])
        commit = check_provenance(collect_provenance(dirs))
        docs_root = os.path.join(root, "docs")
        out_path = write_provenance_record(docs_root, "fixture-provider", commit, "resource pages",
                                            extra={"families": 2, "schema_source": "ubiquex/azure", "schema_version": "1.0.0"})
        written = json.load(open(out_path))
        if (written["ubx_provider_dynamic_commit"] != "aaa111" or written["artifact"] != "resource pages"
                or written["families"] != 2 or written["schema_source"] != "ubiquex/azure" or written["schema_version"] != "1.0.0"):
            print(f"FAIL write_provenance_record: wrong content written: {written}")
            sys.exit(1)
        print(f"PASS write_provenance_record: {out_path} -> {written}")

        # UBI-200: check_staleness's own real classification logic,
        # exercised hermetically via a real, deterministic fake
        # fetch_latest -- no mocking framework, a plain injected
        # function, matching this file's own "no mocks" convention
        # just moved to the network boundary's own real seam.
        def fake_fetch_latest(source):
            return {
                "ubiquex/azure": "v1.0.0",   # matches CLEAN's own real pin -> checked
                "ubiquex/stale-provider": "v2.0.0",  # disagrees -> stale
            }.get(source)  # anything else -> None -> unknown

        STALE_REC = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False,
                     "unpushed": False, "schema_pinned": True, "schema_source": "ubiquex/stale-provider",
                     "schema_version": "1.0.0"}
        UNKNOWN_SOURCE_REC = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False,
                               "unpushed": False, "schema_pinned": True, "schema_source": "ubiquex/no-such-repo",
                               "schema_version": "1.0.0"}

        dirs = make_dirs(root, [CLEAN, STALE_REC, UNKNOWN_SOURCE_REC, LIVE_SCHEMA])
        pairs = collect_provenance(dirs)
        result = check_staleness(pairs, fetch_latest=fake_fetch_latest)
        if len(result["checked"]) != 1 or result["checked"][0][1] != "ubiquex/azure":
            print(f"FAIL check_staleness checked: {result['checked']}")
            sys.exit(1)
        if len(result["stale"]) != 1 or result["stale"][0][1] != "ubiquex/stale-provider" or result["stale"][0][3] != "2.0.0":
            print(f"FAIL check_staleness stale: {result['stale']}")
            sys.exit(1)
        if len(result["unknown"]) != 1 or result["unknown"][0][1] != "ubiquex/no-such-repo":
            print(f"FAIL check_staleness unknown: {result['unknown']}")
            sys.exit(1)
        # LIVE_SCHEMA's own record has schema_pinned=False -- must be
        # skipped entirely, never counted as checked/stale/unknown.
        total_seen = len(result["checked"]) + len(result["stale"]) + len(result["unknown"])
        if total_seen != 3:
            print(f"FAIL check_staleness: unpinned record leaked into results, total_seen={total_seen}")
            sys.exit(1)
        print(f"PASS check_staleness: {len(result['checked'])} checked, {len(result['stale'])} stale, {len(result['unknown'])} unknown, unpinned correctly excluded")

        print("\nALL PASS")
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
