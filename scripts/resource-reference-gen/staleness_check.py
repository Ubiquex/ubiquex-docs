"""UBI-200: is a directory's real, pinned schema source since superseded.

check_provenance's own bar (provenance_check.py) is "was this directory's
schema ever pinned at all" -- it has no way to tell a directory correctly
pinned to `1.0.0` from one pinned to `1.0.0` while `1.1.0` has since been
published. This is a genuinely different, live, external question, so
it lives in its own module (provenance_check.py's own check_staleness)
and its own runner here, never folded into check_provenance's hard
refusal -- staleness is warned about, matching this project's own
coverage-watch.yml posture, never a build-failing check.

Reads real, committed resource-reference/<provider>/PROVENANCE.json
files -- the same real artifact write_provenance_record already writes
during a real regen_pages.py/gen_all_data_source_pages.py batch, no new
interchange format. Compares each real recorded schema_version against
that schema repo's own real, current GitHub Release, queried live.

A real, honest limitation named explicitly, not glossed over: as of
2026-08-28, zero PROVENANCE.json files are committed anywhere in this
corpus yet -- the write path landed with UBI-199 and is real and
reachable (confirmed directly: both real drivers call it unconditionally
whenever a batch writes at least one page), it simply has not been
exercised by a full regeneration since. This script's own "found
nothing to check" state is reported as exactly that, loudly, distinct
from "checked everything and it's current" -- a check that reports
clean because it found zero real records is the same failure class as
a coverage check that reports clean because it looked in the wrong
place, and this project has hit that exact class of bug more than once
this session.

Exit codes: 0 clean (checked at least one real record, none stale),
1 real staleness found, 2 setup/execution error, 3 zero real
PROVENANCE.json files found -- distinct from 0, never silently folded
into "clean".
"""
import argparse
import glob
import os
import sys

from provenance_check import check_staleness

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def collect_committed_provenance(repo_root=REPO_ROOT):
    """Real, committed resource-reference/<provider>/PROVENANCE.json
    files on disk -- collect_provenance's own real shape (dir, record)
    pairs, reused directly rather than a second reader."""
    from provenance_check import collect_provenance

    paths = sorted(glob.glob(os.path.join(repo_root, "resource-reference", "*", "PROVENANCE.json")))
    dirs = [os.path.dirname(p) for p in paths]
    return collect_provenance(dirs)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo-root", default=REPO_ROOT, help="ubiquex-docs checkout root (default: this script's own real repo root)")
    args = p.parse_args()

    pairs = collect_committed_provenance(args.repo_root)
    found = [(d, rec) for d, rec in pairs if rec is not None]

    if not found:
        print(
            "staleness_check: zero real PROVENANCE.json files found under resource-reference/ -- "
            "NOTHING WAS CHECKED. This is not the same as clean. Either no full regeneration has "
            "run through regen_pages.py/gen_all_data_source_pages.py since the UBI-199 provenance "
            "fix landed, or this script is looking in the wrong place -- verify which before "
            "trusting a future clean run."
        )
        sys.exit(3)

    result = check_staleness(found)
    checked, stale, unknown = result["checked"], result["stale"], result["unknown"]

    for d, source, version in unknown:
        print(f"UNKNOWN {d}: {source}@{version} -- live query to the real schema repo failed (network/auth/rate-limit), not treated as clean")

    for d, source, recorded, latest in stale:
        print(f"STALE {d}: {source} pinned at {recorded}, real current latest is {latest}")

    for d, source, recorded, latest in checked:
        print(f"clean {d}: {source}@{recorded} matches the real current latest")

    print(
        f"\n{len(found)} real record(s) found, {len(checked)} current, "
        f"{len(stale)} stale, {len(unknown)} unknown (live query failed)"
    )

    if unknown and not stale:
        sys.exit(2)
    sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
