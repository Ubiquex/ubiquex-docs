#!/usr/bin/env python3
"""UBI-189 part 3: GitHub (107) and Datadog (134) data sources.

Structural, not a matching-bug/orphan split like AWS/Azure/Kubernetes
(gen_ubi189_placements.py): both providers' resource pages are already
grouped by curated product category (categories.json overrides), not
by a real service directory convention gen_all_data_source_pages.py's
own best_matching_group can walk -- confirmed live, an exact wire-type-
prefix check against each provider's own categories.json overrides
found zero matches for all 107 GitHub and all 134 Datadog items (see
/tmp/unmatched-github.json, /tmp/unmatched-datadog.json). Nothing here
is derivable; every wire below was read for its own real field content
and service name, then assigned the real product category that same
curation work already gave every other GitHub/Datadog resource.

Every item gets a real product group -- there is no orphan bucket for
this part, matching the ticket's own framing ("placing these means
authoring category entries for each, the same work the resource
categories needed").

Also writes each new label into artifacts/<provider>/categories.json's
own overrides section, the same real curation source the 80 GitHub and
172 Datadog resource wire types already draw from -- not a docs.json-
only fix.
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

GITHUB_LABELS = {
    "github_advanced_security_active_committers_repository": "Code Security",
    "github_configuration": "Code Security",
    "github_agent": "Agent Tasks",
    "github_cloud_agent": "Agent Tasks",
    "github_coding_agent": "Agent Tasks",
    "github_alert": "Code Scanning",
    "github_app": "GitHub Apps",
    "github_installable_organization": "GitHub Apps",
    "github_integration": "GitHub Apps",
    "github_artifact": "Actions",
    "github_artifact_deployment_record": "Actions",
    "github_concurrency_group": "Actions",
    "github_concurrency_group_list": "Actions",
    "github_concurrency_group_run_list": "Actions",
    "github_oidc_custom_sub": "Actions",
    "github_oidc_custom_sub_repo": "Actions",
    "github_permission": "Actions",
    "github_selected_actions": "Actions",
    "github_workflow": "Actions",
    "github_workflow_run": "Actions",
    "github_budget": "Billing",
    "github_plan": "Billing",
    "github_visual_studio_subscription_assignment": "Billing",
    "github_comment": "Repositories",
    "github_community_profile": "Repositories",
    "github_content": "Repositories",
    "github_content_file": "Repositories",
    "github_language": "Repositories",
    "github_license": "Repositories",
    "github_license_content": "Repositories",
    "github_minimal_repository": "Repositories",
    "github_nullable_simple_repository": "Repositories",
    "github_participation_stats": "Repositories",
    "github_popular": "Repositories",
    "github_protected_branch_admin_enforced": "Repositories",
    "github_protected_branch_pull_request_review": "Repositories",
    "github_required_status_check": "Repositories",
    "github_restriction": "Repositories",
    "github_stargazer": "Repositories",
    "github_stat": "Repositories",
    "github_status_check_policy": "Repositories",
    "github_topic": "Repositories",
    "github_topic_search_result_item": "Repositories",
    "github_traffic": "Repositories",
    "github_dependencie": "Dependabot",
    "github_vulnerability": "Dependabot",
    "github_external_group": "SCIM Provisioning",
    "github_external_groups": "SCIM Provisioning",
    "github_group_mapping": "SCIM Provisioning",
    "github_hosted_runner": "Hosted Compute",
    "github_self_hosted_runners_settings": "Hosted Compute",
    "github_feed": "Users",
    "github_hovercard": "Users",
    "github_user": "Users",
    "github_user_search_result_item": "Users",
    "github_immutable_releases_organization_settings": "Organizations",
    "github_invitation": "Organizations",
    "github_personal_access_token": "Organizations",
    "github_personal_access_token_request": "Organizations",
    "github_propertie": "Organizations",
    "github_import": "Migrations",
    "github_statu": "Migrations",
    "github_matching_ref": "Git",
    "github_membership": "Teams",
    "github_private_registrie": "Private Registries",
    "github_resource": "Security Advisories",
    "github_review": "Pull Requests",
    "github_view": "Projects",
    # New groups: no existing GitHub group covers these real products.
    "github_announcement_banner": "Announcements",
    "github_api_insights_route_stats": "API Insights",
    "github_api_insights_subject_stats": "API Insights",
    "github_api_insights_summary_stats": "API Insights",
    "github_api_insights_time_stats": "API Insights",
    "github_api_insights_user_stats": "API Insights",
    "github_api_overview": "Meta",
    "github_deprecation": "Meta",
    "github_public_ip": "Meta",
    "github_rate_limit_overview": "Meta",
    "github_root": "Meta",
    "github_stubbed": "Meta",
    "github_assignment": "Classroom",
    "github_classroom": "Classroom",
    "github_classroom_assignment": "Classroom",
    "github_bypass_request": "Rulesets",
    "github_bypass_response": "Rulesets",
    "github_dismissal_request": "Rulesets",
    "github_dismissal_request_response": "Rulesets",
    "github_rule_suite": "Rulesets",
    "github_rule_suites": "Rulesets",
    "github_ruleset": "Rulesets",
    "github_ruleset_version_with_state": "Rulesets",
    "github_dependency_graph_diff": "Dependency Graph",
    "github_dependency_graph_spdx_sbom": "Dependency Graph",
    "github_metadata": "Dependency Graph",
    "github_sbom": "Dependency Graph",
    "github_docker": "Packages",
    "github_package": "Packages",
    "github_package_version": "Packages",
    "github_marketplace_listing": "Marketplace",
    "github_marketplace_purchase": "Marketplace",
    "github_secret_scanning": "Secret Scanning",
    "github_secret_scanning_alert_with_metadata": "Secret Scanning",
    "github_secret_scanning_pattern_configuration": "Secret Scanning",
    "github_server_statistics": "Server Statistics",
    "github_thread": "Notifications",
    "github_thread_subscription": "Notifications",
    "github_webhook_config": "Webhooks",
}

DATADOG_LABELS = {
    "datadog_access_token_list_item": "Key Management",
    "datadog_list_application_keys_response": "Key Management",
    "datadog_validate_apikey_response": "Key Management",
    "datadog_validate_v2_response": "Key Management",
    "datadog_account_filters_response": "AWS Integration",
    "datadog_commitments_coverage_timeseries_response": "Cloud Cost Management",
    "datadog_commitments_list_item": "Cloud Cost Management",
    "datadog_commitments_on_demand_hotspots_scalar_response": "Cloud Cost Management",
    "datadog_commitments_savings_timeseries_response": "Cloud Cost Management",
    "datadog_commitments_scalar_column": "Cloud Cost Management",
    "datadog_commitments_utilization_scalar_response": "Cloud Cost Management",
    "datadog_commitments_utilization_timeseries_response": "Cloud Cost Management",
    "datadog_csm_agent_data": "Cloud Security Management",
    "datadog_csm_agentless_host_data": "Cloud Security Management",
    "datadog_csm_agentless_host_facet_data": "Cloud Security Management",
    "datadog_csm_cloud_accounts_coverage_analysis_response": "Cloud Security Management",
    "datadog_csm_host_facet_info_response": "Cloud Security Management",
    "datadog_csm_hosts_and_containers_coverage_analysis_response": "Cloud Security Management",
    "datadog_csm_serverless_coverage_analysis_response": "Cloud Security Management",
    "datadog_csm_unified_host_data": "Cloud Security Management",
    "datadog_csm_unified_host_facet_data": "Cloud Security Management",
    "datadog_finding": "Cloud Security Management",
    "datadog_default_rulesets_per_language_response": "Code Security",
    "datadog_tree_sitter_wasm": "Code Security",
    "datadog_node_types_response": "Code Security",
    "datadog_control_notification_settings_response": "Notifications",
    "datadog_global_incident_settings_response": "Incident Management",
    "datadog_timeline_cell_resource": "Incident Management",
    "datadog_attachment_array": "Incident Management",
    "datadog_domain_allowlist_response": "Organizations",
    "datadog_global_org_data": "Organizations",
    "datadog_v1": "Organizations",
    "datadog_annotation_data": "Dashboards",
    "datadog_graph_snapshot": "Dashboards",
    "datadog_list_powerpacks_response": "Dashboards",
    "datadog_list_shared_dashboards_response": "Dashboards",
    "datadog_snapshot_data": "Dashboards",
    "datadog_identity_provider_data": "Access Control",
    "datadog_ipallowlist_response": "Access Control",
    "datadog_oauth2_well_known_sites_response": "Access Control",
    "datadog_oauth_scopes_restriction_response": "Access Control",
    "datadog_permission": "Access Control",
    "datadog_samlconfigurations_response": "Access Control",
    "datadog_integration": "Integrations",
    "datadog_hamr_org_connection_response": "Integrations",
    "datadog_check_can_delete_monitor_response": "Monitors",
    "datadog_check_can_delete_sloresponse": "Service Level Objectives",
    "datadog_search_sloresponse": "Service Level Objectives",
    "datadog_slohistory_response_error": "Service Level Objectives",
    "datadog_sloreport_status_get_response": "Service Level Objectives",
    "datadog_list_downtimes_response": "Downtimes",
    "datadog_kind_data": "Software Catalog",
    "datadog_list_entity_catalog_response": "Software Catalog",
    "datadog_list_relation_catalog_response": "Software Catalog",
    "datadog_ownership_evidence_response": "Software Catalog",
    "datadog_ownership_inference_list_response": "Software Catalog",
    "datadog_ownership_inference_response": "Software Catalog",
    "datadog_ownership_settings_response": "Software Catalog",
    "datadog_ownership_untagged_findings_response": "Software Catalog",
    "datadog_scorecard_list_response_data": "Software Catalog",
    "datadog_scorecard_score_data": "Software Catalog",
    "datadog_single_entity_context_response": "Software Catalog",
    "datadog_recommendation_document": "Software Catalog",
    "datadog_list_on_call_notification_rules_response": "On-Call",
    "datadog_shift_included": "On-Call",
    "datadog_list_rules_response_data_item": "Security Monitoring",
    "datadog_signal_entities_response": "Security Monitoring",
    "datadog_io_cexplorer_list_response": "Security Monitoring",
    "datadog_model_lab_facet_keys_response": "LLM Observability",
    "datadog_model_lab_facet_values_response": "LLM Observability",
    "datadog_model_lab_project_artifacts_response": "LLM Observability",
    "datadog_model_lab_project_data": "LLM Observability",
    "datadog_model_lab_project_response": "LLM Observability",
    "datadog_model_lab_run_artifacts_response": "LLM Observability",
    "datadog_model_lab_run_data": "LLM Observability",
    "datadog_model_lab_run_response": "LLM Observability",
    "datadog_sample_log_generation_subscription_data": "Logs Pipelines",
    "datadog_artifact": "Application Security Management",
    "datadog_asset": "Application Security Management",
    "datadog_sbom": "Application Security Management",
    "datadog_licenses_list_response": "Application Security Management",
    "datadog_vulnerability": "Vulnerability Management",
    "datadog_list_tags_response": "Tags",
    "datadog_seat_user_data": "Users",
    "datadog_sourcemap_file_response": "RUM",
    "datadog_sourcemap_item": "RUM",
    "datadog_watcher_data": "RUM",
    "datadog_outcomes_response": "DORA Metrics",
    "datadog_workflow_instance_list_item": "Workflow Automation",
    "datadog_workflow_list_item": "Workflow Automation",
    "datadog_list_investigations_response_data": "Case Management",
    # New groups: no existing Datadog group covers these real products.
    "datadog_active_billing_dimensions_response": "Usage Metering",
    "datadog_billing_dimensions_mapping_body_item": "Usage Metering",
    "datadog_blueprint_data": "App Builder",
    "datadog_blueprint_metadata_data": "App Builder",
    "datadog_list_apps_response": "App Builder",
    "datadog_list_connections_response": "App Builder",
    "datadog_item_api_payload_data": "App Builder",
    "datadog_ciapp_git_hub_account_data": "CI Visibility",
    "datadog_container_image_item": "Container Monitoring",
    "datadog_container_item": "Container Monitoring",
    "datadog_ociconfig": "Container Monitoring",
    "datadog_devices_list_data": "Network Device Monitoring",
    "datadog_list_interface_tags_response": "Network Device Monitoring",
    "datadog_elastic_cloud_integration_account_response_data": "Elastic Cloud Integration",
    "datadog_fleet_agent_detail_v2_response": "Fleet Automation",
    "datadog_fleet_agent_v2": "Fleet Automation",
    "datadog_fleet_agent_version_v2": "Fleet Automation",
    "datadog_fleet_deployment_v2": "Fleet Automation",
    "datadog_fleet_deployment_v2_detail_response": "Fleet Automation",
    "datadog_fleet_schedule_v2": "Fleet Automation",
    "datadog_fleet_schedule_v2_response": "Fleet Automation",
    "datadog_fleet_tracers_response": "Fleet Automation",
    "datadog_governance_config_response": "Governance",
    "datadog_governance_control_data": "Governance",
    "datadog_governance_control_detection_data": "Governance",
    "datadog_governance_control_detection_response": "Governance",
    "datadog_governance_control_response": "Governance",
    "datadog_governance_insight_data": "Governance",
    "datadog_governance_notification_settings_response": "Governance",
    "datadog_ipranges": "IP Ranges",
    "datadog_list_apis_response_data": "API Catalog",
    "datadog_network_health_insight": "Network Performance Monitoring",
    "datadog_single_aggregated_connection_response_data": "Network Performance Monitoring",
    "datadog_single_aggregated_dns_response_data": "Network Performance Monitoring",
    "datadog_process_summary": "Process Monitoring",
    "datadog_pruned_trace_response": "APM",
    "datadog_trace_response": "APM",
    "datadog_salesforce_incidents_organization_response_data": "Salesforce Integration",
    "datadog_salesforce_incidents_template_response_data": "Salesforce Integration",
    "datadog_secret_rule_data": "Sensitive Data Scanner",
    "datadog_sensitive_data_scanner_get_config_included_item": "Sensitive Data Scanner",
    "datadog_sensitive_data_scanner_standard_patterns_response_item": "Sensitive Data Scanner",
    "datadog_twilio_integration_account_response_data": "Twilio Integration",
}


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


def run_provider(provider_key, labels, doc, categories_doc):
    cfg = PROVIDERS[provider_key]
    schema = json.load(open(os.path.join(DUMP_ROOT, cfg["dump_dir"], "schema.json")))
    ds_entries = {k: v for k, v in schema.items() if v.get("namespace") == "data"}
    by_wire = {}
    for k, meta in ds_entries.items():
        wire = k[len("data_"):] if k.startswith("data_") else k
        by_wire[wire] = meta

    go_idents = scan_go_data(cfg["go_root"], cfg["go_dir"])
    groups = provider_group(doc, provider_key)
    existing_names = {g["group"]: i for i, g in enumerate(groups)}

    with open(f"/tmp/unmatched-{provider_key}.json") as f:
        unmatched = json.load(f)

    by_label = {}
    unresolved = []
    for wire, service_dir, local_slug in unmatched:
        label = labels.get(wire)
        if label is None:
            unresolved.append(wire)
            continue
        ident = go_idents.get(wire)
        meta = by_wire.get(wire)
        if ident is None or meta is None:
            unresolved.append(wire)
            continue
        path = build_and_write_page(provider_key, cfg, wire, ident, meta)
        by_label.setdefault(label, []).append((wire, path))

    new_groups = []
    touched_existing = []
    for label, items in by_label.items():
        new_pages = [p for _, p in items]
        gi = existing_names.get(label)
        if gi is not None:
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
            touched_existing.append(label)
        else:
            groups.append({
                "group": label,
                "pages": [{"group": "Data sources", "pages": sorted(new_pages)}],
            })
            new_groups.append(label)

        for wire, _ in items:
            categories_doc["overrides"][wire] = {"label": label}

    return {
        "provider": provider_key,
        "written": sum(len(v) for v in by_label.values()),
        "touched_existing": sorted(touched_existing),
        "new_groups": sorted(new_groups),
        "unresolved": unresolved,
    }


def main():
    docs_json_path = os.path.join(DOCS_ROOT, "docs.json")
    doc = json.load(open(docs_json_path))

    results = []
    for provider_key, labels in [("github", GITHUB_LABELS), ("datadog", DATADOG_LABELS)]:
        cat_path = f"artifacts/{provider_key}/categories.json"
        categories_doc = json.load(open(cat_path))
        r = run_provider(provider_key, labels, doc, categories_doc)
        results.append(r)
        with open(cat_path, "w") as f:
            json.dump(categories_doc, f, indent=1, sort_keys=True)
            f.write("\n")

    with open(docs_json_path, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")

    for r in results:
        print(f"{r['provider']}: wrote {r['written']} pages, "
              f"{len(r['touched_existing'])} existing groups touched, "
              f"{len(r['new_groups'])} new groups created")
        if r["unresolved"]:
            print(f"{r['provider']}: UNRESOLVED ({len(r['unresolved'])}): {r['unresolved']}")
        print(f"  new groups: {r['new_groups']}")


if __name__ == "__main__":
    main()
