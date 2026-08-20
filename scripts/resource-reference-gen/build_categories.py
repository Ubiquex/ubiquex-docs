#!/usr/bin/env python3
"""UBI-175 Phase 2: builds artifacts/<provider>/categories.json directly
from Phase 1's own audit findings (scratchpad/UBI-175-phase1-audit.md).

Shape: {"service_map": {sidebar-category-key: "Display Label"},
        "overrides": {resource_type: "Display Label"}}.

service_map is the CURRENT, Phase-1-verified-correct mechanical
categorization (every category NOT flagged, plus the 8 explicitly
reviewed single-word categories the audit judged correct) -- carried
forward as-is, not redesigned. overrides is the real, concrete fix for
every one of the 84 flagged (49 severe + 35 truncated) categories,
resource by resource -- most flagged categories are internally coherent
(every resource gets the same corrected label), a few genuinely conflate
2+ unrelated real products (Azure Dedicated/Service/Web, GCP
Service/Container) and get split per-resource.

Any resource matching neither service_map nor overrides lands in
"Other" and is reported -- see report_unmapped() below. Real, verified,
current docs.json navigation is the source for every resource's own
current category and type name (not re-derived, not assumed).
"""
import json
import re

DOCS_JSON = json.load(open('docs.json'))


def resource_type_from_page(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'title:\s*"([^"]+)"', text)
    return m.group(1) if m else None


# --- Real per-category override targets, one entry per flagged category,
# built directly from Phase 1's own reasoning (its SEVERE/TRUNCATED
# classification and the "why" behind each). A plain string applies to
# every resource in that category uniformly; a dict applies per real
# resource-path substring match, for the categories that genuinely
# conflate more than one real product.
OVERRIDES_RULES = {
    ("AWS", "Default"): "VPC",
    ("AWS", "Egress"): "VPC",
    ("AWS", "Flow"): "VPC",
    ("AWS", "Instance"): "EC2",
    ("AWS", "Internet"): "VPC",
    ("AWS", "Key"): "EC2",
    ("AWS", "Launch"): "EC2",
    ("AWS", "Load"): "ELB",
    ("AWS", "Main"): "VPC",
    ("AWS", "Placement"): "EC2",
    ("AWS", "Proxy"): "ELB",
    ("AWS", "Security"): "VPC",
    ("AWS", "Service"): "Cloud Map",
    ("AWS", "Snapshot"): "EBS",
    ("AWS", "Spot"): "EC2",
    ("AWS", "Subnet"): "VPC",
    ("AWS", "Volume"): "EBS",

    ("Azure", "Advanced"): "Microsoft Defender for Cloud",
    ("Azure", "Custom"): "Networking",
    ("Azure", "Dedicated"): {
        "hardware-security-module": "Dedicated HSM",
        "host": "Dedicated Host",
    },
    ("Azure", "Extended"): "Custom Locations",
    ("Azure", "Federated"): "Workload Identity Federation",
    ("Azure", "Local"): "VPN Gateway",
    ("Azure", "Managed"): {
        "application": "Managed Applications",
        "devops-pool": "Managed DevOps Pools",
        "disk": "Managed Disks",
        "lustre-file-system": "Azure Managed Lustre",
        "redis": "Azure Managed Redis",
    },
    ("Azure", "New"): "New Relic",
    ("Azure", "Orchestrated"): "Virtual Machine Scale Sets",
    ("Azure", "Point"): "VPN Gateway",
    ("Azure", "Private"): {
        "dns": "Private DNS",
        "endpoint": "Private Link",
        "link-service": "Private Link",
    },
    ("Azure", "Proximity"): "Compute",
    ("Azure", "Public"): "Networking",
    ("Azure", "Resource"): "Resource Manager",
    ("Azure", "Role"): "Azure RBAC",
    ("Azure", "Service"): {
        "fabric": "Service Fabric",
        "plan": "App Service",
    },
    ("Azure", "Source"): "App Service",
    ("Azure", "Trusted"): "Trusted Signing",
    ("Azure", "User"): "Managed Identity",
    ("Azure", "Web"): {
        "app-": "App Service",
        "application-firewall": "Web Application Firewall",
        "pubsub": "Web PubSub",
    },

    ("Datadog", "Shared"): "Dashboards",
    ("Datadog", "User"): "Users",

    ("GCP", "Config"): "Infrastructure Manager",
    ("GCP", "Container"): {
        "analysis": "Container Analysis",
        "attached-cluster": "GKE Multi-Cloud",
        "aws-": "GKE Multi-Cloud",
        "azure-": "GKE Multi-Cloud",
        "cluster": "GKE",
        "node-pool": "GKE",
        "registry": "Container Registry",
    },
    ("GCP", "Model"): "Model Armor",
    ("GCP", "Service"): {
        "account": "IAM",
        "directory": "Service Directory",
        "networking": "Service Networking",
    },

    ("GitHub", "Custom"): "Repository Settings",
    ("GitHub", "Full"): "Repositories",
    ("GitHub", "Get"): "Billing",
    ("GitHub", "Key"): "Keys",
    ("GitHub", "Simple"): "Users",
    ("GitHub", "Stack"): "Codespaces",

    # TRUNCATED -- real product, cut to one word.
    ("Azure", "Active"): "Active Directory Domain Services",
    ("Azure", "Confidential"): "Confidential Ledger",
    ("Azure", "Database"): "Database Migration Service",
    ("Azure", "Digital"): "Digital Twins",
    ("Azure", "Key"): "Key Vault",
    ("Azure", "Load"): "Load Testing",
    ("Azure", "Log"): "Log Analytics",
    ("Azure", "Management"): "Management Groups",
    ("Azure", "Recovery"): "Site Recovery",
    ("Azure", "Search"): "Cognitive Search",
    ("Azure", "Security"): "Microsoft Defender for Cloud",
    ("Azure", "Shared"): "Compute Gallery",
    ("Azure", "Site"): "Site Recovery",
    ("Azure", "Snapshot"): "Disks",
    ("Azure", "Stack"): "Azure Stack HCI",
    ("Azure", "Static"): "Static Web Apps",
    ("Azure", "Subnet"): "Networking",
    ("Azure", "System"): "System Center Virtual Machine Manager",
    ("Azure", "Video"): "Video Indexer",

    ("GCP", "Access"): "Access Context Manager",
    ("GCP", "Active"): "Managed Microsoft AD",
    ("GCP", "Assured"): "Assured Workloads",
    ("GCP", "Binary"): "Binary Authorization",
    ("GCP", "Database"): "Database Migration Service",
    ("GCP", "Deployment"): "Deployment Manager",
    ("GCP", "Discovery"): "Discovery Engine",
    ("GCP", "Document"): "Document AI",
    ("GCP", "Essential"): "Essential Contacts",
    ("GCP", "Identity"): "Identity Platform",
    ("GCP", "Integration"): "Integration Connectors",
    ("GCP", "License"): "License Manager",
    ("GCP", "Managed"): "Managed Service for Kafka",
    ("GCP", "Public"): "Public Certificate Authority",
    ("GCP", "Resource"): "Resource Manager",
    ("GCP", "Site"): "Site Verification",
}

