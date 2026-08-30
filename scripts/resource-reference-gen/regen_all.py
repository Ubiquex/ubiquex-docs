#!/usr/bin/env python3
"""UBI-137: orchestrates a full, real resource-reference regeneration
across every declared provider, gap-aware -- the automation UBI-216's
own decided chain calls for once artifacts are written. Assumes the
caller (a CI workflow, or a human running this by hand) has already
built ubx, dumped --dump-ir for every provider, and generated fresh
local go/py/ts bindings -- the identical real steps golden-page-gate.yml
already does, in the identical directory shape, so this script's own
job is orchestrating the generators against that already-prepared
input, not preparing it itself.

Four providers (aws, azure, gcp, kubernetes) get real resource-page
regeneration via regen_pages.py. github/datadog do not yet -- their own
ongoing regen uses a different, less mature mechanism (gen_complete_pages.py's
own generate_one, which splices onto an already-generated page rather
than a real full-corpus rescan) this automation does not cover. A real,
named gap, reported in every run's own summary, not a silent omission.

All six providers get data-source page regeneration via
gen_all_data_source_pages.py, which only needs an already-existing
resource nav group to nest under, never this run's own resource regen.

Every provider this run touches is reported, gap-free or not -- a
provider this run found nothing new for is not the same as a provider
this run never checked, and a report that only speaks when something
changed reads identically to a report that isn't running.

Refuses outright if UBX_DOCS_ALLOW_COVERAGE_GAPS is set in its own
environment -- that override exists for a human running a deliberate,
one-off experiment, never for this script, which excludes gapped
resources instead of ever needing to override the gate at all.

Today's real, confirmed config (sdk/providers/.ubx/config in ubiquex)
carries exactly one [dynamic_providers.<name>] entry per provider for
all six -- no per-family entries exist for gcp/azure anymore (that was
an earlier config shape regen_pages.py's own doc comment still
describes historically). families_file is therefore always a single
line naming that one family, identical to the provider's own
--dump-root/--local-sdk-root directory name -- this script writes it
itself rather than taking it as an external input, since there is
nothing left to enumerate.

Usage:
  python3 regen_all.py --dump-root DIR --local-sdk-root DIR \\
      --docs-root DIR [--only aws,kubernetes]

Emits one real, structured JSON report to stdout:
  {"results": [{"provider": ..., "status": "ok"|"error", "resource_regen":
  {"exit_code": ...}|null, "datasource_regen": {...}|null, "stage":
  {"excluded_resources": [...], "excluded_data_sources": [...],
  "kept_paths": [...]}|null, "stage_error": "..."|absent}, ...],
  "not_covered": ["github", "datadog"]}
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Hardcoded, not a CLI flag -- regen_pages.py and gen_all_data_source_pages.py
# both hardcode this same path internally with no override, so a
# different value here would silently orphan their manifests rather
# than relocating them.
SCRATCH_DIR = "/tmp/regen-scratch"

# provider -> real, human display name (rebuild_provider_index/
# rebuild_provider_nav's own required arg) -- only for the four
# providers regen_pages.py covers; the other two run data-source-only.
RESOURCE_REGEN_PROVIDERS = {
    "aws": "AWS",
    "azure": "Microsoft Azure",
    "gcp": "Google Cloud",
    "kubernetes": "Kubernetes",
}
DATA_SOURCE_ONLY_PROVIDERS = ["github", "datadog"]
ALL_PROVIDERS = ["aws", "azure", "gcp", "kubernetes", "github", "datadog"]

# gcp's own docs-internal key differs from the real published SDK repo's
# own short name ("google") that --dump-root/--local-sdk-root are
# actually keyed by (sdk/providers/.ubx/config's own real naming rule,
# UBI-102's own confirmed precedent) -- every other provider's two names
# already match.
SCHEMA_NAME = {"gcp": "google"}


def run(cmd, **kw):
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, **kw)


def regen_provider(provider, args):
    schema_name = SCHEMA_NAME.get(provider, provider)
    # A real dump/local-sdk run (ubx sdk gen --only <schema_name> --dump-ir/--lang
    # ..., matching golden-page-gate.yml's own real pattern) writes directly to
    # <root>/<schema_name>/... -- gen_all_data_source_pages.py's own dump_dir/go_root
    # args want exactly that directory. regen_pages.py's own dump_dir/sdk_dir args
    # are shaped differently: it appends `family` (== schema_name here, since
    # today's config has exactly one family per provider, see this file's own doc
    # comment) itself, so IT needs the plain root one level up -- passing the
    # already-joined directory there double-nests and regen_pages.py silently
    # finds no schema.json for the family (confirmed live: a real test run against
    # kubernetes reported "1 families skipped entirely: [('kubernetes', 'no
    # dump-ir schema.json')]" before this was caught).
    dump_dir = os.path.join(args.dump_root, schema_name)
    local_sdk = os.path.join(args.local_sdk_root, schema_name)
    go_root = os.path.join(local_sdk, "sdk", "go")

    result = {"provider": provider, "resource_regen": None, "datasource_regen": None, "stage": None, "status": "ok"}

    if provider in RESOURCE_REGEN_PROVIDERS:
        os.makedirs(SCRATCH_DIR, exist_ok=True)
        families_file = os.path.join(SCRATCH_DIR, f"families_{provider}.txt")
        with open(families_file, "w") as f:
            f.write(schema_name + "\n")
        p = run(["python3", os.path.join(HERE, "regen_pages.py"), provider, args.dump_root, args.local_sdk_root, families_file], cwd=HERE)
        result["resource_regen"] = {"exit_code": p.returncode}
        # 0 (clean) or 1 (real gap, UBI-187's own refusal) are both real,
        # expected outcomes this script handles below via stage_gap_free.py
        # -- anything else is a genuine tooling failure (a crash, a bad
        # invocation), not a gap.
        if p.returncode not in (0, 1):
            result["status"] = "error"
            return result

    p = run(["python3", os.path.join(HERE, "gen_all_data_source_pages.py"), provider, dump_dir, go_root], cwd=HERE)
    result["datasource_regen"] = {"exit_code": p.returncode}
    if p.returncode not in (0, 1):
        result["status"] = "error"
        return result

    stage_cmd = ["python3", os.path.join(HERE, "stage_gap_free.py"), provider, "--docs-root", args.docs_root]
    if provider in RESOURCE_REGEN_PROVIDERS:
        stage_cmd += ["--provider-display", RESOURCE_REGEN_PROVIDERS[provider]]
    p = run(stage_cmd, cwd=HERE, capture_output=True, text=True)
    if p.returncode != 0:
        result["status"] = "error"
        result["stage_error"] = p.stderr
        return result
    result["stage"] = json.loads(p.stdout)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dump-root", required=True, help="root of a real --dump-ir run, <root>/<schema-name>/schema.json per provider")
    p.add_argument("--local-sdk-root", required=True, help="root of a real --lang go/py/ts run, <root>/<schema-name>/sdk/{go,python,typescript}")
    p.add_argument("--docs-root", required=True)
    p.add_argument("--only", default=None, help="comma-separated provider subset, default: all six")
    args = p.parse_args()

    if os.environ.get("UBX_DOCS_ALLOW_COVERAGE_GAPS"):
        sys.exit(
            "regen_all.py: UBX_DOCS_ALLOW_COVERAGE_GAPS is set -- refusing to run under it. "
            "That override exists for a human running a deliberate, one-off experiment, never "
            "for an automated chain -- this script excludes gapped resources instead of "
            "overriding the gate, exactly so nothing here ever needs it."
        )

    providers = args.only.split(",") if args.only else ALL_PROVIDERS

    results = [regen_provider(provider, args) for provider in providers]

    print(json.dumps({"results": results, "not_covered": DATA_SOURCE_ONLY_PROVIDERS}, indent=2))

    if any(r["status"] == "error" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
