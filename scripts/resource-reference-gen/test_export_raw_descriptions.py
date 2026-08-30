#!/usr/bin/env python3
"""UBI-222 real regression test for export_raw_descriptions.py's own
strip_qualifier/build_field_index/export_raw_descriptions -- no pytest
dependency (none exists anywhere in this repo), plain assertions,
exits nonzero on any real failure. Run directly:

  python3 test_export_raw_descriptions.py

Builds a tiny, real, self-contained fixture (a temp artifacts/<provider>
tree plus a temp dump-root) rather than mocking strip_qualifier's own
real collaborators -- proves the real, wired-together behavior, the
same discipline this whole file's own doc comment already holds
everything else in this pipeline to ("Confirmed live, empirically, not
assumed").

Covers the exact real bug (UBI-222): a field whose own real content
happens to end in one of the four qualifier phrases, with no relation
to its own real schema-derived qualifier, must never be truncated --
only a genuine render-time-duplicate suffix (one that matches the
field's own real, current qualifier) may be stripped. A field entirely
absent from the fresh dump (renamed/removed) must be left untouched.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def make_field(wire_name, required=False, optional=False, computed=False):
    return {
        "WireName": wire_name,
        "Type": {"Kind": 1, "Scalar": 1, "Element": None, "Object": None},
        "Required": required,
        "Optional": optional,
        "Computed": computed,
    }


def run():
    tmp = tempfile.mkdtemp(prefix="export_raw_descriptions_test_")
    try:
        docs_root = os.path.join(tmp, "docs")
        dump_root = os.path.join(tmp, "dump", "widgetco")
        os.makedirs(os.path.join(docs_root, "artifacts", "widgetco"))
        os.makedirs(dump_root)

        # widgetco_thing: a real, Optional+Computed field (per its own
        # real schema below) whose OWN real content coincidentally ends
        # in "Required." -- the exact real DigitalOcean/kubernetes shape
        # this bug produced. Must be preserved, not stripped.
        # widgetco_thing.duplicated: a real field whose stored text
        # genuinely IS desc+qualifier concatenated (a captured render-
        # time duplicate) -- must be stripped back to clean prose.
        # widgetco_ghost.gone: a field with no match at all in the fresh
        # dump (renamed/removed) -- must be left completely untouched,
        # even though its own stored text also ends in a qualifier
        # phrase.
        descriptions = {
            "widgetco_thing.coincidental": {
                "source": "ai",
                "text": "The widget's own real identifier. Required.",
            },
            "widgetco_thing.duplicated": {
                "source": "ai",
                "text": "The widget's own real name. Optional; if omitted, computed by Widgetco.",
            },
            "widgetco_ghost.gone": {
                "source": "ai",
                "text": "A real, orphaned field. Required.",
            },
        }
        json.dump(descriptions, open(os.path.join(docs_root, "artifacts", "widgetco", "descriptions.json"), "w"))

        # widgetco_thing's own real, fresh schema: "coincidental" is
        # Optional+Computed (so its real qualifier is "Optional; if
        # omitted, computed by Widgetco." -- NOT "Required.", proving
        # the stored "Required." is real content, not a duplicate).
        # "duplicated" is genuinely Optional+Computed too, matching what
        # was captured -- proving a real match strips correctly.
        widgetco_thing = [
            make_field("coincidental", required=False, optional=True, computed=True),
            make_field("duplicated", required=False, optional=True, computed=True),
        ]
        json.dump(widgetco_thing, open(os.path.join(dump_root, "widgetco_thing.json"), "w"))
        # widgetco_ghost is deliberately NOT written to dump_root -- it
        # no longer exists in the fresh schema.

        import export_raw_descriptions as m
        m.DOCS_ROOT = docs_root

        out = m.export_raw_descriptions("widgetco", "Widgetco", dump_root)

        assert out["widgetco_thing.coincidental"]["text"] == "The widget's own real identifier. Required.", (
            f"real content wrongly stripped: {out['widgetco_thing.coincidental']['text']!r}"
        )
        assert out["widgetco_thing.duplicated"]["text"] == "The widget's own real name.", (
            f"genuine render-time duplicate not stripped: {out['widgetco_thing.duplicated']['text']!r}"
        )
        assert out["widgetco_ghost.gone"]["text"] == "A real, orphaned field. Required.", (
            f"orphaned field (no match in fresh dump) was altered: {out['widgetco_ghost.gone']['text']!r}"
        )

        print("PASS: coincidental real content preserved, genuine duplicate stripped, orphaned field untouched")
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    run()
