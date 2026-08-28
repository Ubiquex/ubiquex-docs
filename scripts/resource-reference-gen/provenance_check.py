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

UBI-199: a real, separate, distinct failure mode found live -- a tool
checkout being clean and pushed says nothing about whether the SCHEMA
it fetched was pinned or live. Azure's own real upstream OpenAPI spec
moved between two separate `ubx sdk gen` invocations (--dump-ir,
--lang go --out) run minutes apart, against a genuinely clean tool
commit both times -- the tool-only check above passed cleanly while the
two invocations silently disagreed on which wires were resources vs.
data sources, which is what produced 908 miscategorized docs pages.
`ubx sdk gen` now also stamps schema_pinned/schema_source/
schema_version (or schema_url when live) into the same PROVENANCE.json,
per provider -- this module refuses on an unpinned or missing value the
same way it already refuses on dirty/missing tool provenance. Missing
is deliberate: every PROVENANCE.json written before this fix has no
schema_pinned key at all, and that must read as unknown, never as
implicitly pinned.
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


def check_provenance(pairs, allow_dirty=False, allow_unpinned_schema=False):
    """pairs: collect_provenance's own real output. Refuses (raises
    ProvenanceError) unless every directory has a real record, every
    record confirms a clean(): local-checkout, not dirty, not unpushed
    (allow_dirty=True downgrades dirty/unpushed to a warning instead --
    real escape hatch for a deliberate local experiment, never the
    default for a real batch meant to be committed), every clean record
    names the SAME real commit -- a batch drawing from two different
    real commits is not one coherent corpus, even if each half is
    individually clean -- AND (UBI-199) every record's own schema was
    genuinely pinned (allow_unpinned_schema=True downgrades this to a
    warning too, the identical real escape hatch, never the default),
    agreeing on the SAME real source/version -- a batch where even one
    real member fetched its schema live, or where members were pinned
    to genuinely different versions, is not one coherent, reproducible
    corpus either, the same real reasoning as the commit check just
    applied one layer up.

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

    # UBI-199: schema_pinned absent (every real PROVENANCE.json written
    # before this fix) or explicitly False both mean "not pinned" here --
    # a missing key is never treated as implicitly pinned.
    unpinned = [(d, rec) for d, rec in pairs if not rec.get("schema_pinned")]
    if unpinned and not allow_unpinned_schema:
        d, rec = unpinned[0]
        reason = "no schema_pinned field at all (generated before UBI-199's provenance fix)" if "schema_pinned" not in rec else (
            f"schema_url={rec.get('schema_url')!r} (a real, live, unpinned fetch)"
        )
        raise ProvenanceError(
            f"{len(unpinned)} of {len(pairs)} real directories carry unpinned schema provenance "
            f"-- first: {d} ({reason}). This batch produces a real, published artifact whose two "
            f"separate ubx sdk gen invocations (--dump-ir, --lang go --out) must see byte-identical "
            f"input to agree with each other -- a live schema_url fetch can drift between the two "
            f"runs even against a clean, pinned tool commit (UBI-197's own real Azure finding). "
            f"Re-run against a pinned [dynamic_providers.<name>] entry (source/version, see "
            f"sdk/providers/.ubx/config), or pass allow_unpinned_schema=True for a deliberate local "
            f"experiment that will never be committed."
        )

    schema_pins = {
        (rec.get("schema_source"), rec.get("schema_version"))
        for d, rec in pairs if rec.get("schema_pinned")
    }
    if len(schema_pins) > 1:
        raise ProvenanceError(
            f"real directories in this batch disagree on schema source/version: "
            f"{sorted(schema_pins)} -- this batch is not one coherent, reproducible fetch. "
            f"Re-run the whole batch against one real, pinned source/version."
        )

    return next(iter(commits)) if commits else None


def schema_provenance_of(pairs):
    """The single, agreed-on (schema_source, schema_version) pair across
    pairs -- callers use this AFTER check_provenance has already
    confirmed the batch agrees, to thread the real pin into their own
    write_provenance_record's extra dict. (None, None) when nothing in
    pairs is pinned -- only reachable when check_provenance was called
    with allow_unpinned_schema=True."""
    pins = {
        (rec.get("schema_source"), rec.get("schema_version"))
        for d, rec in pairs if rec and rec.get("schema_pinned")
    }
    if not pins:
        return None, None
    return next(iter(pins))


def real_latest_schema_release(schema_source):
    """schema_source is the real, recorded pin string (`"ubiquex/aws"`) --
    its own second segment IS the real `ubx-schema-<name>` repo's short
    name, no separate mapping table needed (`resource-reference/`'s own
    directory name for a provider can differ, `gcp` vs. the real
    `ubiquex/google` pin, confirmed live -- reading straight out of the
    recorded string avoids a second, potentially-disagreeing source of
    truth for that mapping). Returns the real, current latest release
    tag (e.g. `"v1.1.0"`), or None if the live query itself failed
    (network, auth, rate limit, or a schema repo with no releases yet)
    -- None is a real "unknown", never treated as "not stale" by a
    caller (UBI-200's own point: a check that can't tell must say so,
    not default to "clean").
    """
    import subprocess

    name = schema_source.split("/")[-1] if schema_source else None
    if not name:
        return None
    out = subprocess.run(
        ["gh", "api", f"repos/Ubiquex/ubx-schema-{name}/releases/latest", "--jq", ".tag_name"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def check_staleness(pairs, fetch_latest=real_latest_schema_release):
    """UBI-200: check_provenance's own real bar is "was this directory's
    schema ever pinned" -- it has no way to tell a directory pinned to
    `1.0.0` from one pinned to `1.0.0` while `1.1.0` has since been
    published. This is a genuinely different, live, external question
    ("is there a newer real snapshot now"), so it is checked here,
    separately, never folded into check_provenance's own hard refusal
    -- the comparison target is each real `ubx-schema-<name>` repo's
    own current GitHub Release, queried live, NOT `ubiquex`'s own
    `sdk/providers/.ubx/config` (confirmed, not assumed: `ubiquex`'s
    own pin can itself lag a schema repo's real latest release, which
    would make that comparison target report false-clean on exactly
    the case this check exists to catch, and it would only relocate
    this same staleness problem one repo up rather than closing it).

    fetch_latest is injectable (defaults to the real, live
    real_latest_schema_release) so this function's own real
    classification logic (checked/stale/unknown) can be exercised
    hermetically against a real, deterministic fake, without mocking
    the network boundary itself -- matching this file's own "no mocks"
    testing convention, just moving the seam to a plain function
    parameter instead.

    pairs: collect_provenance's own real output. Returns a dict with
    three real, DISTINCT lists, never collapsed into one pass/fail
    verdict, because "found nothing to check" and "checked everything
    and it's current" are different states a caller must be able to
    tell apart (the same failure class as a coverage check reporting
    clean because it found zero pages, or a filter reporting zero
    matches because it looked in the wrong place):

    - "checked": (dir, schema_source, recorded_version, latest_version)
      for every real record whose live query succeeded and versions
      match
    - "stale": the same shape, for every real record whose recorded
      version disagrees with the real, current latest
    - "unknown": (dir, schema_source, recorded_version) for every real
      record whose live query itself failed -- reported, never
      silently treated as either stale or clean
    """
    checked, stale, unknown = [], [], []
    seen_sources = {}
    for d, rec in pairs:
        if not rec or not rec.get("schema_pinned"):
            continue
        source = rec.get("schema_source")
        version = rec.get("schema_version")
        if not source or not version:
            continue
        if source not in seen_sources:
            seen_sources[source] = fetch_latest(source)
        latest = seen_sources[source]
        if latest is None:
            unknown.append((d, source, version))
            continue
        latest_stripped = latest.lstrip("v")
        if latest_stripped != version:
            stale.append((d, source, version, latest_stripped))
        else:
            checked.append((d, source, version, latest_stripped))
    return {"checked": checked, "stale": stale, "unknown": unknown}


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
