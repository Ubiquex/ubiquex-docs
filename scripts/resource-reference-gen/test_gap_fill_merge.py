#!/usr/bin/env python3
"""UBI-231 real regression test for gap_fill_merge.py -- no pytest
dependency (none exists anywhere in this repo), plain assertions,
exits nonzero on any real failure. Run directly:

  python3 test_gap_fill_merge.py

Covers the exact real bug found live: gap_fill_merge.py used to
re-save the whole descriptions.json with sort_keys=True, on the
assumption every real file was already lexicographically sorted. gcp's
own real file is not -- it groups resource entries before data-source
entries -- so a sort_keys=True resave silently reordered nearly every
existing key, turning an 82-entry addition into a 47000-line diff.
This proves the real, current behavior instead: every pre-existing
key keeps its own real position, new keys are appended, and skipping
an already-present key never touches its own existing value.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run(desc_path, *batch_paths):
    subprocess.run(
        [sys.executable, os.path.join(HERE, "gap_fill_merge.py"), desc_path, *batch_paths],
        check=True, capture_output=True, text=True,
    )


def test_preserves_existing_key_order_not_already_sorted():
    with tempfile.TemporaryDirectory() as tmp:
        desc_path = os.path.join(tmp, "descriptions.json")
        # Deliberately NOT lexicographically sorted -- "zebra" before
        # "apple" -- the exact real shape gcp's own file has (resources
        # grouped before data sources, not a flat alphabetical sort).
        original = {
            "zebra.field": {"source": "vendor-spec", "text": "Z"},
            "apple.field": {"source": "vendor-spec", "text": "A"},
        }
        with open(desc_path, "w") as f:
            json.dump(original, f, indent=1)
            f.write("\n")

        batch_path = os.path.join(tmp, "batch.json")
        with open(batch_path, "w") as f:
            json.dump({"mango.field": {"source": "ai-individual", "text": "M"}}, f)

        run(desc_path, batch_path)

        with open(desc_path) as f:
            result = json.load(f)
        keys = list(result.keys())
        assert keys[:2] == ["zebra.field", "apple.field"], (
            f"expected the two pre-existing keys to keep their own real order, got {keys}"
        )
        assert keys[-1] == "mango.field", f"expected the new key appended last, got {keys}"
        assert result["zebra.field"] == original["zebra.field"]
        assert result["apple.field"] == original["apple.field"]


def test_additive_diff_only_no_reordering_of_untouched_keys():
    with tempfile.TemporaryDirectory() as tmp:
        desc_path = os.path.join(tmp, "descriptions.json")
        original = {f"key{i}.field": {"source": "vendor-spec", "text": f"text{i}"} for i in (9, 1, 5, 3)}
        with open(desc_path, "w") as f:
            json.dump(original, f, indent=1)
            f.write("\n")
        before_bytes = open(desc_path).read()

        batch_path = os.path.join(tmp, "batch.json")
        with open(batch_path, "w") as f:
            json.dump({"new.field": {"source": "ai-individual", "text": "new"}}, f)

        run(desc_path, batch_path)

        after_bytes = open(desc_path).read()
        assert after_bytes.startswith(before_bytes.rstrip("\n}\n").rstrip()), (
            "expected the new file to start with the original content unchanged, "
            "the new key appended -- got a real reordering instead"
        )


def test_never_overwrites_an_existing_key():
    with tempfile.TemporaryDirectory() as tmp:
        desc_path = os.path.join(tmp, "descriptions.json")
        original = {"already.field": {"source": "vendor-spec", "text": "real, existing text"}}
        with open(desc_path, "w") as f:
            json.dump(original, f, indent=1)
            f.write("\n")

        batch_path = os.path.join(tmp, "batch.json")
        with open(batch_path, "w") as f:
            json.dump({"already.field": {"source": "ai-individual", "text": "would-be overwrite"}}, f)

        run(desc_path, batch_path)

        with open(desc_path) as f:
            result = json.load(f)
        assert result["already.field"]["text"] == "real, existing text", (
            "expected the already-present key's own real value to survive untouched"
        )


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
