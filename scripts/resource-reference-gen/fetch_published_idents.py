#!/usr/bin/env python3
"""UBI-185: computes bindings_status per resource, against freshly
fetched published state -- not a reused local clone, and not a
batch-level human decision made once and never revisited.

UBI-222: recovered. This file (PR #27, "docs/auto-bindings-status")
and its own real consumer wiring in gen_complete_pages.py (PR #26,
"docs/bindings-status-published") both showed MERGED via `gh pr view`
but were never actually reachable from main -- confirmed directly,
`git merge-base --is-ancestor` on both real merge commits against
origin/main returns false, and this file did not exist anywhere in a
fresh checkout. A real, live instance of the exact class PR #46
("recover PR #11/#12 -- lost content") already found and fixed once in
this same repo -- some real git-history mechanics (most likely a
stacked-branch base getting consumed before this PR's own merge, the
documented "a stacked PR is only safe while its base is unmerged"
trap) landed a real merge commit that never actually joined main's own
first-parent history. UBI-196's own later, real bindings_status flip
(e63f65b29) independently reimplemented the same real technique ad hoc
rather than reusing this file, since this file was never there to
reuse -- restored here verbatim from the original commit (fb516450d),
not rewritten, and wired into regen_pages.py's own real, live-fetch
path for a wire with no existing committed page. gen_complete_pages.py's
own "auto" mode consumer (PR #27's other real half) is NOT restored
here -- out of scope for this pass, a real, separate, still-open gap
for github/datadog's own bindings_status computation.

The real problem this closes: every bindings_status decision to date
(gcp_corrected_key's own removal, docs/bindings-status-published) was
a manual, one-time check against whatever was published on the day
someone ran it. aws/azure/github/datadog/kubernetes drifted stale
within one to six days, because nothing re-checked. GCP Compute's own
81-of-95 split already proved a provider-wide flag is too coarse --
this needs to be per resource, every real generation run, against
CURRENT live state.

fetch_fresh_clone always does a real network fetch -- clone if the
scratch path doesn't exist, hard-reset to origin's default branch if
it does -- deliberately never trusting a directory just because it's
already there. A stale reused clone would reintroduce the exact
problem this script exists to close, just with an extra layer of
appearing to check.

Usage (as a library, from gen_complete_pages.py's own --bindings-status
auto path):
    from fetch_published_idents import fresh_idents
    idents = fresh_idents("google", "https://github.com/Ubiquex/ubx-sdk-google.git", "/tmp/ubx-sdk-google-fresh")
    "google_billingbudgets_budget" in idents  # -> True/False, decided against what's live right now

Usage (standalone, matching extract_idents.py's own CLI shape):
    python3 fetch_published_idents.py google https://github.com/Ubiquex/ubx-sdk-google.git /tmp/ubx-sdk-google-fresh /tmp/google_idents.json
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_idents import scan_go, scan_py, scan_ts


def fetch_fresh_clone(repo_url, scratch_path):
    """Ensures scratch_path is a real, just-fetched checkout of repo_url's
    own default branch -- never a stale reuse. A directory that already
    exists at scratch_path is fetched and hard-reset, never trusted as
    already current."""
    if os.path.isdir(os.path.join(scratch_path, ".git")):
        subprocess.run(["git", "fetch", "origin"], cwd=scratch_path, check=True, capture_output=True)
        head = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
            cwd=scratch_path, check=True, capture_output=True, text=True,
        ).stdout.strip()
        subprocess.run(["git", "reset", "--hard", head], cwd=scratch_path, check=True, capture_output=True)
    else:
        subprocess.run(["git", "clone", "--depth", "1", repo_url, scratch_path], check=True, capture_output=True)
    return scratch_path


def fresh_idents(provider, repo_url, scratch_path):
    """Real, per-language identifier extraction against a FRESHLY fetched
    checkout -- the same real scan extract_idents.py already does, just
    never against a directory whose freshness wasn't just verified."""
    repo_root = fetch_fresh_clone(repo_url, scratch_path)
    go_root = os.path.join(repo_root, "sdk", "go")
    py_root = os.path.join(repo_root, "sdk", "python")
    ts_root = os.path.join(repo_root, "sdk", "typescript")

    go = scan_go(go_root, provider)
    py = scan_py(py_root, provider)
    ts = scan_ts(ts_root, provider)

    wires = set(go) | set(py) | set(ts)
    combined = {}
    for w in wires:
        if w in go and w in py and w in ts:
            combined[w] = {"go": go[w], "py": py[w], "ts": ts[w]}
        # A wire present in only one or two languages is NOT a real,
        # usable published resource for this purpose -- generate_one
        # needs all three to build a page's own Go/TS/Python tabs, so
        # a partial match is the same as no match: that resource stays
        # local_only, exactly like a wire absent from all three would.
    return combined


def main():
    provider, repo_url, scratch_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    idents = fresh_idents(provider, repo_url, scratch_path)
    json.dump(idents, open(out_path, "w"), indent=2)
    print(f"fetched fresh, {len(idents)} real published resources for {provider} -> {out_path}")


if __name__ == "__main__":
    main()
