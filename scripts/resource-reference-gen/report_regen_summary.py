#!/usr/bin/env python3
"""UBI-137: turns regen_all.py's own structured JSON report into the two
real, human-facing texts the workflow needs -- a $GITHUB_STEP_SUMMARY
body and (only when something was actually staged) a PR body -- so
neither has to be hand-built inline in YAML. Kept as testable Python,
matching this project's own tooling convention, rather than shell string
munging.

Both outputs always name every provider this run touched, whether or
not anything changed for it: UBI-137's own design report called out
that a run which only speaks when something changed reads identically
to a run that isn't running, and that is exactly the failure mode this
script's own output has to refuse to reproduce.

Usage:
  python3 report_regen_summary.py --report /path/to/regen-report.json \\
      --step-summary-out /path/to/summary.md --pr-body-out /path/to/pr-body.md
"""
import argparse
import json


def format_provider(r):
    provider = r["provider"]
    if r["status"] == "error":
        lines = [f"### {provider}: FAILED"]
        if r.get("resource_regen"):
            lines.append(f"- resource regen exit code: {r['resource_regen']['exit_code']}")
        if r.get("datasource_regen"):
            lines.append(f"- data-source regen exit code: {r['datasource_regen']['exit_code']}")
        if r.get("stage_error"):
            lines.append(f"- stage_gap_free.py error:\n```\n{r['stage_error'].strip()}\n```")
        return lines

    stage = r.get("stage") or {}
    excluded_resources = stage.get("excluded_resources", [])
    excluded_data_sources = stage.get("excluded_data_sources", [])
    restored = stage.get("restored_paths", [])
    removal_new = stage.get("removal_candidates_new", [])
    removal_confirmed = stage.get("removal_candidates_confirmed", [])
    kept = stage.get("kept_paths", [])
    lines = [f"### {provider}"]
    lines.append(f"- pages kept this run: {len(kept)}")
    if excluded_resources:
        lines.append(f"- **blocked** on {len(excluded_resources)} resource(s) missing an intro/category/field description: {', '.join(excluded_resources)}")
    if excluded_data_sources:
        lines.append(f"- **blocked** on {len(excluded_data_sources)} data source(s) missing an intro/category/field description: {', '.join(excluded_data_sources)}")
    if not excluded_resources and not excluded_data_sources:
        lines.append("- clean: no coverage gaps in this run's own batch")
    if restored:
        lines.append(
            f"- **{len(restored)} already-published page(s) kept as-is, not this run's own draft** "
            f"(UBI-234: an artifact-coverage miss never deletes a real, previously-published page, "
            f"it only withholds this run's own fresh content for it): {', '.join(restored)}"
        )
    if removal_confirmed:
        lines.append(
            f"- **{len(removal_confirmed)} page(s) confirmed orphaned across two separate runs, "
            f"ready for a human to actually remove** (no matching schema entry either time, never "
            f"auto-deleted): {', '.join(removal_confirmed)}"
        )
    if removal_new:
        lines.append(
            f"- {len(removal_new)} page(s) newly look orphaned this run, not yet confirmed "
            f"(need to show up again on a separate run first): {', '.join(removal_new)}"
        )
    return lines


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--report", required=True)
    p.add_argument("--step-summary-out", required=True)
    p.add_argument("--pr-body-out", required=True)
    p.add_argument("--staged", required=True, choices=["true", "false"],
                   help="whether `git status --porcelain` found real changes after this run -- "
                        "the real signal for whether a PR is being opened, not the JSON report "
                        "alone (a clean run can still touch nothing on disk).")
    p.add_argument("--confirmed-removals-out", default=None,
                   help="UBI-234: writes 'true'/'false' here -- whether any provider this run "
                        "has a page confirmed orphaned across two separate runs. The workflow "
                        "reads this to decide whether to comment on the standing tracking issue "
                        "even on a run that staged nothing else, since a confirmed removal "
                        "candidate is real, human-actionable news on its own.")
    args = p.parse_args()

    with open(args.report) as f:
        report = json.load(f)

    results = report["results"]
    not_covered = report.get("not_covered", [])

    summary = ["## Resource Reference regeneration"]
    if args.staged == "true":
        summary.append("Real changes were staged this run -- see the PR opened by this workflow.")
    else:
        summary.append("No real changes this run -- every provider checked was already current.")
    summary.append("")
    for r in results:
        summary.extend(format_provider(r))
        summary.append("")
    if not_covered:
        summary.append(
            f"**Not covered by this automation:** {', '.join(not_covered)} -- resource-page "
            f"regeneration for these providers uses a different, less mature mechanism "
            f"(gen_complete_pages.py's own splice-only generate_one) with no coverage-gap "
            f"staging path yet. Data-source pages for both are covered."
        )
    with open(args.step_summary_out, "w") as f:
        f.write("\n".join(summary) + "\n")

    if args.confirmed_removals_out:
        any_confirmed = any((r.get("stage") or {}).get("removal_candidates_confirmed") for r in results)
        with open(args.confirmed_removals_out, "w") as f:
            f.write("true" if any_confirmed else "false")

    if args.staged == "true":
        pr_body = ["Automated Resource Reference regeneration (UBI-137)."]
        pr_body.append("")
        pr_body.extend(summary[2:])  # same per-provider detail, skip the summary's own H2 + staged/clean line
        pr_body.append("")
        pr_body.append("Never sets `UBX_DOCS_ALLOW_COVERAGE_GAPS` -- any resource above listed as blocked was excluded from this batch, not shipped with a gap.")
        with open(args.pr_body_out, "w") as f:
            f.write("\n".join(pr_body) + "\n")


if __name__ == "__main__":
    main()
