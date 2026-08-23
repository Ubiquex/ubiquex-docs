"""Shared category resolution for the two-section categories.json shape
(services + overrides, added on top of the existing vendor-derived
categories map): overrides by exact wire name first, then the
resource's derived service in services, then the raw derived label.

The vendor-derived `categories` map itself is the authoritative base and
is never edited by this resolver or anything that calls it -- `services`
and `overrides` are a purely additive authored layer for display names
and for the rare case where the vendor's own grouping is wrong for a
reader (see artifacts/<provider>/categories.json's own _comment)."""
import re


def slugify(label):
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def resolve_category(categories_doc, wire):
    """categories_doc is one provider's already-loaded categories.json.
    Returns (label, domain_or_None, source) where source is one of
    "override", "service", "raw" -- source is for reporting/debugging,
    never meant to be shown to a reader."""
    raw_label = categories_doc.get("categories", {}).get(wire)
    if raw_label is None:
        return None, None, None

    overrides = categories_doc.get("overrides", {})
    if wire in overrides:
        entry = overrides[wire]
        return entry["label"], entry.get("domain"), "override"

    services = categories_doc.get("services", {})
    slug = slugify(raw_label)
    if slug in services:
        entry = services[slug]
        return entry["label"], entry.get("domain"), "service"

    return raw_label, None, "raw"