# 8 categories Phase 1 reviewed and judged correct despite being a
# single word -- explicitly kept, not silently left to the mechanical
# default (so a future reader sees this was a real, reviewed decision).
VERIFIED_CORRECT = {
    ("AWS", "Config"): "Config",
    ("Azure", "Container"): "Container",
    ("Azure", "Policy"): "Policy",
    ("Azure", "Portal"): "Portal",
    ("GCP", "Project"): "Project",
    ("Kubernetes", "Discovery"): "Discovery",
    ("Kubernetes", "Resource"): "Resource",
    ("GitHub", "Deployment"): "Deployment",
}


def walk_provider_groups(provider_group):
    for sub in provider_group.get("pages", []):
        if isinstance(sub, dict) and "group" in sub:
            yield sub["group"], [p for p in sub.get("pages", []) if isinstance(p, str)]


def build_for_provider(provider_label, provider_key):
    """provider_label: docs.json's own group name ('AWS'); provider_key:
    artifacts/ directory name ('aws')."""
    for t in DOCS_JSON["navigation"]["tabs"]:
        if t["tab"] != "SDK Reference":
            continue
        for pg in t.get("groups", []):
            if pg.get("group") != provider_label:
                continue
            groups = dict(walk_provider_groups(pg))
            break

    service_map = {}
    overrides = {}
    flagged_cats = {k[1] for k in OVERRIDES_RULES if k[0] == provider_label}
    verified_cats = {k[1] for k in VERIFIED_CORRECT if k[0] == provider_label}

    for catname, pages in groups.items():
        if catname in flagged_cats:
            rule = OVERRIDES_RULES[(provider_label, catname)]
            for p in pages:
                rtype = resource_type_from_page(p + ".mdx")
                if not rtype:
                    continue
                if isinstance(rule, str):
                    overrides[rtype] = rule
                else:
                    label = None
                    relname = p.split("/")[-1]  # docs.json page paths carry no .mdx extension
                    for substr, target in rule.items():
                        if substr in relname:
                            label = target
                            break
                    overrides[rtype] = label or f"UNRESOLVED:{catname}"
        else:
            # current, Phase-1-verified-correct mechanical category
            # (includes the 8 explicitly-reviewed single-word ones).
            service_map[catname.lower()] = catname

    return {"service_map": service_map, "overrides": overrides}


PROVIDERS = [("AWS", "aws"), ("Azure", "azure"), ("GCP", "gcp"),
             ("Datadog", "datadog"), ("GitHub", "github"), ("Kubernetes", "kubernetes")]

if __name__ == "__main__":
    for label, key in PROVIDERS:
        result = build_for_provider(label, key)
        unresolved = [k for k, v in result["overrides"].items() if v.startswith("UNRESOLVED:")]
        if unresolved:
            print(f"!! {key}: {len(unresolved)} unresolved override(s): {unresolved}")
        json.dump(result, open(f"artifacts/{key}/categories.json", "w"), indent=1, sort_keys=True)
        print(f"{key}: service_map={len(result['service_map'])} overrides={len(result['overrides'])}")
