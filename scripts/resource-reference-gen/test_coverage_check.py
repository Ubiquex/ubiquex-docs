#!/usr/bin/env python3
"""UBI-222 real regression test for coverage_check.py's own
field_is_covered -- no pytest dependency (none exists anywhere in this
repo), plain assertions, exits nonzero on any real failure. Run
directly:

  python3 test_coverage_check.py

Covers the precise rule the founder gave, not a looser approximation:
a pure object-typed wrapper with no dedicated description of its own
is exempt from missing_field_description ONLY when every one of its
own real children is itself covered, recursively. A wrapper with even
one undescribed descendant is still a real gap. A scalar field is
only ever covered by its own text. An object field with zero real
children is treated the same as an undescribed scalar.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from coverage_check import field_is_covered

SCALAR = {"Kind": 1, "Scalar": 1, "Element": None, "Object": None}


def scalar_field(name, description=""):
    return {"WireName": name, "Type": SCALAR, "Description": description}


def object_field(name, children, description=""):
    return {
        "WireName": name,
        "Type": {"Kind": 5, "Scalar": 0, "Element": None, "Object": children},
        "Description": description,
    }


def run():
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    # A wrapper with no dedicated text of its own, every child described:
    # exempt -- not a gap.
    wrapper = object_field("entitlement", [
        scalar_field("account", "The AWS account ID"),
        scalar_field("role_name", "The IAM role name"),
    ])
    check(
        "wrapper with fully described children is covered",
        field_is_covered(wrapper, "pw", "entitlement", {}),
        True,
    )

    # A wrapper with no dedicated text, one child undescribed: still a
    # real gap.
    wrapper_partial = object_field("entitlement", [
        scalar_field("account", "The AWS account ID"),
        scalar_field("role_name", ""),
    ])
    check(
        "wrapper with one undescribed child is still a gap",
        field_is_covered(wrapper_partial, "pw", "entitlement", {}),
        False,
    )

    # A wrapper with no dedicated text, an undescribed GRANDCHILD nested
    # two levels down: still a real gap -- recursion has to go all the
    # way down, not just one level.
    wrapper_deep_gap = object_field("entitlement", [
        object_field("principal_role", [
            scalar_field("account", "The AWS account ID"),
            scalar_field("undescribed_leaf", ""),
        ]),
    ])
    check(
        "wrapper with an undescribed grandchild is still a gap",
        field_is_covered(wrapper_deep_gap, "pw", "entitlement", {}),
        False,
    )

    # A wrapper with no dedicated text, every descendant described at
    # every depth: exempt.
    wrapper_deep_ok = object_field("entitlement", [
        object_field("principal_role", [
            scalar_field("account", "The AWS account ID"),
            scalar_field("principal", "The principal identity"),
        ]),
    ])
    check(
        "wrapper with every descendant described at every depth is covered",
        field_is_covered(wrapper_deep_ok, "pw", "entitlement", {}),
        True,
    )

    # A scalar field with no description of its own: always a gap --
    # it has no children to borrow coverage from.
    check(
        "an undescribed scalar is always a gap",
        field_is_covered(scalar_field("route_id", ""), "pw", "route_id", {}),
        False,
    )

    # A scalar field WITH its own native description: covered.
    check(
        "a described scalar is covered",
        field_is_covered(scalar_field("api_id", "The API identifier."), "pw", "api_id", {}),
        True,
    )

    # An object field with zero real children: not exempt -- treated
    # the same as an undescribed scalar, never silently passed.
    empty_wrapper = object_field("empty_thing", [])
    check(
        "an object field with zero children is not exempt",
        field_is_covered(empty_wrapper, "pw", "empty_thing", {}),
        False,
    )

    # A wrapper with no native Description but a real descriptions.json
    # entry under its own exact depth-0 key: covered by that entry
    # directly, the ordinary (non-wrapper-exemption) path.
    wrapper_corpus_covered = object_field("entitlement", [
        scalar_field("account", ""),
    ])
    descriptions = {"pw.entitlement": "A real, dedicated corpus entry."}
    check(
        "a wrapper covered by its own corpus entry, regardless of children",
        field_is_covered(wrapper_corpus_covered, "pw", "entitlement", descriptions),
        True,
    )

    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    print("all field_is_covered checks passed")


if __name__ == "__main__":
    run()
