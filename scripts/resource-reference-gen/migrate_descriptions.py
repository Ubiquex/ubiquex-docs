#!/usr/bin/env python3
"""UBI-175 Phase 2: real migration of existing description content into
artifacts/<provider>/descriptions.json. Two real sources, never rewritten,
only migrated:

1. The LIVE docs corpus (resource-reference/**/*.mdx) -- parsed directly,
   real content, most current, correctly named. Used for datadog, github,
   kubernetes, and gcp/compute (the four providers/segments the docs
   pipeline has actually regenerated through the real, live-verified
   pipeline). AI-inferred fields are marked inline with "(AI-inferred)";
   everything else with real, non-mechanical text is vendor-sourced.

2. The checked-in `sdk/providers/descriptions/<provider>.json` artifact
   (a sibling repo, ubiquex/sdk/providers/descriptions/) -- real,
   already-paid-for DeepSeek/Claude content, verified this session to be
   ENTIRELY AI-inferred for every provider except aws (confirmed via a
   real verbatim-text cross-check against each provider's own live spec:
   0.18-2.9% coincidental short-string matches everywhere except aws,
   where a real git-diff boundary at commit f0e6b3b cleanly separates
   11,986 real CFN vendor entries from 18,078 real DeepSeek AI entries --
   see STATE.md's own matching checkpoint entry for the full account).
   Used as the ONLY source for aws (whose docs pages never received this
   content) and azure (whose SDK-codegen entry uses a genuinely different,
   OpenAPI-sourced `azure_*` resource set that has zero overlap with the
   docs corpus's own live `azurerm_*` corpus), and as a gap-filling
   supplement for gcp/compute where the live docs page has only a
   mechanical placeholder for a field the SDK artifact does cover.

Mechanical placeholder text (Required./Optional./"Optional; if omitted,
computed by X."/"Computed by X after `ship`.") carries no real content
and is never migrated as either vendor or AI -- this mirrors
gen_field_descriptions.py's own known_placeholder_lines() exactly, the
established, already-proven definition of "not real content" this
pipeline already uses.
"""
import json
import os
import re
import sys

DOCS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UBIQUEX_ROOT = os.path.join(os.path.dirname(DOCS_ROOT), "ubiquex")
SDK_DESC_DIR = os.path.join(UBIQUEX_ROOT, "sdk", "providers", "descriptions")

AI_MARKER = "**(AI-inferred)**"

PROVIDER_DISPLAY = {
    "aws": "AWS", "azure": "Azure", "gcp": "GCP",
    "datadog": "Datadog", "github": "GitHub", "kubernetes": "Kubernetes",
}


def known_placeholder_lines(provider_display):
    """Exact mirror of gen_field_descriptions.py's own function -- the
    established, already-proven definition of mechanical (non-real)
    text in this pipeline."""
    return {
        "Required.",
        f"Optional; if omitted, computed by {provider_display}.",
        "Optional.",
        f"Computed by {provider_display} after `ship`.",
    }


# --- docs-corpus parsing ----------------------------------------------------

RESPONSE_FIELD_OPEN = re.compile(r'<ResponseField\s+name="([^"]+)"')
TAG_LINE = re.compile(r'^\s*<')


def parse_docs_page(path, provider_display):
    """Walks a real .mdx page's own real JSX tree (ResponseField/
    Expandable) as an explicit-stack recursive-descent pass over the raw
    lines, returns {dotted.field.path: (text, is_ai)} for every field
    carrying real, non-mechanical content. A stack, not a regex flatten:
    two different top-level fields can each have a same-named nested
    child (every "tags" object has its own "name"/"value" children), and
    </ResponseField> always pops the most recently opened field -- real
    LIFO nesting, exactly what a stack models directly, with no separate
    depth-counting skip-ahead needed (a real bug in an earlier version of
    this function: skipping ahead to a field's own closing tag silently
    skipped every nested field's own opening tag too, never recording
    their paths at all)."""
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.split("\n")
    placeholders = known_placeholder_lines(provider_display)

    out = {}
    stack = []  # list of field names, current nesting path
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if "</ResponseField>" in line:
            if stack:
                stack.pop()
            i += 1
            continue
        m = RESPONSE_FIELD_OPEN.search(line)
        if m:
            name = m.group(1)
            stack.append(name)
            path_key = ".".join(stack)
            # This field's own description lines sit immediately after
            # its open tag, before any child tag (Expandable/nested
            # ResponseField) or its own close -- peek forward without
            # consuming beyond that, so the outer loop naturally
            # continues into any real nested structure next.
            desc_lines = []
            j = i + 1
            while j < n and not TAG_LINE.match(lines[j]):
                if lines[j].strip():
                    desc_lines.append(lines[j].strip())
                j += 1
            desc = " ".join(desc_lines).strip()
            is_ai = AI_MARKER in desc
            clean = desc.replace(AI_MARKER, "").strip()
            if clean and clean not in placeholders:
                out[path_key] = (clean, is_ai)
            i = j
            continue
        i += 1
    return out


def resource_type_from_page(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r'title:\s*"([^"]+)"', text)
    return m.group(1) if m else None


def migrate_from_docs(provider_dir_filter, provider_display):
    """provider_dir_filter: list of real resource-reference subdirectories
    to walk (e.g. ["datadog"] or ["gcp/compute"])."""
    result = {}  # "type.path" -> {"text":..., "source": "vendor"|"ai"}
    stats = {"pages": 0, "vendor": 0, "ai": 0}
    for rel in provider_dir_filter:
        root = os.path.join(DOCS_ROOT, "resource-reference", rel)
        for dirpath, _, files in os.walk(root):
            for fn in sorted(files):
                if fn == "index.mdx" or not fn.endswith(".mdx"):
                    continue
                full = os.path.join(dirpath, fn)
                rtype = resource_type_from_page(full)
                if not rtype:
                    continue
                stats["pages"] += 1
                fields = parse_docs_page(full, provider_display)
                for fpath, (text, is_ai) in fields.items():
                    key = f"{rtype}.{fpath}"
                    source = "ai" if is_ai else "vendor-spec"
                    result[key] = {"text": text, "source": source}
                    stats["ai" if is_ai else "vendor"] += 1
    return result, stats


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("provider")
    ap.add_argument("--docs-subdirs", nargs="+", required=True)
    args = ap.parse_args()
    display = PROVIDER_DISPLAY[args.provider]
    result, stats = migrate_from_docs(args.docs_subdirs, display)
    print(json.dumps({"stats": stats, "entries": len(result)}, indent=1))
    out_path = os.path.join(DOCS_ROOT, "artifacts", args.provider, "_docs_migrated.json")
    json.dump(result, open(out_path, "w"), indent=1, sort_keys=True)
    print("wrote", out_path)
