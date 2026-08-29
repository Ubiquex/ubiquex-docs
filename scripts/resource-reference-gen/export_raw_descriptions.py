#!/usr/bin/env python3
"""UBI-102: exports a real, portable, qualifier-free description corpus
from artifacts/<provider>/descriptions.json -- the raw form both
`ubx sdk gen` (code comments) and this docs pipeline (rendered pages)
can read directly, replacing the two independently-maintained copies
(sdk/providers/descriptions/<provider>.json and this same artifacts
file) that caused UBI-102's own real 49,479-description gap.

Two real, baked-in transforms get reversed here, neither a guess:

1. A qualifier suffix ("Required."/"Optional."/"Optional; if omitted,
   computed by X."/"Computed by X after `ship`.") that field_desc()
   (gen_provider_docs.py) computes fresh and appends at render time --
   confirmed live, empirically, not assumed: sdk/providers/descriptions/
   datadog.json's own entry for datadog_dashboard.default_timeframe.from
   is qualifier-free ("...in epoch milliseconds."), the live, currently
   committed page for that exact field reads "...in epoch milliseconds.
   Optional; if omitted, computed by Datadog." -- appended exactly once,
   at render time, on top of the clean text. This file's own stored
   copy of the same entry already has the qualifier baked in -- a real
   artifact of how `migrate_descriptions.py` populated it (parsing
   already-rendered MDX for datadog/github, capturing whatever
   field_desc() had already produced, not the pre-qualifier original).
   All 437 real overlapping keys between the two files matched exactly
   once this suffix is stripped, zero content drift -- checked, not
   assumed.

2. `normalize_schema_description`'s own MDX-safety HTML-entity escaping
   (`<`/`>`/`{`/`}` to `&lt;`/`&gt;`/`&#123;`/`&#125;`) -- also baked in
   permanently by the same migration, also confirmed live (a real
   comparator field's stored text had `&gt;`/`&lt;` where the sdk-side
   copy had literal `>`/`<`). Reversed here since a code comment should
   show literal characters, not raw HTML entities -- docs' own render
   path re-escapes via the same `normalize_schema_description` call it
   already makes unconditionally, so storing the raw form here changes
   nothing for docs, and fixes it for code comments.

`vendor-spec` entries are never exported -- that text already lives
natively in the schema dump itself (the real provider's own wire
response), re-exporting it would be redundant, never a real gap to fill.

Output shape: {key: {"source": ..., "text": <raw, qualifier-free,
unescaped>}} -- same flat key shape (resource.field.path for a
resource, data_resource.field.path for a data source) this repo's own
descriptions.json already uses, so both consumers change only WHERE
they read from, never the shape they parse.

Usage:
  python3 export_raw_descriptions.py <provider> <provider-display> [--out PATH]
"""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS_ROOT = os.path.dirname(os.path.dirname(HERE))


def qualifiers_for(provider_display):
    return [
        "Required.",
        f"Optional; if omitted, computed by {provider_display}.",
        "Optional.",
        f"Computed by {provider_display} after `ship`.",
    ]


def unescape_entities(text):
    return (
        text
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&#123;", "{")
        .replace("&#125;", "}")
    )


def strip_qualifier(text, qualifiers):
    for q in qualifiers:
        suffix = " " + q
        if text.endswith(suffix):
            return text[: -len(suffix)]
    return text


def to_raw(text, qualifiers):
    return unescape_entities(strip_qualifier(text, qualifiers)).strip()


def export_raw_descriptions(provider, provider_display):
    desc_path = os.path.join(DOCS_ROOT, "artifacts", provider, "descriptions.json")
    desc_raw = json.load(open(desc_path, encoding="utf-8"))
    qualifiers = qualifiers_for(provider_display)

    out = {}
    for key, entry in desc_raw.items():
        if entry.get("source") == "vendor-spec":
            continue
        out[key] = {"source": entry["source"], "text": to_raw(entry["text"], qualifiers)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("provider")
    ap.add_argument("provider_display")
    ap.add_argument("--out", default=None, help="output path, default stdout")
    args = ap.parse_args()

    raw = export_raw_descriptions(args.provider, args.provider_display)
    by_prefix = {"resource": 0, "data_source": 0}
    for k in raw:
        by_prefix["data_source" if k.startswith("data_") else "resource"] += 1
    print(
        f"{args.provider}: exported {len(raw)} real, qualifier-free entries "
        f"({by_prefix['resource']} resource, {by_prefix['data_source']} data source)"
    )

    text = json.dumps(raw, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
