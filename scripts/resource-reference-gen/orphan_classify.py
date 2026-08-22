#!/usr/bin/env python3
"""UBI-175 Phase D: splits each provider's ORPHANED bucket (redirect_
diff.py's own output) into two real, distinct classes, same split the
founder asked for after the AWS Phase 4 precedent:

  SERVICE-ONBOARDED  -- the old resource's own service already has real,
    live pages from the new source (its normalized name appears inside
    the old wire), so this specific old resource has no new counterpart
    for a reason OTHER than "we haven't reached that service yet" --
    almost always a Terraform-only decomposition/association/deprecated-
    variant concept the new discovery-doc/ARM source doesn't model as
    its own resource at all.

  SERVICE-NOT-ONBOARDED -- no currently-live new-source service name
    appears in the old wire at all -- the new source genuinely doesn't
    cover this product/service yet, a real coverage gap rather than a
    modeling difference.

This is a real, mechanical signal (service name presence), not a
semantic judgment about whether Terraform "should" have modeled it
differently -- reported as a signal for the founder's own review, not
a final verdict.

Usage:
  python3 orphan_classify.py gcp
  python3 orphan_classify.py azure
"""
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TITLE_RE = re.compile(r'^title:\s*"([^"]+)"', re.MULTILINE)
OLD_MARKER = "Real, generated bindings for"

IAM_RE = re.compile(r'_iam_(binding|member|policy)$')
ASSOC_RE = re.compile(r'_(association|attachment|assignment)$')


def normalize(w):
    return w.replace("_", "").replace("-", "").lower()


def main():
    provider = sys.argv[1]
    prefix = {"gcp": "google_", "azure": "azurerm_"}[provider]

    live_service_dirs = set()
    live_wire_bodies = set()
    for path in glob.glob(os.path.join(REPO_ROOT, "resource-reference", provider, "**", "*.mdx"), recursive=True):
        if os.path.basename(path) == "index.mdx":
            continue
        text = open(path).read()
        if OLD_MARKER in text:
            continue
        m = TITLE_RE.search(text)
        if m:
            live_wire_bodies.add(normalize(m.group(1)))
        # service dir = the path segment right after resource-reference/<provider>/
        rel = os.path.relpath(path, os.path.join(REPO_ROOT, "resource-reference", provider))
        service_dir = rel.split(os.sep)[0]
        if len(service_dir) >= 4:  # skip degenerate/too-short dirs, real noise source
            live_service_dirs.add(normalize(service_dir))

    d = json.load(open(f"/tmp/regen-scratch/{provider}_redirect_diff.json"))
    orphans = [o["old_wire"] for o in d["orphaned"]]

    onboarded, not_onboarded = [], []
    for w in orphans:
        rest = w[len(prefix):] if w.startswith(prefix) else w
        body = normalize(rest)
        first_token = normalize(rest.split("_", 1)[0])
        # found-in-review miss: the real GCP API/service name for
        # Bigtable is "bigtableadmin" (google_bigtableadmin, the real
        # onboarded family/service dir), but the OLD Terraform wire uses
        # the shorter "google_bigtable_*" -- "bigtableadmin" never
        # appears as a substring of "bigtableinstance", so the one-
        # directional body-contains-service_dir check alone missed a
        # genuinely already-onboarded service. Also check the reverse
        # direction (old wire's own first token is itself a real prefix
        # of a live service dir), gated to >=5 chars so this doesn't
        # reopen the earlier short-generic-token false-positive class
        # (e.g. "api").
        # A third signal beyond service-dir matching: Azure's own ARM
        # namespace grouping can be a totally different WORD from the
        # old Terraform name for the same real product (azurerm_app_
        # service_* vs. the real "web" family/Microsoft.Web -- zero
        # token overlap at the service-dir level at all), but the real
        # resource's own new WIRE name usually still echoes the old
        # concept somewhere in its body ("openapi_app_service_plan"
        # does contain "appservice"). Two leading old tokens
        # concatenated, gated to >=6 chars, checked against every live
        # wire body -- looser than the service-dir check, but still a
        # real multi-word token match, not a bare short word.
        two_tok = normalize("".join(rest.split("_")[:2]))
        hit = (
            any(sd in body for sd in live_service_dirs)
            or (len(first_token) >= 5 and any(sd.startswith(first_token) for sd in live_service_dirs))
            or (len(two_tok) >= 6 and any(two_tok in wb for wb in live_wire_bodies))
        )
        (onboarded if hit else not_onboarded).append(w)

    iam_like = [w for w in orphans if IAM_RE.search(w) or ASSOC_RE.search(w)]

    print(f"{provider}: {len(orphans)} orphaned total")
    print(f"  SERVICE-ONBOARDED (TF-shaped concept, no new-source equivalent): {len(onboarded)}")
    print(f"  SERVICE-NOT-ONBOARDED (genuine coverage gap):                    {len(not_onboarded)}")
    print(f"  of which IAM-binding/member/policy or association/attachment/assignment shaped: {len(iam_like)}")

    out = {
        "provider": provider,
        "onboarded_service_no_new_equivalent": onboarded,
        "not_onboarded_genuine_gap": not_onboarded,
        "iam_or_association_shaped": iam_like,
    }
    out_path = f"/tmp/regen-scratch/{provider}_orphan_classify.json"
    json.dump(out, open(out_path, "w"), indent=2)
    print(f"\nwrote -> {out_path}")

    print("\n--- sample SERVICE-NOT-ONBOARDED (25) ---")
    for w in not_onboarded[:25]:
        print(" ", w)


if __name__ == "__main__":
    main()
