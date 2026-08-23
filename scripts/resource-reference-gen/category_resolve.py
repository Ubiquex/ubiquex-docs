"""Shared category resolution for categories.json.

All six providers were converted to flat per-resource form: one
overrides entry per real resource, `{wire: {label, domain?}}`, holding
a snapshot of whatever that resource's label resolved to at conversion
time. `services` is kept as an always-present, currently-empty section
(schema stability, not dead weight -- a provider could repopulate it
later without a shape change) but is never the resolution path for any
of the six real files today, since every resource already has a direct
override.

The old two-section shape (a vendor-derived `categories` base map, with
`services`/`overrides` as an additive layer on top) is still supported
here for backward compatibility -- resolve_category only walks that
fallback path when a file actually has a `categories` key. None of the
six real provider files do anymore; this is purely so an
older-shaped input never silently resolves to nothing."""
import re


def slugify(label):
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def resolve_category(categories_doc, wire):
    """categories_doc is one provider's already-loaded categories.json.
    Returns (label, domain_or_None, source) where source is one of
    "override", "service", "raw" -- source is for reporting/debugging,
    never meant to be shown to a reader."""
    overrides = categories_doc.get("overrides", {})
    if wire in overrides:
        entry = overrides[wire]
        return entry["label"], entry.get("domain"), "override"

    categories = categories_doc.get("categories")
    if categories is None:
        return None, None, None

    raw_label = categories.get(wire)
    if raw_label is None:
        return None, None, None

    services = categories_doc.get("services", {})
    slug = slugify(raw_label)
    if slug in services:
        entry = services[slug]
        return entry["label"], entry.get("domain"), "service"

    return raw_label, None, "raw"
