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
from provenance_check import ProvenanceError, check_provenance, collect_provenance, write_provenance_record

CLEAN = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False, "unpushed": False}
DIRTY = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": True, "unpushed": False}
UNPUSHED = {"source": "local-checkout", "repo_path": "/repo", "commit": "aaa111", "dirty": False, "unpushed": True}
OTHER_COMMIT = {"source": "local-checkout", "repo_path": "/repo", "commit": "bbb222", "dirty": False, "unpushed": False}


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

        dirs = make_dirs(root, [CLEAN, CLEAN])
        commit = check_provenance(collect_provenance(dirs))
        docs_root = os.path.join(root, "docs")
        out_path = write_provenance_record(docs_root, "fixture-provider", commit, "resource pages", extra={"families": 2})
        written = json.load(open(out_path))
        if written["ubx_provider_dynamic_commit"] != "aaa111" or written["artifact"] != "resource pages" or written["families"] != 2:
            print(f"FAIL write_provenance_record: wrong content written: {written}")
            sys.exit(1)
        print(f"PASS write_provenance_record: {out_path} -> {written}")

        print("\nALL PASS")
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
