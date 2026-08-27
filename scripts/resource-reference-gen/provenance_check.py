"""UBI-197: real provenance checking for the docs corpus's own real
generation drivers (regen_pages.py for resources, gen_all_data_source_
pages.py for data sources).

Real root cause this closes: the published data-source corpus was built
from a real, unmerged WIP branch that was live in ubx-provider-dynamic's
local checkout for under an hour, with nothing anywhere recording that
it happened -- confirmed live by comparing a preserved real dump
(/tmp/docs-dump, still on disk) against the checkout's own git history.
`ubx sdk gen` now writes a real PROVENANCE.json (source, commit, dirty,
unpushed) as a sibling of every real dump-ir output directory and every
real --out repo directory it produces -- this module reads those files
back, the same real artifacts the drivers already consume, no new
interchange format.

Real, distinct failure mode this module also catches that a single
provenance check could not: resource/data-source page generation both
need TWO separate real `ubx sdk gen` invocations per family/provider
(one --dump-ir, one --lang go --out, run as separate processes) -- if
those two runs happen far enough apart to land on different commits,
each one's own PROVENANCE.json is individually clean, but the corpus
they jointly produce is not coherent. Checking that every real
PROVENANCE.json found across a whole batch agrees on one commit catches
this, not just "was any single one dirty".

Refuses by default -- this produces a real, committed, published
artifact (the docs corpus), the same posture CI's own
--require-clean-provenance already established for the six
ubx-sdk-<provider> repos, not the interactive-local-iteration posture
`ubx sdk gen`'s own bare invocation defaults to.
"""
import json
import os


class ProvenanceError(RuntimeError):
    """Raised when a batch's own real provenance can't be confirmed --
    missing, dirty, unpushed, or internally disagreeing. Callers should
    let this propagate (sys.exit via an uncaught exception, matching
    this codebase's own "refuse loudly, never silently proceed"
    discipline for a real batch generation), not swallow it."""


def _read_provenance(path):
    """Reads one real PROVENANCE.json ubx sdk gen wrote -- returns None
    if it's genuinely missing (a real, reportable gap, not the same as
    a present-but-unclean record)."""
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def collect_provenance(dirs):
    """dirs: real directories that should each carry a real PROVENANCE.json
    at <dir>/PROVENANCE.json (a dump-ir output directory or a --out repo
    directory -- ubx sdk gen writes the identical shape to both). Returns
    a list of (dir, record_or_None) pairs, in the order given -- callers
    that need to report WHICH directories are missing one keep that
    context this way, rather than collapsing straight to a verdict.
    """
    return [(d, _read_provenance(os.path.join(d, "PROVENANCE.json"))) for d in dirs]


def check_provenance(pairs, allow_dirty=False):
    """pairs: collect_provenance's own real output. Refuses (raises
    ProvenanceError) unless every directory has a real record, every
    record confirms a clean(): local-checkout, not dirty, not unpushed
    (allow_dirty=True downgrades dirty/unpushed to a warning instead --
    real escape hatch for a deliberate local experiment, never the
    default for a real batch meant to be committed), and every clean
    record names the SAME real commit -- a batch drawing from two
    different real commits is not one coherent corpus, even if each half
    is individually clean.

    Returns the single, agreed-on commit string on success.
    """
    missing = [d for d, rec in pairs if rec is None]
    if missing:
        raise ProvenanceError(
            f"{len(missing)} of {len(pairs)} real directories have no PROVENANCE.json "
            f"(ubx sdk gen must have run without this session's own provenance fix) -- "
            f"first few: {missing[:5]}"
        )

    unclean = []
    commits = set()
    for d, rec in pairs:
        is_clean = rec.get("source") == "local-checkout" and not rec.get("dirty") and not rec.get("unpushed")
        if not is_clean:
            unclean.append((d, rec))
        commit = rec.get("commit")
        if commit:
            commits.add(commit)

    if unclean and not allow_dirty:
        d, rec = unclean[0]
        raise ProvenanceError(
            f"{len(unclean)} of {len(pairs)} real directories carry unclean provenance "
            f"(source={rec.get('source')!r} dirty={rec.get('dirty')} unpushed={rec.get('unpushed')}) -- "
            f"first: {d}. This batch produces a real, published artifact -- refusing rather than "
            f"silently baking in content that can't be traced to a real, fetchable commit. "
            f"Re-run against a clean, pushed ubx-provider-dynamic checkout, or pass allow_dirty=True "
            f"for a deliberate local experiment that will never be committed."
        )

    if len(commits) > 1:
        raise ProvenanceError(
            f"real directories in this batch disagree on commit: {sorted(commits)} -- "
            f"this usually means the --dump-ir run and the --lang go --out run (or two --dump-ir "
            f"runs across different families) happened far enough apart to land on different real "
            f"ubx-provider-dynamic commits. Re-run the whole batch back-to-back against one commit."
        )

    return next(iter(commits)) if commits else None


def write_provenance_record(docs_root, provider_key, commit, artifact, extra=None):
    """Writes the real, committed resource-reference/<provider_key>/
    PROVENANCE.json this batch's own check_provenance just confirmed --
    the docs repo's own equivalent of each ubx-sdk-<provider> repo's real
    committed PROVENANCE.json (this session's own prior fix), so a future
    session can trace the PUBLISHED page content back to the exact real
    commit that produced it, not just infer it from file mtimes the way
    this whole investigation had to.
    """
    out_dir = os.path.join(docs_root, "resource-reference", provider_key)
    os.makedirs(out_dir, exist_ok=True)
    record = {
        "ubx_provider_dynamic_commit": commit,
        "artifact": artifact,
    }
    if extra:
        record.update(extra)
    out_path = os.path.join(out_dir, "PROVENANCE.json")
    with open(out_path, "w") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    return out_path
