#!/usr/bin/env python3
"""Pure nav restructure: every real service subgroup across all six
providers gets the identical shape -- a "Resources" subgroup always,
a "Data sources" subgroup only when that service has any. Before this,
a service with zero data sources (never matched by
gen_all_data_source_pages.py, or never regenerated at all) still sat as
a flat page-string list, while every service WITH data sources already
got the nested {"group": "Resources", ...}/{"group": "Data sources",
...} shape gen_data_source_pages.py's own real generation established --
inconsistent to browse, real pages neither added nor removed, only
docs.json's own navigation shape.
"""
import json

DOCS_JSON = "docs.json"
PROVIDER_TABS = {"AWS", "Azure", "GCP", "Kubernetes", "GitHub", "Datadog"}


def main():
    doc = json.load(open(DOCS_JSON))

    wrapped = 0
    already_nested = 0

    for t in doc["navigation"]["tabs"]:
        if t.get("tab") != "SDK Reference":
            continue
        for g in t["groups"]:
            if g.get("group") not in PROVIDER_TABS:
                continue
            for sg in g["pages"]:
                pages = sg.get("pages", [])
                if not pages:
                    continue
                if isinstance(pages[0], str):
                    sg["pages"] = [{"group": "Resources", "pages": pages}]
                    wrapped += 1
                else:
                    already_nested += 1

    with open(DOCS_JSON, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")

    print(f"wrapped {wrapped} flat groups into a Resources subgroup")
    print(f"{already_nested} groups already had the nested shape, untouched")


if __name__ == "__main__":
    main()
