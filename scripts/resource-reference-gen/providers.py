#!/usr/bin/env python3
"""Two-tier provider registry -- the single place any script or
workflow in this pipeline learns which providers exist and their
docs-specific metadata. Built after ten independent hardcoded
provider lists across this directory (coverage_check.py, gen_all_
data_source_pages.py, regen_all.py x2, regen_pages.py x4, corpus_
index.py, build_categories.py, check_duplicate_wires.py) plus three
CI workflow YAML for-loops all needed the identical, separate edit
every time a new provider was onboarded -- confirmed live: none of
them got that edit for DigitalOcean's own first CI dispatch, so the
automated regen never actually ran, only the manual runbook path did.

Tier 1 (existence): read live from ubiquex's own real config
(sdk/providers/.ubx/config's [dynamic_providers.<name>] tables) --
the one place a provider's existence is actually declared, required
before anything else in onboarding (ubx-provider-runbook's own
onboard-provider.md hop 2). Never hardcoded here.

Tier 2 (metadata): docs-pipeline classification ubiquex's own config
doesn't carry and can't infer -- display name, whether this provider
gets real resource-page regen or is data-source-only, the docs-
internal key when it differs from the real schema/SDK-repo name
(gcp's own real config table is "google", UBI-102's own confirmed
precedent -- every other provider's two names already match). A
real, deliberate decision made once per new provider, in exactly one
place -- REGISTRY below, keyed by the real schema name so it lines
up directly against Tier 1 with no translation step.

all_docs_keys(config_path) is what replaces every one of those ten
hardcoded ALL_PROVIDERS-shaped lists: when a real ubiquex checkout is
available (every CI workflow already has one; regen_all.py's own
--ubiquex-config flag), it reads Tier 1 live and raises loudly, by
name, if any real provider is missing its own REGISTRY entry --
never a silent skip. Without a checkout available, it falls back to
iterating REGISTRY directly -- still one consolidated source instead
of ten, just without the live existence check.
"""
import sys

# schema_name (matches ubiquex's own [dynamic_providers.<name>] table
# name exactly) -> metadata. docs_key is this pipeline's own internal
# key when it differs from schema_name -- omitted when the two match.
REGISTRY = {
    "aws": dict(provider_display="AWS", tab_name="AWS", resource_regen=True),
    "azure": dict(provider_display="Microsoft Azure", tab_name="Azure", resource_regen=True),
    "google": dict(docs_key="gcp", provider_display="Google Cloud", tab_name="GCP", resource_regen=True),
    "kubernetes": dict(provider_display="Kubernetes", tab_name="Kubernetes", resource_regen=True),
    "github": dict(provider_display="GitHub", tab_name="GitHub", resource_regen=False),
    "datadog": dict(provider_display="Datadog", tab_name="Datadog", resource_regen=False),
    "digitalocean": dict(provider_display="DigitalOcean", tab_name="DigitalOcean", resource_regen=True),
}

# Uniform across every real provider carrying this source tag today
# (UBI-222's own confirmed audit) -- kept as a function, not inlined
# at every call site, so a future provider needing a different tag
# has exactly one place to diverge.
def skip_injection_source(docs_key):
    return "vendor-spec"


def docs_key_of(schema_name):
    if schema_name not in REGISTRY:
        raise KeyError(f"providers.py: no REGISTRY entry for schema name {schema_name!r}")
    return REGISTRY[schema_name].get("docs_key", schema_name)


def schema_name_of(docs_key):
    for sn, meta in REGISTRY.items():
        if meta.get("docs_key", sn) == docs_key:
            return sn
    raise KeyError(f"providers.py: no REGISTRY entry for docs key {docs_key!r}")


def provider_display(docs_key):
    return REGISTRY[schema_name_of(docs_key)]["provider_display"]


def tab_name(docs_key):
    return REGISTRY[schema_name_of(docs_key)]["tab_name"]


def is_resource_regen(docs_key):
    return REGISTRY[schema_name_of(docs_key)]["resource_regen"]


def resource_regen_docs_keys():
    return [docs_key_of(sn) for sn, meta in REGISTRY.items() if meta["resource_regen"]]


def data_source_only_docs_keys():
    return [docs_key_of(sn) for sn, meta in REGISTRY.items() if not meta["resource_regen"]]


def real_provider_schema_names(config_path):
    """Tier 1: every real, live provider ubiquex's own config
    declares, in file order. A schema name here with no REGISTRY
    entry is a real, actionable onboarding gap -- see all_docs_keys,
    which is what actually enforces that, not this function (kept
    separate so a caller that genuinely wants the raw, unvalidated
    list -- e.g. reporting exactly what's missing -- still can)."""
    import tomllib
    with open(config_path, "rb") as f:
        doc = tomllib.load(f)
    return list(doc.get("dynamic_providers", {}).keys())


def all_docs_keys(config_path=None):
    """The full, real, current provider set for this pipeline.
    Pass a real ubiquex checkout's sdk/providers/.ubx/config path
    (every CI workflow already checks one out) to derive this from
    Tier 1 live, with a loud failure naming any real provider this
    REGISTRY doesn't know about yet. Without one, falls back to
    REGISTRY's own keys -- still one shared source, just without the
    live existence check against ubiquex itself."""
    if config_path:
        names = real_provider_schema_names(config_path)
        missing = [n for n in names if n not in REGISTRY]
        if missing:
            raise SystemExit(
                f"providers.py: ubiquex's own config ({config_path}) declares "
                f"{missing!r} but this pipeline's own REGISTRY has no entry "
                f"for it -- add one to scripts/resource-reference-gen/"
                f"providers.py's own REGISTRY before anything here can run "
                f"against it. See ubx-provider-runbook's write-artifacts.md/"
                f"regen-docs.md for what a new provider needs beyond this."
            )
        return [docs_key_of(n) for n in names]
    return [docs_key_of(sn) for sn in REGISTRY]


def _main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="path to ubiquex's own sdk/providers/.ubx/config")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list-schema-names", action="store_true", help="one real schema name per line, Tier 1 (needs --config)")
    mode.add_argument("--list-docs-keys", action="store_true", help="one docs key per line, Tier 1+2 if --config given, else Tier 2 only")
    mode.add_argument("--validate", action="store_true", help="check Tier 1 against Tier 2, print OK or fail loudly (needs --config)")
    args = p.parse_args()

    if args.list_schema_names:
        if not args.config:
            sys.exit("providers.py --list-schema-names needs --config")
        for name in real_provider_schema_names(args.config):
            print(name)
    elif args.list_docs_keys:
        for key in all_docs_keys(args.config):
            print(key)
    elif args.validate:
        if not args.config:
            sys.exit("providers.py --validate needs --config")
        keys = all_docs_keys(args.config)
        print(f"providers.py: OK -- {len(keys)} real provider(s), every one has a REGISTRY entry: {keys}")


if __name__ == "__main__":
    _main()
