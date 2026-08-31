#!/usr/bin/env python3
"""UBI-236 real regression test: schema_entries_from_corrected and
build_schema_entries now share one real widening step (_widen_candidates),
rather than the two diverging the way they used to -- build_schema_entries
tried both the raw and doubling-corrected form of a wire,
schema_entries_from_corrected tried only whatever form its caller
happened to pass in, which is what let a wire renamed between the raw
and corrected form (google_dns_key) fail to match its own real intro.

No pytest dependency (none exists anywhere in this repo), plain
assertions, exits nonzero on any real failure. Run directly:

  python3 test_schema_entries_widening.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from coverage_check import schema_entries_from_corrected, build_schema_entries, _widen_candidates


def test_gcp_widens_raw_wire_to_include_corrected_form():
    # google_dns_dns_key is the real, confirmed doubling case
    # gcp_corrected_key exists to collapse -- schema_entries_from_corrected
    # must widen a raw wire the same way build_schema_entries already does.
    rec = {"service": "dns", "ir": {"Fields": []}}
    candidates, _ = schema_entries_from_corrected("gcp", {"google_dns_dns_key": rec})[("google_dns_dns_key", False)]
    assert candidates == {"google_dns_dns_key", "google_dns_key"}, (
        f"expected both the raw and doubling-corrected form, got {candidates}"
    )


def test_azure_widens_raw_wire_to_include_corrected_form():
    rec = {"service": "kusto", "ir": {"Fields": []}}
    candidates, _ = schema_entries_from_corrected(
        "azure", {"azure_azure_kusto_kusto_cluster": rec}
    )[("azure_azure_kusto_kusto_cluster", False)]
    assert candidates == {"azure_azure_kusto_kusto_cluster", "azure_kusto_cluster"}, (
        f"expected both the raw and doubling-corrected form, got {candidates}"
    )


def test_idempotent_on_an_already_corrected_wire():
    # regen_pages.py's own real call site passes wires it already ran
    # through gcp_corrected_key/azure_corrected_wire itself -- widening
    # an already-corrected wire again must add no spurious second
    # candidate, or every already-clean regen_pages.py run would
    # start reporting phantom extra candidates.
    rec = {"service": "dns", "ir": {"Fields": []}}
    candidates, _ = schema_entries_from_corrected("gcp", {"google_dns_key": rec})[("google_dns_key", False)]
    assert candidates == {"google_dns_key"}, (
        f"expected re-correcting an already-corrected wire to be a no-op, got {candidates}"
    )


def test_no_widening_for_a_provider_with_no_doubling_pathology():
    rec = {"service": "iam", "ir": {"Fields": []}}
    candidates, _ = schema_entries_from_corrected("aws", {"aws_iam_role": rec})[("aws_iam_role", False)]
    assert candidates == {"aws_iam_role"}, (
        f"aws has no doubling correction, expected the raw wire as the only candidate, got {candidates}"
    )


def test_matches_build_schema_entries_for_the_identical_wire():
    # The real point of UBI-236: both callers now resolve the same
    # wire to the same candidate set via the same shared step, not
    # two implementations that can silently drift apart again.
    rec = {"service": "dns", "namespace": "resource", "ir": {"Fields": []}}
    from_corrected, _ = schema_entries_from_corrected("gcp", {"google_dns_dns_key": rec})[("google_dns_dns_key", False)]
    from_schema, _ = build_schema_entries("gcp", {"google_dns_dns_key": rec})[("google_dns_dns_key", False)]
    assert from_corrected == from_schema, (
        f"the two callers disagreed on the same wire: {from_corrected} vs {from_schema}"
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
