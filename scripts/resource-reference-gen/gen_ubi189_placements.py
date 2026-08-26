#!/usr/bin/env python3
"""UBI-189 driver: places the 493 AWS/Azure/Kubernetes data sources
gen_all_data_source_pages.py's own best_matching_group left unplaced
(the 734-unplaced count in the ticket also includes GitHub 107 and
Datadog 134, which are structural -- categories.json needs new entries
for those services first, so they're a separate driver, not this one).

Classification is by real content, decided by hand this session, never
by directory-name shape alone -- gen_all_data_source_pages.py's own
path heuristic already covers everything shape-derivable; everything
reaching this driver needed a human read of what the data source
actually is.

MATCHED: a real sibling resource exists already in docs.json under a
different service-group name than this data source's own scanned
service_dir would suggest (AWS's Smithy-derived data-source directory
naming and its CFN-derived resource wire-type prefix frequently
diverge completely for the identical real product, not just by
truncation -- confirmed live: CloudWatch's data sources scan under
"monitoring", its resources carry the "aws_cloud_watch_*" prefix; six
of Azure's nine unplaced items are Microsoft.Compute VM image/
extension/run-command catalog lookups whose field content
(publisher_name/offer/skus, run-command schema, VMSS rolling-upgrade
status) matches the already-placed "Azure Virtual Machines" resources
even though their own wire types share no prefix with them at all).
Placed as Data sources under that existing group, alongside its
Resources.

ORPHAN: no corresponding managed resource exists anywhere for that
service, confirmed by the same real-content read finding nothing to
match against. Each gets its OWN new group carrying the real product
name, Data sources only, no Resources sibling -- not one flat bucket
per provider, so a reader finds e.g. Amazon Polly's lookups where they
would expect Amazon Polly, not under a generic heading.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_data_source_pages import build_data_source_page
from gen_all_data_source_pages import (
    PROVIDERS, DUMP_ROOT, DOCS_ROOT,
    scan_go_data, provider_group, resource_pages_of, idents_for,
)

# service_dir -> real sibling group label already present in docs.json (Part 1)
AWS_MATCHED_BUCKETS = {
    "profile": "Amazon Connect Customer Profiles",
    "models_v2_lex": "Amazon Lex", "models_lex": "Amazon Lex",
    "runtime_lex": "Amazon Lex", "runtime_v2_lex": "Amazon Lex",
    "monitoring": "Amazon CloudWatch",
    "es": "Amazon OpenSearch Service",
    "messaging_chime": "Amazon Chime", "meetings_chime": "Amazon Chime",
    "admin_wickr": "AWS Wickr",
    "email": "Amazon Simple Email Service (SES)",
    "mail_manager": "Amazon Simple Email Service (SES)",
    "schemas": "Amazon EventBridge Schema Registry",
    "medical_imaging": "AWS HealthImaging",
    "states": "AWS Step Functions",
    "thinclient": "Amazon WorkSpaces Thin Client",
    "ingest_timestream": "Amazon Timestream", "query_timestream": "Amazon Timestream",
    "aoss": "Amazon OpenSearch Serverless",
    "airflow": "Amazon Managed Workflows for Apache Airflow (MWAA)",
    "airflow_serverless": "Amazon Managed Workflows for Apache Airflow (MWAA)",
    "firehose": "Amazon Data Firehose",
    "qconnect": "Amazon Connect Wisdom",
    "ds_data": "AWS Directory Service",
    "mq": "Amazon MQ",
    "aco_automation": "AWS Compute Optimizer",
    "aidevops": "Amazon Q Developer",
}

# service_dir -> real product name for a brand-new group (Part 2)
AWS_ORPHAN_BUCKETS = {
    "migrationhub_strategy": "AWS Migration Hub Strategy Recommendations",
    "mturk_requester": "Amazon Mechanical Turk",
    "glacier": "Amazon S3 Glacier",
    "agreement_marketplace": "AWS Marketplace", "catalog_marketplace": "AWS Marketplace",
    "discovery_marketplace": "AWS Marketplace", "deployment_marketplace": "AWS Marketplace",
    "entitlement_marketplace": "AWS Marketplace",
    "tnb": "AWS Telco Network Builder",
    "discovery": "AWS Application Discovery Service",
    "snowball": "AWS Snowball",
    "trustedadvisor": "AWS Trusted Advisor",
    "mgh": "AWS Migration Hub",
    "tax": "AWS Tax Settings",
    "cost_optimization_hub": "AWS Cost Optimization Hub",
    "machinelearning": "Amazon Machine Learning",
    "partnercentral_benefits": "AWS Partner Central", "partnercentral_account": "AWS Partner Central",
    "partnercentral_selling": "AWS Partner Central", "partnercentral_channel": "AWS Partner Central",
    "sts": "AWS Security Token Service (STS)",
    "tagging": "AWS Resource Groups Tagging API", "tags": "AWS Resource Groups Tagging API",
    "polly": "Amazon Polly",
    "swf": "Amazon Simple Workflow Service (SWF)",
    "participant_connect": "Amazon Connect Participant Service",
    "savingsplans": "AWS Savings Plans",
    "streams_dynamodb": "Amazon DynamoDB Streams",
    "sustainability": "AWS Sustainability",
    "ebs": "Amazon EBS direct APIs",
    "portal_sso": "AWS Single Sign-On",
    "repostspace": "AWS re:Post Private",
    "signin": "AWS Sign-In",
    "a2i_runtime_sagemaker": "Amazon Augmented AI (A2I)",
    "edge_sagemaker": "Amazon SageMaker Edge Manager",
    "featurestore_runtime_sagemaker": "Amazon SageMaker Feature Store",
    "freetier": "AWS Free Tier",
    "artifact": "AWS Artifact",
    "contact_lens": "Amazon Connect Contact Lens",
    "execute_api": "Amazon API Gateway V2",
    "migrationhub_orchestrator": "AWS Migration Hub Orchestrator",
    "pricingplanmanager": "AWS Pricing Plan Manager",
    "snow_device_management": "AWS Snow Device Management",
    "social_messaging": "AWS End User Messaging Social",
}

AZURE_MATCHED_BUCKETS = {
    "offer": "Azure Virtual Machines",
    "sku": "Azure Virtual Machines",
    "type_": "Azure Virtual Machines",
    "vmextension": "Azure Virtual Machines",
    "vmimage": "Azure Virtual Machines",
    "rolling": "Azure Virtual Machines",
    "run": "Azure Virtual Machines",
    # "list this RP's own operations" is a generic ARM control-plane
    # endpoint -- "Azure Resource Manager" already exists as a real
    # group with real Resources (deployments, features, links, generic
    # resource), confirmed live rather than assumed when creating it as
    # a new group collided with the real one already in docs.json.
    "microsoft": "Azure Resource Manager",
}
AZURE_ORPHAN_BUCKETS = {}

KUBERNETES_MATCHED_BUCKETS = {}
KUBERNETES_ORPHAN_BUCKETS = {
    "io": "Kubernetes API Discovery",
    "meta": "Kubernetes API Discovery",
}


def load_unmatched(provider_key):
    with open(f"/tmp/unmatched-{provider_key}.json") as f:
        return json.load(f)


def build_and_write_page(provider_key, cfg, wire, ident, meta):
    local = meta["localName"]
    fields = meta["ir"]["Fields"]
    slug = ident["local_slug"].replace("_", "-")
    go, ts, py = idents_for(ident["local_slug"], ident["service_dir"], ident["binding"], ident["config"])
    page = build_data_source_page(
        wire=wire, service=meta["service"], local=local, slug=slug,
        fields=fields, go=go, ts=ts, py=py,
        provider=provider_key, schema_name=cfg["schema_name"],
        provider_display=cfg["provider_display"], stack_name="example",
        sdk_repo_id=cfg["sdk_repo_id"],
    )
    out_dir = os.path.join(DOCS_ROOT, "resource-reference", provider_key, "data", ident["service_dir"])
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{slug}.mdx")
    with open(out_path, "w") as f:
        f.write(page)
    return f"resource-reference/{provider_key}/data/{ident['service_dir']}/{slug}"


def run_provider(provider_key, matched_buckets, orphan_buckets, doc):
    cfg = PROVIDERS[provider_key]
    schema = json.load(open(os.path.join(DUMP_ROOT, cfg["dump_dir"], "schema.json")))
    ds_entries = {k: v for k, v in schema.items() if v.get("namespace") == "data"}
    by_wire = {}
    for k, meta in ds_entries.items():
        wire = k[len("data_"):] if k.startswith("data_") else k
        by_wire[wire] = meta

    go_idents = scan_go_data(cfg["go_root"], cfg["go_dir"])
    groups = provider_group(doc, provider_key)

    unmatched = load_unmatched(provider_key)
    matched_written = 0
    orphan_written = 0
    matched_by_label = {}
    orphan_by_label = {}
    unresolved = []

    for wire, service_dir, local_slug in unmatched:
        ident = go_idents.get(wire)
        meta = by_wire.get(wire)
        if ident is None or meta is None:
            unresolved.append(wire)
            continue

        label = matched_buckets.get(service_dir)
        if label is not None:
            path = build_and_write_page(provider_key, cfg, wire, ident, meta)
            matched_by_label.setdefault(label, []).append(path)
            matched_written += 1
            continue

        label = orphan_buckets.get(service_dir)
        if label is not None:
            path = build_and_write_page(provider_key, cfg, wire, ident, meta)
            orphan_by_label.setdefault(label, []).append(path)
            orphan_written += 1
            continue

        unresolved.append(wire)

    # Part 1: fold matched pages into their existing group's Data sources.
    for label, new_pages in matched_by_label.items():
        gi = next((i for i, g in enumerate(groups) if g.get("group") == label), None)
        if gi is None:
            raise RuntimeError(f"{provider_key}: no existing group named {label!r}")
        g = groups[gi]
        resources_pages = resource_pages_of(g)
        existing_data = []
        pages = g.get("pages", [])
        if pages and isinstance(pages[0], dict):
            data_sub = next((p for p in pages if p.get("group") == "Data sources"), None)
            if data_sub:
                existing_data = [p for p in data_sub["pages"] if p not in new_pages]
        g["pages"] = [
            {"group": "Resources", "pages": resources_pages},
            {"group": "Data sources", "pages": sorted(set(existing_data) | set(new_pages))},
        ]

    # Part 2: one brand-new group per orphaned product, Data sources only.
    new_groups_created = []
    for label, new_pages in orphan_by_label.items():
        existing_gi = next((i for i, g in enumerate(groups) if g.get("group") == label), None)
        if existing_gi is not None:
            raise RuntimeError(f"{provider_key}: orphan label {label!r} collides with an existing group")
        groups.append({
            "group": label,
            "pages": [{"group": "Data sources", "pages": sorted(new_pages)}],
        })
        new_groups_created.append(label)

    return {
        "provider": provider_key,
        "matched_written": matched_written,
        "orphan_written": orphan_written,
        "matched_groups_touched": sorted(matched_by_label.keys()),
        "new_groups_created": sorted(new_groups_created),
        "unresolved": unresolved,
    }


def main():
    docs_json_path = os.path.join(DOCS_ROOT, "docs.json")
    doc = json.load(open(docs_json_path))

    results = []
    results.append(run_provider("aws", AWS_MATCHED_BUCKETS, AWS_ORPHAN_BUCKETS, doc))
    results.append(run_provider("azure", AZURE_MATCHED_BUCKETS, AZURE_ORPHAN_BUCKETS, doc))
    results.append(run_provider("kubernetes", KUBERNETES_MATCHED_BUCKETS, KUBERNETES_ORPHAN_BUCKETS, doc))

    with open(docs_json_path, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")

    for r in results:
        print(f"{r['provider']}: matched {r['matched_written']} into {len(r['matched_groups_touched'])} existing groups, "
              f"orphaned {r['orphan_written']} into {len(r['new_groups_created'])} new groups")
        if r["unresolved"]:
            print(f"{r['provider']}: UNRESOLVED ({len(r['unresolved'])}): {r['unresolved']}")
        print(f"  new groups: {r['new_groups_created']}")


if __name__ == "__main__":
    main()
